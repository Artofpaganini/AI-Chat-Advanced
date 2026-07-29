"""Проверка обучающего набора перед сдачей.

1. Все строки парсятся, ровно три сообщения с ролями system/user/assistant.
2. assistant проходит guards.check_reply без единого нарушения.
3. Системный промпт во всех строках равен spec7.TRIAGE_SYSTEM_PROMPT.
4. Непересечение с тестовым набором data/cases.jsonl: точное совпадение по
   нормализованному тексту и близость по коэффициенту Жаккара (порог 0.6).
5. Распределение по маршрутам совпадает с заказанным.
6. Матрица покрытия: возрастные полосы, типы подачи, структуры сообщения,
   плюс баланс тона (спокойные экстренные и панические не экстренные).
"""

import json
import os
import re
import sys
from collections import Counter

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HARNESS_DIR)
TEST_CASES_PATH = os.path.join(TASK_DIR, "data", "cases.jsonl")
TRAIN_PATH = os.path.join(TASK_DIR, "data", "train_triage.jsonl")

if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import guards
import spec7

from build_train import ROUTE_GROUPS, TARGET_COUNTS

PUNCT_PATTERN = re.compile(r"[^\w\s]", re.UNICODE)
SPACE_PATTERN = re.compile(r"\s+", re.UNICODE)
JACCARD_LIMIT = 0.6

BANDS = (
    "до 1 месяца",
    "1-3 месяца",
    "4-6 месяцев",
    "7-12 месяцев",
    "1-2 года",
    "3-5 лет",
    "не указан",
)

STYLES = (
    "спокойное описание",
    "паника капсом",
    "ночное сбивчивое",
    "три слова",
    "длинный абзац",
    "опечатки",
    "за подругу",
    "бабушка",
    "повторное обращение",
)

STRUCTURES = (
    "один симптом",
    "несколько симптомов",
    "плюс посторонний вопрос",
    "отрицание в начале",
    "флаг в конце",
    "прошедшее время",
    "уже дал лекарство",
    "вопрос без симптомов",
)

TONES = ("спокойный", "обычный", "паника")

MIN_CALM_EMERGENCY = 15
MIN_PANIC_NOT_EMERGENCY = 15


def normalize(text):
    lowered = text.lower().replace("ё", "е")
    without_punct = PUNCT_PATTERN.sub(" ", lowered)
    return SPACE_PATTERN.sub(" ", without_punct).strip()


def words(text):
    return set(normalize(text).split())


def jaccard(left, right):
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            rows.append((number, json.loads(stripped)))
    return rows


def print_table(title, keys, counter):
    print(f"\n{title}")
    for key in keys:
        print(f"  {key:<24} {counter.get(key, 0):>3}")


def check_tags(problems):
    """Разметка покрытия живёт в файлах кейсов, её проверяем отдельно от jsonl."""
    band_counter = Counter()
    style_counter = Counter()
    structure_counter = Counter()
    tone_counter = Counter()
    calm_emergency = 0
    panic_not_emergency = 0
    per_route_band = {}

    for route, cases in ROUTE_GROUPS:
        per_route_band[route] = Counter()
        for index, case in enumerate(cases, start=1):
            where = f"{route} #{index}"
            band = case.get("band")
            style = case.get("style")
            structure = case.get("structure")
            tone = case.get("tone")
            if band not in BANDS:
                problems.append(f"{where}: неизвестная полоса возраста {band!r}")
            if style not in STYLES:
                problems.append(f"{where}: неизвестный тип подачи {style!r}")
            if structure not in STRUCTURES:
                problems.append(f"{where}: неизвестная структура {structure!r}")
            if tone not in TONES:
                problems.append(f"{where}: неизвестный тон {tone!r}")
            age = case.get("age_months")
            if (band == "не указан") != (age is None):
                problems.append(f"{where}: band={band!r} не согласован с age_months={age!r}")
            band_counter[band] += 1
            style_counter[style] += 1
            structure_counter[structure] += 1
            tone_counter[tone] += 1
            per_route_band[route][band] += 1
            if route == spec7.ROUTE_EMERGENCY and tone == "спокойный":
                calm_emergency += 1
            if route != spec7.ROUTE_EMERGENCY and tone == "паника":
                panic_not_emergency += 1

    print_table("покрытие по возрасту:", BANDS, band_counter)
    print_table("покрытие по типу подачи:", STYLES, style_counter)
    print_table("покрытие по структуре сообщения:", STRUCTURES, structure_counter)
    print_table("тон сообщения:", TONES, tone_counter)

    for key, counter in (("возраст", band_counter), ("подача", style_counter), ("структура", structure_counter)):
        expected = {"возраст": BANDS, "подача": STYLES, "структура": STRUCTURES}[key]
        for value in expected:
            if counter.get(value, 0) == 0:
                problems.append(f"{key}: значение {value!r} не покрыто ни одним примером")

    print(f"\nспокойных EMERGENCY: {calm_emergency} (нужно не меньше {MIN_CALM_EMERGENCY})")
    print(f"панических не EMERGENCY: {panic_not_emergency} (нужно не меньше {MIN_PANIC_NOT_EMERGENCY})")
    if calm_emergency < MIN_CALM_EMERGENCY:
        problems.append(f"спокойных EMERGENCY только {calm_emergency}")
    if panic_not_emergency < MIN_PANIC_NOT_EMERGENCY:
        problems.append(f"панических не EMERGENCY только {panic_not_emergency}")

    print("\nвозрастные полосы по маршрутам:")
    header = "  маршрут      " + "".join(f"{band:>14}" for band in BANDS)
    print(header)
    for route, _ in ROUTE_GROUPS:
        row = f"  {route:<13}" + "".join(f"{per_route_band[route].get(band, 0):>14}" for band in BANDS)
        print(row)


