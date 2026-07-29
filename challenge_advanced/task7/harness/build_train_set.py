#!/usr/bin/env python3
"""Сборка единого обучающего набора триажа из всех источников.

Источники:
  data/train_triage.jsonl - уже в формате чата {"messages": [...]}
  data/parts/*.jsonl      - плоский формат {"user":..., "assistant":{...}, "meta":{...}}

Что делает по шагам:
  1. Плоские строки переводит в формат чата. Системный промпт подставляется ОДНОЙ
     константой spec7.TRIAGE_SYSTEM_PROMPT - той же, что уходит на инференсе.
     Для строк, которые уже в формате чата, системное сообщение всё равно
     перезаписывается константой, иначе обучение и инференс могут разъехаться.
  2. Прогоняет каждый ответ ассистента через guards.check_reply. Что не прошло -
     выбрасывает. Учиться на примерах, которые не проходят собственный валидатор,
     смысла нет.
  3. Дедуп: сначала точные дубли по нормализованному тексту user, потом почти-дубли
     по коэффициенту Жаккара (порог 0.75). Из пары остаётся первый.
  4. Защита от утечки теста: выбрасывает всё, что похоже на любой пример из
     data/cases.jsonl по Жаккару с порогом 0.6. Без этого замеры на тесте
     обесцениваются.
  5. Пишет data/train_triage_full.jsonl и печатает распределение по маршрутам.

Запуск: python3 harness/build_train_set.py
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import guards
import spec7

TASK_ROOT = Path(HARNESS_DIR).parent
DEFAULT_CHAT_SRC = TASK_ROOT / "data" / "train_triage.jsonl"
DEFAULT_PARTS_DIR = TASK_ROOT / "data" / "parts"
DEFAULT_TEST_SRC = TASK_ROOT / "data" / "cases.jsonl"
DEFAULT_OUT = TASK_ROOT / "data" / "train_triage_full.jsonl"

NEAR_DUP_THRESHOLD = 0.75
TEST_LEAK_THRESHOLD = 0.6

TOKEN_PATTERN = re.compile(r"[0-9a-zа-яё]+")


def normalize(text: str) -> str:
    """Нижний регистр, ё -> е, только буквы и цифры, одиночные пробелы."""
    lowered = (text or "").lower().replace("ё", "е")
    return " ".join(TOKEN_PATTERN.findall(lowered))


def tokens_of(text: str) -> frozenset:
    return frozenset(normalize(text).split())


def jaccard(left: frozenset, right: frozenset) -> float:
    if not left or not right:
        return 0.0
    union = len(left | right)
    if union == 0:
        return 0.0
    return len(left & right) / union


def read_jsonl(path: Path) -> list:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((line_no, json.loads(line)))
            except json.JSONDecodeError as error:
                sys.exit(f"{path}:{line_no} не разбирается как JSON: {error}")
    return rows


def from_chat_row(row: dict, origin: str):
    """Достаёт user и assistant из строки формата {"messages": [...]}."""
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return None, f"{origin}: нет messages или меньше двух сообщений"
    user_text = None
    assistant_text = None
    for message in messages:
        role = message.get("role")
        if role == "user":
            user_text = message.get("content")
        elif role == "assistant":
            assistant_text = message.get("content")
    if not isinstance(user_text, str) or not user_text.strip():
        return None, f"{origin}: пустое сообщение user"
    if not isinstance(assistant_text, str):
        return None, f"{origin}: нет ответа assistant"
    return (user_text, assistant_text), None


def from_flat_row(row: dict, origin: str):
    """Достаёт user и assistant из плоской строки {"user":..., "assistant":{...}}."""
    user_text = row.get("user")
    assistant = row.get("assistant")
    if not isinstance(user_text, str) or not user_text.strip():
        return None, f"{origin}: пустое поле user"
    if not isinstance(assistant, dict):
        return None, f"{origin}: поле assistant не объект"
    return (user_text, json.dumps(assistant, ensure_ascii=False)), None


def load_sources(chat_src: Path, parts_dir: Path) -> list:
    """Собирает все источники в общий список записей одного вида."""
    records = []
    malformed = []

    if chat_src.exists():
        for line_no, row in read_jsonl(chat_src):
            origin = f"{chat_src.name}:{line_no}"
            pair, error = from_chat_row(row, origin)
            if pair is None:
                malformed.append(error)
                continue
            records.append({"origin": origin, "source": chat_src.name, "user": pair[0], "assistant": pair[1]})
    else:
        print(f"внимание: {chat_src} не найден, пропускаю")

    part_paths = sorted(parts_dir.glob("*.jsonl")) if parts_dir.exists() else []
    for path in part_paths:
        for line_no, row in read_jsonl(path):
            origin = f"{path.name}:{line_no}"
            pair, error = from_flat_row(row, origin)
            if pair is None:
                malformed.append(error)
                continue
            records.append({"origin": origin, "source": path.name, "user": pair[0], "assistant": pair[1]})

    return records, malformed, [path.name for path in part_paths]


def validate(records: list):
    """Шаг 2: оставляет только то, что проходит guards.check_reply."""
    kept = []
    dropped = []
    for record in records:
        result = guards.check_reply(record["assistant"])
        if not result.ok:
            dropped.append((record["origin"], result.violations))
            continue
        record["route"] = result.parsed.get("route")
        record["soft"] = list(result.violations)
        kept.append(record)
    return kept, dropped


def dedup(records: list, threshold: float):
    """Шаг 3: точные дубли по нормализованному user, затем почти-дубли по Жаккару."""
    exact_dropped = []
    seen_exact = {}
    after_exact = []
    for record in records:
        key = normalize(record["user"])
        if key in seen_exact:
            exact_dropped.append((record["origin"], seen_exact[key]))
            continue
        seen_exact[key] = record["origin"]
        record["tokens"] = frozenset(key.split())
        after_exact.append(record)

    near_dropped = []
    kept = []
    for record in after_exact:
        collision = None
        for earlier in kept:
            score = jaccard(record["tokens"], earlier["tokens"])
            if score >= threshold:
                collision = (earlier["origin"], score)
                break
        if collision is not None:
            near_dropped.append((record["origin"], collision[0], collision[1]))
            continue
        kept.append(record)

    return kept, exact_dropped, near_dropped


def load_test_tokens(test_src: Path) -> list:
    rows = read_jsonl(test_src)
    entries = []
    for line_no, row in rows:
        text = row.get("text")
        if not isinstance(text, str):
            sys.exit(f"{test_src}:{line_no} нет поля text")
        entries.append((row.get("id", f"line{line_no}"), tokens_of(text)))
    return entries


def drop_test_overlap(records: list, test_entries: list, threshold: float):
    """Шаг 4: выбрасывает всё, что пересекается с тестовым набором."""
    kept = []
    dropped = []
    max_kept = 0.0
    max_kept_pair = None
    for record in records:
        worst = 0.0
        worst_id = None
        for case_id, case_tokens in test_entries:
            score = jaccard(record["tokens"], case_tokens)
            if score > worst:
                worst = score
                worst_id = case_id
        if worst >= threshold:
            dropped.append((record["origin"], worst_id, worst))
            continue
        if worst > max_kept:
            max_kept = worst
            max_kept_pair = (record["origin"], worst_id)
        kept.append(record)
    return kept, dropped, max_kept, max_kept_pair


def build_messages(record: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": spec7.TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": record["user"]},
            {"role": "assistant", "content": record["assistant"]},
        ]
    }


def print_distribution(records: list) -> None:
    counts = Counter(record["route"] for record in records)
    total = len(records)
    for route in spec7.ROUTES:
        count = counts.get(route, 0)
        share = count / total * 100 if total else 0.0
        print(f"  {route:<12} {count:>4}  {share:5.1f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description="Сборка обучающего набора триажа")
    parser.add_argument("--chat-src", type=Path, default=DEFAULT_CHAT_SRC)
    parser.add_argument("--parts-dir", type=Path, default=DEFAULT_PARTS_DIR)
    parser.add_argument("--test-src", type=Path, default=DEFAULT_TEST_SRC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--near-dup", type=float, default=NEAR_DUP_THRESHOLD)
    parser.add_argument("--test-leak", type=float, default=TEST_LEAK_THRESHOLD)
    args = parser.parse_args()

    records, malformed, part_names = load_sources(args.chat_src, args.parts_dir)
    by_source = Counter(record["source"] for record in records)
    print("=== ШАГ 1: чтение источников ===")
    for name in sorted(by_source):
        print(f"  {name:<28} {by_source[name]:>5}")
    print(f"  {'ИТОГО на входе':<28} {len(records):>5}")
    if malformed:
        print(f"  битых строк пропущено: {len(malformed)}")
        for line in malformed[:10]:
            print(f"    {line}")
    print(f"  частей в {args.parts_dir.name}: {len(part_names)}")
    print()

    valid_records, invalid = validate(records)
    print("=== ШАГ 2: валидатор guards.check_reply ===")
    print(f"  прошло:   {len(valid_records)}")
    print(f"  выброшено: {len(invalid)}")
    if invalid:
        reasons = Counter()
        for _, violations in invalid:
            for code in violations:
                if not code.startswith(spec7.SOFT_PREFIX):
                    reasons[code] += 1
        for code, count in reasons.most_common():
            print(f"    {code:<28} {count:>4}")
        for origin, violations in invalid[:10]:
            print(f"    {origin}: {', '.join(violations)}")
    soft = sum(1 for record in valid_records if record["soft"])
    if soft:
        print(f"  прошло с мягкими замечаниями: {soft}")
    print()

    deduped, exact_dropped, near_dropped = dedup(valid_records, args.near_dup)
    print("=== ШАГ 3: дедуп ===")
    print(f"  точных дублей выброшено:      {len(exact_dropped)}")
    print(f"  почти-дублей (Жаккар >= {args.near_dup}): {len(near_dropped)}")
    print(f"  осталось:                     {len(deduped)}")
    for origin, first, score in near_dropped[:10]:
        print(f"    {origin} ~ {first}  {score:.3f}")
    print()

    test_entries = load_test_tokens(args.test_src)
    final, leaked, max_kept, max_kept_pair = drop_test_overlap(
        deduped, test_entries, args.test_leak
    )
    print("=== ШАГ 4: защита от утечки теста ===")
    print(f"  тестовых примеров в {args.test_src.name}: {len(test_entries)}")
    print(f"  выброшено за пересечение (Жаккар >= {args.test_leak}): {len(leaked)}")
    for origin, case_id, score in leaked[:20]:
        print(f"    {origin} ~ {case_id}  {score:.3f}")
    if max_kept_pair is not None:
        print(f"  максимальный Жаккар с тестом в итоговом наборе: {max_kept:.3f}"
              f"  ({max_kept_pair[0]} ~ {max_kept_pair[1]})")
    else:
        print("  максимальный Жаккар с тестом в итоговом наборе: 0.000")
    print()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for record in final:
            handle.write(json.dumps(build_messages(record), ensure_ascii=False) + "\n")

    print("=== ИТОГ ===")
    print(f"  на входе:  {len(records)}")
    print(f"  на выходе: {len(final)}")
    print(f"  файл: {args.out}")
    print("  распределение по маршрутам:")
    print_distribution(final)


if __name__ == "__main__":
    main()
