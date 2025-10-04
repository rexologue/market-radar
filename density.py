#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from dateutil import parser as dtparser
from tqdm import tqdm

# --------- Параметры по умолчанию ---------
DEFAULT_MODEL_ID = "BAAI/bge-m3"  # сильная мульти-языковая модель
DEFAULT_TITLE_SCORE = 0.7
DEFAULT_CONTENT_SCORE = 0.3
DEFAULT_CONTENT_CHARS = 300
DEFAULT_WINDOW_HOURS = 24
DEFAULT_BATCH_SIZE = 64


# --------- Утиль ---------
def to_dt_utc(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = dtparser.parse(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def best_time(published_at: Optional[str], crawled_at: Optional[str]) -> datetime:
    p = to_dt_utc(published_at)
    c = to_dt_utc(crawled_at)
    return p or c or datetime.now(timezone.utc)


STRIP_TAGS_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean_text(s: str) -> str:
    s = STRIP_TAGS_RE.sub(" ", s)
    s = WS_RE.sub(" ", s).strip()
    return s


def lead(text: str, max_chars: int) -> str:
    if not text:
        return ""
    t = clean_text(text)
    parts = re.split(r"(?<=[.!?])\s+", t)
    t = " ".join(parts[:2])  # первые 1-2 предложения
    if len(t) > max_chars:
        t = t[:max_chars]
    return t


def l2_normalize(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n = np.maximum(n, eps)
    return x / n


@dataclass
class Item:
    # Глобальный индекс в общем массиве
    global_idx: int
    # Идентификаторы исходника
    source_id: str
    # Индекс внутри items исходного файла (то, что просил "num")
    num: int
    # Полезные поля для эмбеддинга/времени
    title: str
    content: str
    published_at: Optional[str]
    crawled_at: Optional[str]

    # вычисляется позже
    dt_utc: datetime = None  # type: ignore


# --------- Модель ---------
_MODEL = None


def has_cuda() -> bool:
    try:
        import torch  # noqa
        import torch.cuda  # noqa

        return torch.cuda.is_available()
    except Exception:
        return False


def get_model(model_id: str, model_path: Optional[str]) -> Any:
    """
    Если указан model_path:
      - если это директория с моделью → грузим локально
      - иначе → используем как cache_folder для загрузки model_id
    """
    from sentence_transformers import SentenceTransformer

    device = "cuda" if has_cuda() else "cpu"

    if model_path:
        p = Path(model_path)
        p.mkdir(parents=True, exist_ok=True)
        # попытка загрузить локальную модель (если реально лежит)
        # эвристика: наличие конфигурационных файлов
        local_files = {"config.json", "modules.json", "model.safetensors", "pytorch_model.bin"}
        exists_local = any((p / f).exists() for f in local_files) or any(p.glob("**/config.json"))
        if exists_local:
            model = SentenceTransformer(str(p), device=device)
        else:
            # скачаем модель в указанный кэш
            model = SentenceTransformer(model_id, cache_folder=str(p), device=device)
    else:
        model = SentenceTransformer(model_id, device=device)

    return model


def encode_texts(
    model: Any,
    titles: List[str],
    contents: List[str],
    title_score: float,
    content_score: float,
    batch_size: int,
) -> np.ndarray:
    """
    Кодируем отдельно title и content с префиксом 'passage: ' (как у E5/BGE),
    потом взвешенно складываем и L2-нормализуем.
    """
    # Пустые строки закодируются, но вес для них будет 0
    titles_p = [("passage: " + t) if t else "" for t in titles]
    contents_p = [("passage: " + c) if c else "" for c in contents]

    # Закодировать
    e_title = model.encode(
        titles_p,
        batch_size=batch_size,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    e_content = model.encode(
        contents_p,
        batch_size=batch_size,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    # Веса: если пусто — нулевой вес
    w_t = np.array([title_score if bool(t) else 0.0 for t in titles], dtype=np.float32)[:, None]
    w_c = np.array([content_score if bool(c) else 0.0 for c in contents], dtype=np.float32)[:, None]
    w_sum = w_t + w_c
    # чтобы избежать деления на ноль
    w_sum = np.where(w_sum == 0.0, 1.0, w_sum)

    combined = (w_t * e_title + w_c * e_content) / w_sum
    combined = l2_normalize(combined)
    return combined


# --------- Загрузка данных ---------
def load_items(input_dirs: List[Path]) -> Tuple[List[Item], Dict[int, Tuple[Path, int]]]:
    """
    Читаем все json-файлы (каждый файл = источник).
    Возвращаем список Item и карту глобального индекса -> (путь_файла, локальный_индекс).
    """
    items: List[Item] = []
    trace: Dict[int, Tuple[Path, int]] = {}  # global_idx -> (file_path, local_num)

    gid = 0
    for d in input_dirs:
        if not d.exists():
            continue
        files = []
        if d.is_file() and d.suffix.lower() == ".json":
            files = [d]
        else:
            files = sorted([p for p in d.rglob("*.json") if p.is_file()])

        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[WARN] skip {f}: {e}")
                continue

            meta = data.get("meta", {})
            default_source_id = meta.get("source_id", "")
            arr = data.get("items", [])
            for local_idx, it in enumerate(arr):
                source_id = it.get("source_id") or default_source_id or ""
                title = it.get("title") or ""
                content = it.get("content") or ""

                published_at = it.get("published_at")
                crawled_at = it.get("crawled_at")
                dt = best_time(published_at, crawled_at)

                item = Item(
                    global_idx=gid,
                    source_id=source_id,
                    num=local_idx,
                    title=title,
                    content=content,
                    published_at=published_at,
                    crawled_at=crawled_at,
                    dt_utc=dt,
                )
                items.append(item)
                trace[gid] = (f, local_idx)
                gid += 1

    return items, trace


# --------- Группировка по 24-часовым окнам (UTC) ---------
def day_bucket(dt: datetime) -> str:
    # Начало суток по UTC
    day = dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    return day


def group_by_window(items: List[Item], window_hours: int = 24) -> Dict[str, List[int]]:
    """
    Простая реализация: бьём по календарным дням UTC.
    (Если нужно сдвигать окно — легко добавить параметр сдвига)
    """
    groups: Dict[str, List[int]] = {}
    for it in items:
        key = day_bucket(it.dt_utc) if window_hours == 24 else day_bucket(it.dt_utc)
        groups.setdefault(key, []).append(it.global_idx)
    return groups


# --------- Подсчёт "density score" (через среднюю дистанцию) ---------
def compute_window_scores(
    idxs: List[int],
    items: List[Item],
    emb: np.ndarray,
    window_hours: int,
) -> Dict[int, float]:
    """
    Для списка глобальных индексов внутри окна:
      1) считаем все косинусные дистанции d = 1 - cos
      2) исключаем пары из одного source_id и self
      3) берём среднюю дистанцию по каждой строке
      4) нормализуем средние дистанции внутри окна в [0,1]
      5) value = 1 - norm(mean_distance)

    Возвращает mapping: global_idx -> value (float в [0,1])
    """
    if len(idxs) == 0:
        return {}

    # Сформируем матрицу эмбеддингов окна
    W = emb[idxs, :]  # [n, d], уже L2-нормализованные
    n = W.shape[0]
    if n == 1:
        # Один элемент в окне → нет соседей
        return {idxs[0]: 0.0}

    # Грам-матрица сходств
    # cos(i,j) = W_i · W_j (т.к. нормированы)
    sim = np.clip(W @ W.T, -1.0, 1.0)  # [n, n]
    dist = 1.0 - sim                   # косинусная дистанция

    # Маска "разрешённых" пар: не сравниваем self и одинаковые source_id
    srcs = [items[i].source_id for i in idxs]
    srcs_arr = np.array(srcs, dtype=object)
    same_src = (srcs_arr[:, None] == srcs_arr[None, :])  # [n, n]
    mask = ~same_src
    np.fill_diagonal(mask, False)

    # Средняя дистанция по каждой строке, только по True в mask
    mean_dist = np.zeros(n, dtype=np.float32)
    valid = np.zeros(n, dtype=bool)
    for i in range(n):
        row_mask = mask[i]
        vals = dist[i, row_mask]
        if vals.size > 0:
            mean_dist[i] = float(vals.mean())
            valid[i] = True
        else:
            mean_dist[i] = np.nan
            valid[i] = False

    # Нормализация по окну
    if np.any(valid):
        md_valid = mean_dist[valid]
        lo = float(np.min(md_valid))
        hi = float(np.max(md_valid))
        if hi > lo:
            norm = (mean_dist - lo) / (hi - lo)
        else:
            norm = np.zeros_like(mean_dist)
        # value = 1 - norm(mean_distance)
        value = 1.0 - norm
        # На NaN (без соседей) поставим 0.0
        value = np.where(np.isfinite(value), value, 0.0)
    else:
        # Нет валидных пар
        value = np.zeros(n, dtype=np.float32)

    # Соберём в словарь: global_idx -> value
    out = {idxs[i]: float(value[i]) for i in range(n)}
    return out


# --------- Главная ---------
def main():
    ap = argparse.ArgumentParser(
        description="Вычисляет 'оценку плотности' новости по средним косинусным дистанциям внутри 24-часовых окон."
    )
    ap.add_argument("--in", dest="inputs", action="append", required=True,
                    help="Путь к папке или файлу JSON. Можно указывать несколько раз.")
    ap.add_argument("--out", dest="out_json", default="density_scores.json",
                    help="Путь для итогового JSON.")
    ap.add_argument("--model-id", dest="model_id", default=DEFAULT_MODEL_ID,
                    help=f"HuggingFace id модели (по умолчанию {DEFAULT_MODEL_ID}).")
    ap.add_argument("--model-path", dest="model_path", default=None,
                    help="Папка для локальной модели/кэша. Если пуста — модель скачается сюда, если уже есть — загрузится локально.")
    ap.add_argument("--title-score", dest="title_score", type=float, default=DEFAULT_TITLE_SCORE,
                    help=f"Вес заголовка (по умолчанию {DEFAULT_TITLE_SCORE}).")
    ap.add_argument("--content-score", dest="content_score", type=float, default=DEFAULT_CONTENT_SCORE,
                    help=f"Вес контента (по умолчанию {DEFAULT_CONTENT_SCORE}).")
    ap.add_argument("--content-chars", dest="content_chars", type=int, default=DEFAULT_CONTENT_CHARS,
                    help=f"Сколько символов брать из контента (по умолчанию {DEFAULT_CONTENT_CHARS}).")
    ap.add_argument("--window-hours", dest="window_hours", type=int, default=DEFAULT_WINDOW_HOURS,
                    help=f"Ширина окна в часах (по умолчанию {DEFAULT_WINDOW_HOURS}; разбиение по суткам UTC).")
    ap.add_argument("--batch-size", dest="batch_size", type=int, default=DEFAULT_BATCH_SIZE,
                    help=f"Размер батча при кодировании (по умолчанию {DEFAULT_BATCH_SIZE}).")
    args = ap.parse_args()

    input_dirs = [Path(p) for p in args.inputs]
    items, _trace = load_items(input_dirs)

    if not items:
        print("Нет новостей для обработки.")
        # Запишем пустой JSON, чтобы пайплайн не падал
        Path(args.out_json).write_text(json.dumps({"scores": [], "total_items": 0}, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    # Подготовим тексты для эмбеддингов
    titles = [clean_text(it.title) for it in items]
    contents = [lead(it.content, max_chars=args.content_chars) for it in items]

    # Загрузим/инициализируем модель
    model = get_model(args.model_id, args.model_path)

    # Кодируем и получаем эмбеддинги (уже L2-нормированные)
    print(f"Encoding {len(items)} items with model: {args.model_id} "
          f"(cache/local: {args.model_path or '[hf default cache]'}).")
    emb = encode_texts(
        model=model,
        titles=titles,
        contents=contents,
        title_score=args.title_score,
        content_score=args.content_score,
        batch_size=args.batch_size,
    )

    # Группируем по 24-часовым окнам (UTC-сутки)
    groups = group_by_window(items, window_hours=args.window_hours)

    # Считаем значения для каждого окна и собираем
    values: Dict[int, float] = {}
    for gkey, idxs in tqdm(groups.items(), desc="Windows"):
        # внутри окна считаем средние дистанции (исключаем пары одного source_id), нормализуем, value = 1 - norm_dist
        win_scores = compute_window_scores(idxs, items, emb, args.window_hours)
        values.update(win_scores)

    # Сформировать итог
    out_scores = []
    for it in items:
        v = float(values.get(it.global_idx, 0.0))
        out_scores.append({
            "source_id": it.source_id,
            "num": it.num,     # индекс внутри items данного файла-источника
            "value": round(v, 6)
        })

    out = {
        "model_id": args.model_id,
        "model_path": args.model_path,
        "title_score": args.title_score,
        "content_score": args.content_score,
        "content_chars": args.content_chars,
        "window_hours": args.window_hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_items": len(items),
        "scores": out_scores,
    }
    Path(args.out_json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done. Wrote {args.out_json} with {len(out_scores)} rows.")
    

if __name__ == "__main__":
    main()