def main():
    problems = []
    train_rows = load_jsonl(TRAIN_PATH)
    total_target = sum(TARGET_COUNTS.values())
    print(f"строк в наборе: {len(train_rows)}")
    if len(train_rows) != total_target:
        problems.append(f"ожидалось {total_target} строк, получено {len(train_rows)}")

    route_counts = {route: 0 for route in spec7.ROUTES}
    clean_replies = 0
    train_texts = []

    for number, row in train_rows:
        messages = row.get("messages")
        if not isinstance(messages, list) or len(messages) != 3:
            problems.append(f"строка {number}: не три сообщения")
            continue
        roles = [message.get("role") for message in messages]
        if roles != ["system", "user", "assistant"]:
            problems.append(f"строка {number}: роли {roles}")
            continue
        if messages[0]["content"] != spec7.TRIAGE_SYSTEM_PROMPT:
            problems.append(f"строка {number}: системный промпт отличается от TRIAGE_SYSTEM_PROMPT")
        user_text = messages[1]["content"]
        train_texts.append((number, user_text))
        if not user_text.strip():
            problems.append(f"строка {number}: пустое сообщение родителя")

        result = guards.check_reply(messages[2]["content"])
        if result.violations:
            problems.append(f"строка {number}: нарушения {result.violations}")
            continue
        if not result.ok:
            problems.append(f"строка {number}: check_reply вернул ok=False")
            continue
        clean_replies += 1
        route_counts[result.parsed["route"]] += 1

    print(f"чистых по check_reply: {clean_replies} из {len(train_rows)}")
    print("\nраспределение по маршрутам:")
    for route in spec7.ROUTES:
        target = TARGET_COUNTS[route]
        mark = "ok" if route_counts[route] == target else "MISMATCH"
        print(f"  {route:<12} {route_counts[route]:>3} (заказано {target}) {mark}")
        if route_counts[route] != target:
            problems.append(f"{route}: {route_counts[route]} вместо {target}")

    test_rows = load_jsonl(TEST_CASES_PATH)
    test_texts = [(row["id"], row["text"]) for _, row in test_rows]
    test_normalized = {normalize(text): case_id for case_id, text in test_texts if text.strip()}
    test_words = [(case_id, words(text)) for case_id, text in test_texts if text.strip()]

    max_jaccard = 0.0
    max_pair = ("", "")
    for number, text in train_texts:
        norm = normalize(text)
        if norm in test_normalized:
            problems.append(f"строка {number}: точное совпадение с тестовым {test_normalized[norm]}")
        train_word_set = words(text)
        for case_id, test_word_set in test_words:
            value = jaccard(train_word_set, test_word_set)
            if value > max_jaccard:
                max_jaccard = value
                max_pair = (f"строка {number}", case_id)
            if value >= JACCARD_LIMIT:
                problems.append(
                    f"строка {number}: Жаккар {value:.3f} с тестовым {case_id}, порог {JACCARD_LIMIT}"
                )

    print(f"\nмаксимальный коэффициент Жаккара с тестом: {max_jaccard:.3f} ({max_pair[0]} - {max_pair[1]})")

    duplicates = {}
    for number, text in train_texts:
        duplicates.setdefault(normalize(text), []).append(number)
    for _, numbers in duplicates.items():
        if len(numbers) > 1:
            problems.append(f"дубликат внутри набора: строки {numbers}")

    check_tags(problems)

    if problems:
        print("\nПРОБЛЕМЫ:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nВсе проверки пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
