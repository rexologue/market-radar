#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, os, sys, time, re, tempfile, shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple
import httpx

# Категории и веса
CATS: Dict[str, float] = {
    "регуляторика/санкции/правовые риски": 1.0,
    "взломы/инциденты/остановки": 0.9,
    "существенные тех. прорывы/SOTA": 0.8,
    "крупные релизы/партнёрства/финансы": 0.7,
    "маркетинг/«шум»": 0.2,
}
CAT_KEYS = {k.lower(): k for k in CATS.keys()}

SYSTEM = (
    "Ты — финансовый аналитик. Суммаризируй новость по-русски и отнеси её к одной из 5 категорий.\n"
    "ОТВЕТЬ РОВНО ДВУМЯ СТРОКАМИ, без пояснений и кода:\n"
    "CATEGORY=<ОДНА категория из списка ниже, БЕЗ изменений формулировки>\n"
    "SUMMARY=<1–3 коротких предложения с выводом/прогнозом>\n\n"
    "Категории:\n"
    "регуляторика/санкции/правовые риски\n"
    "взломы/инциденты/остановки\n"
    "существенные тех. прорывы/SOTA\n"
    "крупные релизы/партнёрства/финансы\n"
    "маркетинг/«шум»"
)

CATEGORY_RE = re.compile(r"^\s*CATEGORY\s*=\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
SUMMARY_RE  = re.compile(r"^\s*SUMMARY\s*=\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

def write_json_atomic(path: Path, data: Any) -> None:
    """Записываем JSON атомарно: сначала во временный файл, потом replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(path.parent), suffix=".tmp") as tf:
        json.dump(data, tf, ensure_ascii=False, indent=2)
        tmp_name = tf.name
    os.replace(tmp_name, path)

def parse_model_output(txt: str) -> Tuple[str, str]:
    """Возвращает (category, summary) с приведением категории к каноническому виду; при сбое — фолбэки."""
    cat_m = CATEGORY_RE.search(txt)
    sum_m = SUMMARY_RE.search(txt)
    raw_cat = (cat_m.group(1).strip() if cat_m else "").lower()
    summary = (sum_m.group(1).strip() if sum_m else "").strip()

    # Приведение к каноническому ключу
    if raw_cat in CAT_KEYS:
        cat = CAT_KEYS[raw_cat]
    else:
        # Лёгкая эвристика
        lr = raw_cat
        if any(w in lr for w in ["регулятор", "санкц", "правов"]):
            cat = "регуляторика/санкции/правовые риски"
        elif any(w in lr for w in ["взлом", "инцидент", "останов", "outage", "даунтайм"]):
            cat = "взломы/инциденты/остановки"
        elif any(w in lr for w in ["sota", "прорыв", "бенчмарк"]):
            cat = "существенные тех. прорывы/SOTA"
        elif any(w in lr for w in ["релиз", "партнер", "партн", "финанс", "m&a"]):
            cat = "крупные релизы/партнёрства/финансы"
        else:
            cat = "маркетинг/«шум»"

    if not summary:
        summary = "Саммари не извлечено: модель вернула нестандартный формат ответа."
    return cat, summary

def call_llm(api_key: str, model: str, title: str, content: str, temperature: float, timeout: int) -> Tuple[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Заголовок: {title}\n\nТекст:\n{content or '(пусто)'}"}
        ],
        "temperature": temperature,
    }

    backoffs = [0, 1.5, 3.0]
    last_err = None
    with httpx.Client(timeout=timeout) as client:
        for t in backoffs:
            try:
                if t: time.sleep(t)
                r = client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                r.raise_for_status()
                txt = r.json()["choices"][0]["message"]["content"]
                return parse_model_output(txt)
            except Exception as e:
                last_err = e
    raise RuntimeError(f"LLM call failed after retries: {last_err}")

def process_file(in_path: Path, out_path: Path, api_key: str, model: str, temperature: float, timeout: int, verbose: bool) -> None:
    data = json.loads(in_path.read_text(encoding="utf-8"))
    items: List[Dict[str, Any]] = data.get("items", [])
    if not isinstance(items, list):
        if verbose: print(f"[WARN] {in_path.name}: items не список — пропуск", file=sys.stderr)
        write_json_atomic(out_path, data)
        return

    # Обрабатываем ПОЭЛЕМЕНТНО: получили ответ — сразу записали весь JSON (с уже обновлённой частью)
    for i, it in enumerate(items):
        title = it.get("title") or ""
        content = it.get("content") or ""
        try:
            cat, summ = call_llm(api_key, model, title, content, temperature, timeout)
            weight = CATS.get(cat, 0.2)
        except Exception as e:
            # Не падаем: вбиваем заглушки и идём дальше
            cat = "маркетинг/«шум»"
            weight = CATS[cat]
            summ = f"LLM error: {e}"

        # Обогащаем текущий элемент
        it["num"] = i
        it["summary"] = summ
        it["category"] = cat
        it["weight"] = weight

        # Немедленная запись
        write_json_atomic(out_path, data)
        if verbose:
            print(f"[OK] {in_path.name} item#{i}: {cat} (w={weight})", file=sys.stderr)

def collect_files(in_dir: Path, glob_patterns: str) -> List[Path]:
    files: List[Path] = []
    for pat in [p.strip() for p in glob_patterns.split(",") if p.strip()]:
        files.extend(sorted(in_dir.glob(pat)))
    # Уникализируем, сохраняем порядок
    seen = set()
    unique = []
    for f in files:
        if f not in seen and f.is_file():
            unique.append(f)
            seen.add(f)
    return unique

def main():
    ap = argparse.ArgumentParser(description="One-pass суммаризация: прочли → спросили LLM → сразу записали JSON.")
    ap.add_argument("--in-dir", required=True, help="Папка с исходными файлами.")
    ap.add_argument("--out-dir", required=True, help="Папка для сохранения обработанных файлов.")
    ap.add_argument("--model", default="openrouter/auto", help="ID модели в OpenRouter (например: meta-llama/llama-3.1-8b-instruct:free).")
    ap.add_argument("--api-key", help="Ключ OpenRouter (или env OPENROUTER_API_KEY).")
    ap.add_argument("--temperature", type=float, default=0.2, help="Температура генерации.")
    ap.add_argument("--timeout", type=int, default=60, help="Таймаут запроса к OpenRouter, сек.")
    ap.add_argument("--glob", default="*.json", help="Шаблоны файлов через запятую (по умолчанию: *.json).")
    ap.add_argument("--verbose", action="store_true", help="Подробные логи в stderr.")
    args = ap.parse_args()

    api_key = args.api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: задайте OPENROUTER_API_KEY или --api-key", file=sys.stderr)
        sys.exit(1)

    in_dir, out_dir = Path(args.in_dir), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = collect_files(in_dir, args.glob)
    if not files:
        print(f"В {in_dir} не найдены файлы по шаблону(ам): {args.glob}", file=sys.stderr)
        sys.exit(2)

    for f in files:
        try:
            process_file(f, out_dir / f.name, api_key, args.model, args.temperature, args.timeout, args.verbose)
        except Exception as e:
            # На уровне файла — логируем и идём дальше
            print(f"[ERROR] {f.name}: {e}", file=sys.stderr)

    if args.verbose:
        print(f"Готово: обработано файлов — {len(files)}", file=sys.stderr)

if __name__ == "__main__":
    main()
