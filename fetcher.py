#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import concurrent.futures as futures
import hashlib
import json
import os
import re
import sys
import time
import socket
import traceback
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Callable
from threading import Lock
from collections import defaultdict

import feedparser
import tldextract
from dateutil import parser as dtparse
from newsplease import NewsPlease

# --- optional progress backends ---
try:
    from rich.progress import (
        Progress, SpinnerColumn, BarColumn, TimeElapsedColumn,
        TimeRemainingColumn, MofNCompleteColumn, TextColumn
    )
    RICH_OK = True
except Exception:
    RICH_OK = False

try:
    from tqdm import tqdm as tqdm_cls
    TQDM_OK = True
except Exception:
    TQDM_OK = False

ISO = "%Y-%m-%dT%H:%M:%SZ"


@dataclass
class ArticleOut:
    source_id: str
    source_domain: str
    url: str
    title: Optional[str]
    content: Optional[str]
    published_at: Optional[str]        # ISO-8601 UTC
    published_at_source_tz: Optional[str]
    crawled_at: str                    # ISO-8601 UTC
    language: Optional[str]
    authors: Optional[List[str]]
    extras: Dict[str, Any]


def parse_since(s: str) -> timedelta:
    m = re.fullmatch(r"(?i)\s*(\d+)\s*([smhdw])\s*", s)
    if not m:
        raise ValueError("Use like: 45m, 2h, 24h, 3d, 1w")
    n = int(m.group(1))
    unit = m.group(2).lower()
    return {
        "s": timedelta(seconds=n),
        "m": timedelta(minutes=n),
        "h": timedelta(hours=n),
        "d": timedelta(days=n),
        "w": timedelta(weeks=n),
    }[unit]


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def slugify(text: str, fallback: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    if not text:
        text = fallback
    return text[:128]


def best_entry_datetime(entry: Dict[str, Any]) -> Optional[datetime]:
    for key in ("published", "pubDate", "updated", "dc_date"):
        v = entry.get(key)
        if v:
            try:
                dt = dtparse.parse(v)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    for key in ("published_parsed", "updated_parsed"):
        v = entry.get(key)
        if v:
            try:
                return datetime(*v[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def collect_feed_urls(
    source_id: str,
    urls: Sequence[str],
    since_utc: datetime,
    request_headers: Optional[Dict[str, str]] = None,
    retries: int = 2,
    log_error: Optional[Callable[[str, Optional[BaseException]], None]] = None,
) -> List[Tuple[str, Optional[datetime]]]:
    """
    Надёжный сбор ссылок из RSS:
      - ретраи на сетевые сбои/таймауты
      - кастомный User-Agent
      - без падений процесса
    """
    out: List[Tuple[str, Optional[datetime]]] = []
    headers = request_headers or {}

    for feed_url in urls:
        parsed = None
        last_err = None
        for attempt in range(retries + 1):
            try:
                # feedparser сам делает HTTP-запрос; уважается socket.setdefaulttimeout(...)
                parsed = feedparser.parse(feed_url, request_headers=headers)
                # Иногда вместо исключения будет parsed.bozo=True (битый фид)
                # или status != 200 — обработаем ниже.
                break
            except Exception as e:
                last_err = e
                # экспоненциальный бэкофф с джиттером
                if attempt < retries:
                    sleep_s = (1.5 ** attempt) + random.random() * 0.5
                    time.sleep(sleep_s)
                else:
                    msg = f"RSS fetch failed after retries | src={source_id} | url={feed_url} | err={repr(e)}"
                    if log_error:
                        log_error(msg, e)
                    else:
                        print(f"[w] {msg}", file=sys.stderr)
                    parsed = None

        if not parsed:
            continue

        # Проверка статуса HTTP, если доступен
        status = getattr(parsed, "status", None)
        if status and status != 200:
            msg = f"non-200 RSS response | src={source_id} | url={feed_url} | status={status}"
            if log_error:
                log_error(msg, last_err)
            else:
                print(f"[w] {msg}", file=sys.stderr)
            # можно не прерывать: иногда лента частично читается — но обычно entries пустые.
        try:
            entries = getattr(parsed, "entries", []) or []
        except Exception as e:
            msg = f"bad RSS structure | src={source_id} | url={feed_url} | err={repr(e)}"
            if log_error:
                log_error(msg, e)
            else:
                print(f"[w] {msg}", file=sys.stderr)
            entries = []

        for e in entries:
            dt = best_entry_datetime(e)
            link = e.get("link") or ""
            if not link:
                continue
            if dt is None:
                # без даты — всё равно возьмём (метку определим позже при извлечении)
                out.append((link, None))
            else:
                if dt >= since_utc:
                    out.append((link, dt))

    # очистка/дедуп
    out = [(u, dt) for (u, dt) in out if u]
    seen = set()
    uniq: List[Tuple[str, Optional[datetime]]] = []
    for u, dt in out:
        if u not in seen:
            uniq.append((u, dt))
            seen.add(u)
    return uniq


def extract_with_newsplease(url: str) -> Optional[NewsPlease]:
    try:
        return NewsPlease.from_url(url)
    except Exception:
        return None


def map_article(source_id: str, url: str, guess_dt: Optional[datetime]) -> Optional[ArticleOut]:
    art = extract_with_newsplease(url)
    if art is None:
        return None

    content = getattr(art, "maintext", None)
    title   = getattr(art, "title", None)

    ext = tldextract.extract(url)
    domain = ".".join(part for part in [ext.domain, ext.suffix] if part)

    dp: Optional[datetime] = getattr(art, "date_publish", None)
    if isinstance(dp, datetime):
        if dp.tzinfo is None:
            dp = dp.replace(tzinfo=timezone.utc)
        pub_iso = dp.astimezone(timezone.utc).strftime(ISO)
    elif guess_dt is not None:
        pub_iso = guess_dt.astimezone(timezone.utc).strftime(ISO)
    else:
        pub_iso = None

    authors = getattr(art, "authors", None)
    language = getattr(art, "language", None)

    extras = {
        "newsplease": {
            "date_download": str(getattr(art, "date_download", None)),
            "description": getattr(art, "description", None),
            "image_url": getattr(art, "image_url", None),
        }
    }

    return ArticleOut(
        source_id=source_id,
        source_domain=domain,
        url=url,
        title=title,
        content=content,
        published_at=pub_iso,
        published_at_source_tz=None,
        crawled_at=datetime.now(timezone.utc).strftime(ISO),
        language=language,
        authors=authors if isinstance(authors, list) else None,
        extras=extras,
    )


def save_article_tree(base_out: Path, art: ArticleOut) -> Path:
    dt = art.published_at or art.crawled_at
    dtp = dtparse.parse(dt)
    year, month, day = dtp.year, dtp.month, dtp.day

    h = hashlib.md5(art.url.encode("utf-8")).hexdigest()[:10]
    slug = slugify(art.title or "", h)
    ts = dtp.strftime("%Y%m%dT%H%M%SZ")
    outdir = base_out / art.source_id / f"{year:04d}" / f"{month:02d}" / f"{day:02d}"
    ensure_dir(outdir)
    outfile = outdir / f"{ts}_{slug}.json"

    with outfile.open("w", encoding="utf-8") as f:
        json.dump(asdict(art), f, ensure_ascii=False, indent=2)
    return outfile


def main():
    ap = argparse.ArgumentParser(description="Fetch financial news via news-please + RSS window filter (robust + detailed progress)")
    ap.add_argument("--sources", required=True, help="sources.json")
    ap.add_argument("--since", required=True, help="time window, e.g. 1h, 24h, 7d, 90m")
    ap.add_argument("--out", default="news", help="output dir (default: news)")
    ap.add_argument("--concurrency", type=int, default=8, help="parallel workers (default: 8)")
    ap.add_argument("--min-chars", type=int, default=400, help="min content length to save (default: 400)")
    ap.add_argument("--max-per-source", type=int, default=200, help="safety cap per source (default: 200)")
    ap.add_argument("--timeout", type=int, default=30, help="per-request socket timeout seconds (default: 30)")
    ap.add_argument("--progress", choices=["auto", "rich", "tqdm", "none"], default="auto", help="progress UI backend (default: auto)")
    ap.add_argument("--heartbeat", type=int, default=30, help="stderr heartbeat seconds for non-TTY (default: 30)")
    ap.add_argument("--error-log", default="news/errors.log", help="path to error log file (default: news/errors.log)")
    ap.add_argument("--trace", action="store_true", help="include tracebacks in error-log")
    ap.add_argument("--output-format", choices=["tree","per-source-json","per-source-jsonl"], default="per-source-json",
                    help="tree: dated tree files; per-source-json: one JSON with meta+items; per-source-jsonl: JSONL (meta line then items)")
    ap.add_argument("--feed-retries", type=int, default=2, help="number of retries for RSS fetching (default: 2)")
    ap.add_argument("--user-agent", default="finnews/1.0 (+https://localhost)", help="User-Agent for RSS HTTP requests")
    args = ap.parse_args()

    # global timeout to avoid stuck sockets inside underlying urllib
    socket.setdefaulttimeout(max(1, args.timeout))

    # prepare output + error log
    base_out = Path(args.out); ensure_dir(base_out)
    ensure_dir(Path(args.error_log).parent)
    err_fh = open(args.error_log, "a", encoding="utf-8")

    def _log_error(msg: str, exc: Optional[BaseException] = None):
        ts = datetime.now(timezone.utc).strftime(ISO)
        err_fh.write(f"[{ts}] {msg}\n")
        if args.trace and exc is not None:
            err_fh.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        err_fh.flush()

    since_td = parse_since(args.since)
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = now_utc - since_td
    print(f"[i] Time window: now={now_utc.strftime(ISO)}  cutoff={cutoff_utc.strftime(ISO)}  (since={args.since})")

    cfg = json.loads(Path(args.sources).read_text(encoding="utf-8"))
    sources = cfg.get("sources", [])
    sources_by_id = {s["id"]: s for s in sources}

    total_urls = 0
    per_source_urls: Dict[str, List[Tuple[str, Optional[datetime]]]] = {}

    # robust RSS collection with retries + UA + error logging
    for s in sources:
        sid = s["id"]
        if s.get("type") != "rss":
            print(f"[w] Source '{sid}' has unsupported type (only 'rss' here). Skipped.")
            continue
        urls = s.get("urls", [])
        items = collect_feed_urls(
            sid,
            urls,
            cutoff_utc,
            request_headers={"User-Agent": args.user_agent},
            retries=max(0, args.feed_retries),
            log_error=_log_error,
        )
        if args.max_per_source and len(items) > args.max_per_source:
            items = items[:args.max_per_source]
        per_source_urls[sid] = items
        total_urls += len(items)
        print(f"[i] {sid}: picked {len(items)} items within window")

    print(f"[i] Total URLs to process: {total_urls}")
    if total_urls == 0:
        print(json.dumps({"ok": 0, "failed": 0, "skipped": 0, "sources": {}}, ensure_ascii=False))
        err_fh.close()
        return 0

    # choose progress backend
    if args.progress == "rich":
        ui = "rich" if RICH_OK and sys.stderr.isatty() else "none"
    elif args.progress == "tqdm":
        ui = "tqdm" if TQDM_OK and sys.stderr.isatty() else "none"
    elif args.progress == "none":
        ui = "none"
    else:  # auto
        if RICH_OK and sys.stderr.isatty():
            ui = "rich"
        elif TQDM_OK and sys.stderr.isatty():
            ui = "tqdm"
        else:
            ui = "none"

    # stats & locks
    lock = Lock()
    started_by_source = defaultdict(int)
    done_by_source = defaultdict(int)
    ok_by_source = defaultdict(int)
    fail_by_source = defaultdict(int)
    skip_by_source = defaultdict(int)

    # aggregation for per-source outputs
    collected_by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)   # sid -> List[article dict]
    out_files: Dict[str, Path] = {}

    # Heartbeat for non-TTY
    last_hb = time.time()
    def maybe_heartbeat(done_total: int):
        nonlocal last_hb
        if ui != "none":
            return
        if time.time() - last_hb >= max(5, args.heartbeat):
            with lock:
                inprog = sum(started_by_source.values()) - sum(done_by_source.values())
                print(
                    f"[i] progress: {done_total}/{total_urls} done | in-flight={inprog} "
                    f"| ok={sum(ok_by_source.values())} | skip={sum(skip_by_source.values())} | fail={sum(fail_by_source.values())}",
                    file=sys.stderr, flush=True
                )
            last_hb = time.time()

    # build task list
    tasks: List[Tuple[str, str, Optional[datetime]]] = []
    for sid, items in per_source_urls.items():
        for url, dt_guess in items:
            tasks.append((sid, url, dt_guess))

    # progress objects
    start_ts = time.time()

    if ui == "rich":
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold]Total[/]"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("• ok:[green]{task.fields[ok]}[/] skip:[yellow]{task.fields[skip]}[/] fail:[red]{task.fields[fail]}[/]"),
            TextColumn("• rate:{task.fields[rate]:.2f}/s"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            transient=True,
        )
        per_source_progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.fields[sid]}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("• ok:[green]{task.fields[ok]}[/] skip:[yellow]{task.fields[skip]}[/] fail:[red]{task.fields[fail]}[/]"),
            transient=True,
        )
        progress.start()
        per_source_progress.start()

        total_task_id = progress.add_task(
            "total",
            total=total_urls,
            ok=0, skip=0, fail=0, rate=0.0
        )
        source_task_ids: Dict[str, int] = {}
        for sid, items in per_source_urls.items():
            source_task_ids[sid] = per_source_progress.add_task(
                "src",
                total=len(items),
                sid=sid, ok=0, skip=0, fail=0
            )
    elif ui == "tqdm":
        tbar = tqdm_cls(total=total_urls, desc="Total", unit="art")
        sbar: Dict[str, Any] = {}
        for sid, items in per_source_urls.items():
            sbar[sid] = tqdm_cls(total=len(items), desc=sid, unit="art", leave=False)
    else:
        # none
        pass

    # execution
    saved, failed, skipped = 0, 0, 0
    done_total = 0

    try:
        with futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            future_map = {ex.submit(
                lambda _sid, _url, _dtg: (
                    started_by_source.__setitem__(_sid, started_by_source[_sid] + 1) or None,
                    map_article(_sid, _url, _dtg)
                )[1],
                sid, url, dtg
            ): (sid, url) for (sid, url, dtg) in tasks}

            for fut in futures.as_completed(future_map):
                sid, url = future_map[fut]
                err: Optional[str] = None
                art: Optional[ArticleOut] = None
                try:
                    art = fut.result()
                except Exception as e:
                    err = repr(e)

                # update stats
                with lock:
                    done_by_source[sid] += 1
                    done_total += 1
                    elapsed = max(1e-3, time.time() - start_ts)
                    rate = done_total / elapsed

                    if err is not None:
                        fail_by_source[sid] += 1
                        failed += 1
                        _log_error(f"{sid} | {url} | ERROR: {err}")
                    else:
                        if (art is None) or (not art.content) or (len(art.content.strip()) < args.min_chars):
                            skip_by_source[sid] += 1
                            skipped += 1
                        else:
                            if args.output_format == "tree":
                                save_article_tree(base_out, art)
                            else:
                                collected_by_source[sid].append(asdict(art))
                            ok_by_source[sid] += 1
                            saved += 1

                    # progress UI updates
                    if ui == "rich":
                        # total
                        progress.update(
                            total_task_id,
                            advance=1,
                            ok=saved, skip=skipped, fail=failed,
                            rate=rate,
                        )
                        # per-source
                        tid = source_task_ids.get(sid)
                        if tid is not None:
                            per_source_progress.update(
                                tid,
                                advance=1,
                                ok=ok_by_source[sid],
                                skip=skip_by_source[sid],
                                fail=fail_by_source[sid],
                            )
                    elif ui == "tqdm":
                        tbar.update(1)
                        tbar.set_postfix(ok=saved, skip=skipped, fail=failed, rate=f"{rate:.2f}/s")
                        sbar[sid].update(1)
                        sbar[sid].set_postfix(ok=ok_by_source[sid], skip=skip_by_source[sid], fail=fail_by_source[sid])

                maybe_heartbeat(done_total)
    finally:
        # close progress
        if ui == "rich":
            try:
                progress.stop()
                per_source_progress.stop()
            except Exception:
                pass
        elif ui == "tqdm":
            try:
                tbar.close()
                for sb in sbar.values():
                    sb.close()
            except Exception:
                pass

    # write aggregated files if needed
    if args.output_format in ("per-source-json", "per-source-jsonl"):
        ensure_dir(base_out)
        host = socket.gethostname()
        now_str = datetime.now(timezone.utc).strftime(ISO)
        cutoff_str = cutoff_utc.strftime(ISO)

        for sid, items in collected_by_source.items():
            # sort: by published_at desc then crawled_at desc
            def _key(d):
                from dateutil import parser as _p
                pa = d.get("published_at") or ""
                ca = d.get("crawled_at") or ""
                try:
                    pa_dt = _p.parse(pa) if pa else _p.parse("1970-01-01T00:00:00Z")
                except Exception:
                    pa_dt = _p.parse("1970-01-01T00:00:00Z")
                try:
                    ca_dt = _p.parse(ca)
                except Exception:
                    ca_dt = _p.parse("1970-01-01T00:00:00Z")
                return (pa_dt, ca_dt)
            items.sort(key=_key, reverse=True)

            # filename: from config 'outfile' or default "<id>.json/.jsonl"
            custom_name = sources_by_id.get(sid, {}).get("outfile")
            if args.output_format == "per-source-jsonl":
                fname = custom_name or f"{sid}.jsonl"
            else:
                fname = custom_name or f"{sid}.json"
            outfile = base_out / fname
            out_files[sid] = outfile

            src_cfg = sources_by_id.get(sid, {})
            meta = {
                "source_id": sid,
                "timezone": src_cfg.get("timezone"),
                "urls": src_cfg.get("urls", []),
                "generated_at": now_str,
                "window": str(args.since),
                "cutoff_utc": cutoff_str,
                "now_utc": now_str,
                "picked": len(per_source_urls.get(sid, [])),
                "ok": ok_by_source[sid],
                "skipped": skip_by_source[sid],
                "failed": fail_by_source[sid],
                "hostname": host,
            }

            if args.output_format == "per-source-jsonl":
                # first line meta, then items, one json per line
                with outfile.open("w", encoding="utf-8") as f:
                    f.write(json.dumps({"meta": meta}, ensure_ascii=False) + "\n")
                    for obj in items:
                        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            else:
                # {"meta": {...}, "items": [ ... ]}
                payload = {"meta": meta, "items": items}
                with outfile.open("w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

    err_fh.close()

    # Final summary (also per source)
    summary_sources = {
        sid: {
            "picked": len(per_source_urls[sid]),
            "started": started_by_source[sid],
            "done": done_by_source[sid],
            "ok": ok_by_source[sid],
            "skip": skip_by_source[sid],
            "fail": fail_by_source[sid],
            # outfile имело бы смысл добавить, но мы его не собирали тут; можно доп. хранить при записи
        }
        for sid in per_source_urls.keys()
    }

    summary = {
        "ok": saved,
        "failed": failed,
        "skipped": skipped,
        "total": total_urls,
        "elapsed_sec": round(time.time() - start_ts, 3),
        "sources": summary_sources,
        "error_log": str(Path(args.error_log).resolve()),
        "output_format": args.output_format,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
