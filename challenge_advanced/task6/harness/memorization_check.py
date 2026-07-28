# -*- coding: utf-8 -*-
"""Проверка на запоминание: читает ли дообученная модель цифры из входа или помнит их из обучения.

Берёт примеры из artifacts/train.jsonl (модель их ВИДЕЛА при обучении), подменяет в блоке
[child_context] все числовые поля на заведомо другие правдоподобные значения и гонит
изменённый промпт через модель. Дальше смотрит, какие числа приехали в ответ:
новые (модель читает вход) или старые из обучающего примера (модель запомнила).

Правила подмены: возраст остаётся в 0-36 месяцев, но отличается минимум на 6; вес и рост
меняются на 10-25%; баллы (*_score и family_battery) уходят в другое значение 0-100 с разницей
минимум 15; срок беременности остаётся в неделях 32-41 с разницей минимум 3. Строковые поля
вроде gender не трогаются, целые остаются целыми.

Числа в ответе ищутся по границе числа, поэтому 12 не находится внутри 120 или 112.
Значение не идёт в подсчёт, если оно столкнулось со значением другого поля с другой стороны
(одна и та же строка и в старых, и в новых - её не приписать никому), если это число и так
есть в реплике родителя (модель могла просто повторить её), или если оно меньше 10: такую
цифру не отличить от бытовых «2 часа» и «5 раз». Отбор идёт по значению, а не по полю: если
старое значение шумное, а новое чистое, новое всё равно считается. Поля, у которых хотя бы
одна сторона выпала, перечислены в ambiguous_fields. По той же причине подстановка внутри
разрешённого диапазона предпочитает значения от 10.

Схема прогона повторяет mlx_generate.py: apply_chat_template с system из примера, флаг --thinking,
sampler с температурой 0, то есть greedy. Блок <think>...</think> в анализ чисел не идёт.

Режим --dry-run модель не грузит: показывает подстановки для первых трёх примеров.

Запуск: /private/tmp/claude-503/-Users-Victor/73faef96-e5bc-4be5-9599-8edbcd893e7e/scratchpad/mlxenv/bin/python harness/memorization_check.py --model mlx-community/Qwen3-1.7B-4bit --dry-run
        /private/tmp/claude-503/-Users-Victor/73faef96-e5bc-4be5-9599-8edbcd893e7e/scratchpad/mlxenv/bin/python harness/memorization_check.py --model mlx-community/Qwen3-1.7B-4bit --n 10
        /private/tmp/claude-503/-Users-Victor/73faef96-e5bc-4be5-9599-8edbcd893e7e/scratchpad/mlxenv/bin/python harness/memorization_check.py --model mlx-community/Qwen3-1.7B-4bit --adapter-path adapters --n 10
"""

import argparse
import json
import os
import random
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HARNESS_DIR)
ARTIFACTS_DIR = os.path.join(TASK_DIR, "artifacts")
RESULTS_DIR = os.path.join(TASK_DIR, "results")

if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

try:
    import spec
except ImportError:
    spec = None

CHILD_CONTEXT_OPEN = getattr(spec, "CHILD_CONTEXT_OPEN", "[child_context]")
CHILD_CONTEXT_CLOSE = getattr(spec, "CHILD_CONTEXT_CLOSE", "[/child_context]")
SPEC_SYSTEM_PROMPT = getattr(spec, "SYSTEM_PROMPT", None)

SOURCE_FILE_NAME = "train.jsonl"
OUTPUT_FILE_NAME = "memorization_check.jsonl"

DEFAULT_EXAMPLES = 10
DEFAULT_SEED = 42
DEFAULT_MAX_TOKENS = 900
TEMPERATURE = 0.0

THINKING_OFF = "off"
THINKING_ON = "on"
THINKING_AUTO = "auto"
THINKING_CHOICES = (THINKING_OFF, THINKING_ON, THINKING_AUTO)
THINKING_FLAGS = {THINKING_OFF: False, THINKING_ON: True}

ADAPTER_CONFIG_FILE = "adapter_config.json"
ADAPTER_WEIGHTS_FILE = "adapters.safetensors"

AGE_FIELD = "age_months"
AGE_MIN = 0
AGE_MAX = 36
AGE_MIN_DELTA = 6

SCORE_SUFFIX = "_score"
SCORE_EXTRA_FIELDS = ("family_battery",)
SCORE_MIN = 0
SCORE_MAX = 100
SCORE_MIN_DELTA = 15

SIZE_MARKERS = ("weight", "height", "length_cm")
SIZE_MIN_RATIO = 0.10
SIZE_MAX_RATIO = 0.25

PREGNANCY_FIELD = "pregnancy_length"
PREGNANCY_MIN = 32
PREGNANCY_MAX = 41
PREGNANCY_MIN_DELTA = 3

GENERIC_RATIO = 0.30
MIN_UNAMBIGUOUS_VALUE = 10
SUBSTITUTION_ATTEMPTS = 12

VERDICT_READS = "reads_input"
VERDICT_MEMORIZED = "memorized"
VERDICT_MIXED = "mixed"
VERDICT_NONE = "no_numbers"
VERDICT_ORDER = (VERDICT_READS, VERDICT_MEMORIZED, VERDICT_MIXED, VERDICT_NONE)

MEMORIZATION_ALERT_RATIO = 0.30

DRY_RUN_PREVIEW = 3
MILLISECONDS_IN_SECOND = 1000.0
STATUS_ERROR_CHARS = 60

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2

_CONTEXT_RE = re.compile(
    re.escape(CHILD_CONTEXT_OPEN) + r"(.*?)" + re.escape(CHILD_CONTEXT_CLOSE),
    re.DOTALL,
)
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class SourceDatasetError(Exception):
    """Исходный jsonl не соответствует контракту или в нём нет примеров с child_context."""


class ModelLoadError(Exception):
    """Модель или адаптер не удалось загрузить."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Тест на запоминание: подменяет цифры в child_context и смотрит, "
        "какие числа модель вернёт в ответе.",
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--adapter-path", dest="adapter_path", default=None)
    parser.add_argument("--n", type=int, default=DEFAULT_EXAMPLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--source", dest="source_path", default=None)
    parser.add_argument("--out", dest="out_path", default=None)
    parser.add_argument("--max-tokens", dest="max_tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--thinking", choices=list(THINKING_CHOICES), default=THINKING_OFF)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    return parser


def describe_thinking(thinking_mode: str) -> str:
    if thinking_mode == THINKING_AUTO:
        return "auto (параметр не передаётся, как решит токенизатор)"
    return "%s (enable_thinking=%s)" % (thinking_mode, THINKING_FLAGS[thinking_mode])


def resolve_source_path(raw_value: Optional[str]) -> str:
    if raw_value:
        return os.path.abspath(raw_value)
    return os.path.join(ARTIFACTS_DIR, SOURCE_FILE_NAME)


def resolve_out_path(raw_value: Optional[str]) -> str:
    if raw_value:
        return os.path.abspath(raw_value)
    return os.path.join(RESULTS_DIR, OUTPUT_FILE_NAME)


def resolve_adapter_path(raw_value: Optional[str]) -> Optional[str]:
    if not raw_value:
        return None
    return os.path.abspath(raw_value)


def extract_role(messages: List[Dict[str, Any]], role: str) -> Optional[str]:
    for message in messages:
        if isinstance(message, dict) and message.get("role") == role:
            content = message.get("content")
            if isinstance(content, str):
                return content
    return None


def is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def format_number(value: Any) -> str:
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return "%g" % value


def parse_context(user: str) -> Optional[Tuple[Dict[str, Any], Tuple[int, int], str]]:
    match = _CONTEXT_RE.search(user)
    if match is None:
        return None
    try:
        payload = json.loads(match.group(1).strip())
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    if not any(is_number(value) for value in payload.values()):
        return None
    parent_text = user[: match.start()] + user[match.end() :]
    return payload, (match.start(), match.end()), parent_text


def load_source_examples(source_path: str) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    skipped = 0
    with open(source_path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except ValueError as parse_error:
                raise SourceDatasetError(
                    "Строка %d в %s не парсится как JSON: %s"
                    % (line_number + 1, source_path, parse_error)
                )
            messages = record.get("messages")
            if not isinstance(messages, list) or not messages:
                raise SourceDatasetError(
                    "Строка %d в %s без ключа messages" % (line_number + 1, source_path)
                )
            user_text = extract_role(messages, "user")
            if user_text is None:
                raise SourceDatasetError(
                    "Строка %d в %s без роли user" % (line_number + 1, source_path)
                )
            parsed = parse_context(user_text)
            if parsed is None:
                skipped += 1
                continue
            payload, span, parent_text = parsed
            system_text = extract_role(messages, "system")
            if system_text is None:
                system_text = SPEC_SYSTEM_PROMPT
            examples.append(
                {
                    "index": line_number,
                    "system": system_text,
                    "user": user_text,
                    "payload": payload,
                    "span": span,
                    "parent_text": parent_text,
                }
            )
    if not examples:
        raise SourceDatasetError(
            "В %s нет ни одного примера с разбираемым блоком %s и числами внутри "
            "(пропущено строк: %d)" % (source_path, CHILD_CONTEXT_OPEN, skipped)
        )
    return examples


def select_examples(
    examples: List[Dict[str, Any]], limit: int, seed: int
) -> List[Dict[str, Any]]:
    if limit >= len(examples):
        return list(examples)
    rng = random.Random(seed)
    chosen = rng.sample(range(len(examples)), limit)
    chosen.sort()
    return [examples[position] for position in chosen]


def keep_type(old_value: Any, new_value: float) -> Any:
    if isinstance(old_value, int):
        return int(round(new_value))
    return round(float(new_value), 1)


def pick_from_range(
    old_value: Any, low: int, high: int, min_delta: int, rng: random.Random
) -> Any:
    candidates = [
        candidate
        for candidate in range(low, high + 1)
        if abs(candidate - float(old_value)) >= min_delta
    ]
    if not candidates:
        return shift_by_ratio(old_value, GENERIC_RATIO, GENERIC_RATIO, rng)
    readable = [candidate for candidate in candidates if candidate >= MIN_UNAMBIGUOUS_VALUE]
    if readable:
        candidates = readable
    return keep_type(old_value, rng.choice(candidates))


def shift_by_ratio(
    old_value: Any, low_ratio: float, high_ratio: float, rng: random.Random
) -> Any:
    ratio = rng.uniform(low_ratio, high_ratio)
    delta = abs(float(old_value)) * ratio
    if isinstance(old_value, int):
        delta = max(1.0, round(delta))
    elif delta == 0:
        delta = 1.0
    direction = rng.choice((-1, 1))
    shifted = float(old_value) + direction * delta
    if shifted <= 0:
        shifted = float(old_value) + delta
    return keep_type(old_value, shifted)


def substitute_value(field: str, old_value: Any, rng: random.Random) -> Any:
    lowered = field.lower()
    if lowered == AGE_FIELD:
        return pick_from_range(old_value, AGE_MIN, AGE_MAX, AGE_MIN_DELTA, rng)
    if lowered == PREGNANCY_FIELD:
        return pick_from_range(
            old_value, PREGNANCY_MIN, PREGNANCY_MAX, PREGNANCY_MIN_DELTA, rng
        )
    if lowered.endswith(SCORE_SUFFIX) or lowered in SCORE_EXTRA_FIELDS:
        return pick_from_range(old_value, SCORE_MIN, SCORE_MAX, SCORE_MIN_DELTA, rng)
    if any(marker in lowered for marker in SIZE_MARKERS):
        return shift_by_ratio(old_value, SIZE_MIN_RATIO, SIZE_MAX_RATIO, rng)
    return shift_by_ratio(old_value, GENERIC_RATIO, GENERIC_RATIO, rng)


def substitute_payload(
    payload: Dict[str, Any], rng: random.Random
) -> Tuple[Dict[str, Any], Dict[str, List[Any]]]:
    taken = set(
        format_number(value) for value in payload.values() if is_number(value)
    )
    new_payload: Dict[str, Any] = {}
    substitutions: Dict[str, List[Any]] = {}
    for field, old_value in payload.items():
        if not is_number(old_value):
            new_payload[field] = old_value
            continue
        new_value = substitute_value(field, old_value, rng)
        for _ in range(SUBSTITUTION_ATTEMPTS):
            if format_number(new_value) not in taken:
                break
            new_value = substitute_value(field, old_value, rng)
        taken.add(format_number(new_value))
        new_payload[field] = new_value
        substitutions[field] = [old_value, new_value]
    return new_payload, substitutions


def rebuild_user(user: str, span: Tuple[int, int], new_payload: Dict[str, Any]) -> str:
    block = "%s\n%s\n%s" % (
        CHILD_CONTEXT_OPEN,
        json.dumps(new_payload, ensure_ascii=False),
        CHILD_CONTEXT_CLOSE,
    )
    return user[: span[0]] + block + user[span[1] :]


def contains_number(text: str, number: str) -> bool:
    pattern = r"(?<![\d.,])" + re.escape(number) + r"(?![\d.,]?\d)"
    return re.search(pattern, text) is not None


def split_countable(
    substitutions: Dict[str, List[Any]], parent_text: str
) -> Tuple[List[str], List[str], List[str]]:
    old_strings = set()
    new_strings = set()
    for old_value, new_value in substitutions.values():
        old_strings.add(format_number(old_value))
        new_strings.add(format_number(new_value))
    collisions = old_strings & new_strings

    def is_countable(value: Any) -> bool:
        text = format_number(value)
        if text in collisions:
            return False
        if abs(float(value)) < MIN_UNAMBIGUOUS_VALUE:
            return False
        return not contains_number(parent_text, text)

    countable_old: List[str] = []
    countable_new: List[str] = []
    ambiguous: List[str] = []
    for field, pair in substitutions.items():
        old_ok = is_countable(pair[0])
        new_ok = is_countable(pair[1])
        if old_ok:
            countable_old.append(format_number(pair[0]))
        if new_ok:
            countable_new.append(format_number(pair[1]))
        if not old_ok or not new_ok:
            ambiguous.append(field)
    return sorted(set(countable_old)), sorted(set(countable_new)), sorted(ambiguous)


def strip_thinking(response: str) -> str:
    return _THINK_RE.sub(" ", response)


def analyze_response(
    response: str, countable_old: List[str], countable_new: List[str]
) -> Tuple[int, int, str]:
    answer = strip_thinking(response)
    new_hits = sum(1 for number in countable_new if contains_number(answer, number))
    old_hits = sum(1 for number in countable_old if contains_number(answer, number))
    if new_hits > 0 and old_hits == 0:
        verdict = VERDICT_READS
    elif old_hits > 0 and new_hits == 0:
        verdict = VERDICT_MEMORIZED
    elif old_hits > 0 and new_hits > 0:
        verdict = VERDICT_MIXED
    else:
        verdict = VERDICT_NONE
    return new_hits, old_hits, verdict


def prepare_case(example: Dict[str, Any], seed: int) -> Dict[str, Any]:
    rng = random.Random(seed + example["index"])
    new_payload, substitutions = substitute_payload(example["payload"], rng)
    countable_old, countable_new, ambiguous_fields = split_countable(
        substitutions, example["parent_text"]
    )
    return {
        "index": example["index"],
        "system": example["system"],
        "user": rebuild_user(example["user"], example["span"], new_payload),
        "payload": new_payload,
        "substitutions": substitutions,
        "countable_old": countable_old,
        "countable_new": countable_new,
        "ambiguous_fields": ambiguous_fields,
    }


def build_messages(case: Dict[str, Any]) -> List[Dict[str, str]]:
    messages = []
    if case["system"]:
        messages.append({"role": "system", "content": case["system"]})
    messages.append({"role": "user", "content": case["user"]})
    return messages


def check_adapter_dir(adapter_path: Optional[str]) -> Optional[str]:
    if adapter_path is None:
        return None
    if not os.path.isdir(adapter_path):
        return "каталог адаптера не найден: %s" % adapter_path
    config_file = os.path.join(adapter_path, ADAPTER_CONFIG_FILE)
    if not os.path.isfile(config_file):
        return "в каталоге адаптера нет файла %s: %s" % (ADAPTER_CONFIG_FILE, adapter_path)
    weights_file = os.path.join(adapter_path, ADAPTER_WEIGHTS_FILE)
    if not os.path.isfile(weights_file):
        return "в каталоге адаптера нет файла %s: %s" % (ADAPTER_WEIGHTS_FILE, adapter_path)
    return None


def load_model_and_tokenizer(model_name: str, adapter_path: Optional[str]) -> Tuple[Any, Any, Any]:
    try:
        from mlx_lm import load, stream_generate
        from mlx_lm.sample_utils import make_sampler
    except ImportError as import_error:
        raise ModelLoadError(
            "не импортируется mlx_lm, запускайте скрипт python-ом из venv с mlx-lm: %s"
            % import_error
        )
    try:
        model, tokenizer = load(model_name, adapter_path=adapter_path)
    except Exception as load_error:
        raise ModelLoadError(
            "не удалось загрузить модель %s%s: %s"
            % (
                model_name,
                "" if adapter_path is None else " с адаптером %s" % adapter_path,
                load_error,
            )
        )
    return model, tokenizer, (stream_generate, make_sampler)


def build_prompt(tokenizer: Any, case: Dict[str, Any], thinking_mode: str) -> Any:
    messages = build_messages(case)
    if thinking_mode == THINKING_AUTO:
        return tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    try:
        return tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            enable_thinking=THINKING_FLAGS[thinking_mode],
        )
    except Exception:
        return tokenizer.apply_chat_template(messages, add_generation_prompt=True)


def generate_one(
    stream_generate: Any,
    model: Any,
    tokenizer: Any,
    prompt: Any,
    max_tokens: int,
    sampler: Any,
) -> str:
    text_parts: List[str] = []
    for response in stream_generate(
        model,
        tokenizer,
        prompt,
        max_tokens=max_tokens,
        sampler=sampler,
    ):
        text_parts.append(response.text)
    return "".join(text_parts)


def print_substitutions(case: Dict[str, Any]) -> None:
    sys.stdout.write("\nПример %d\n" % case["index"])
    sys.stdout.write("%-18s %-12s %-12s %s\n" % ("поле", "было", "стало", "идёт в счёт"))
    countable_old = set(case["countable_old"])
    countable_new = set(case["countable_new"])
    for field, pair in case["substitutions"].items():
        old_text = format_number(pair[0])
        new_text = format_number(pair[1])
        marks = []
        if old_text in countable_old:
            marks.append("старое")
        if new_text in countable_new:
            marks.append("новое")
        status = " и ".join(marks) if marks else "ничего, неоднозначно"
        sys.stdout.write("%-18s %-12s %-12s %s\n" % (field, old_text, new_text, status))
    sys.stdout.write("новый блок: %s\n" % json.dumps(case["payload"], ensure_ascii=False))


def print_dry_run(
    model_name: str,
    adapter_path: Optional[str],
    adapter_problem: Optional[str],
    thinking_mode: str,
    source_path: str,
    out_path: str,
    seed: int,
    requested: int,
    cases: List[Dict[str, Any]],
    source_problem: Optional[str],
) -> None:
    sys.stdout.write("DRY-RUN: модель не загружается, генерации нет.\n")
    sys.stdout.write("Модель:           %s\n" % model_name)
    sys.stdout.write(
        "Адаптер:          %s\n" % (adapter_path if adapter_path else "нет, чистая база")
    )
    if adapter_problem is not None:
        sys.stdout.write("ВНИМАНИЕ:         %s\n" % adapter_problem)
    sys.stdout.write("Размышления:      %s\n" % describe_thinking(thinking_mode))
    sys.stdout.write("Сэмплер:          make_sampler(temp=%s), это greedy argmax\n" % TEMPERATURE)
    sys.stdout.write("Seed:             %d\n" % seed)
    sys.stdout.write("Файл источника:   %s\n" % source_path)
    sys.stdout.write("Файл вывода:      %s\n" % out_path)
    if source_problem is not None:
        sys.stdout.write("\nПримеры прочитать не удалось: %s\n" % source_problem)
        return
    sys.stdout.write("Запрошено примеров: %d, отобрано: %d\n" % (requested, len(cases)))
    sys.stdout.write("\nПодстановки для первых %d примеров:\n" % min(DRY_RUN_PREVIEW, len(cases)))
    for case in cases[:DRY_RUN_PREVIEW]:
        print_substitutions(case)
    sys.stdout.write("\nВсего примеров к прогону: %d.\n" % len(cases))


def print_summary(records: List[Dict[str, Any]], failed: int) -> None:
    counts = {verdict: 0 for verdict in VERDICT_ORDER}
    for record in records:
        counts[record["verdict"]] += 1
    total = len(records)
    sys.stdout.write("\nИтог по вердиктам (успешных примеров: %d):\n" % total)
    for verdict in VERDICT_ORDER:
        sys.stdout.write("  %-12s %d\n" % (verdict, counts[verdict]))
    if failed:
        sys.stdout.write("  %-12s %d\n" % ("ошибки", failed))
    if total == 0:
        sys.stdout.write("\nВердикт: нет данных, ни один пример не прошёл.\n")
        return
    suspicious = counts[VERDICT_MEMORIZED] + counts[VERDICT_MIXED]
    ratio = suspicious / total
    sys.stdout.write(
        "\nДоля memorized + mixed: %.0f%% (%d из %d)\n" % (ratio * 100, suspicious, total)
    )
    if ratio > MEMORIZATION_ALERT_RATIO:
        sys.stdout.write(
            "ВНИМАНИЕ: МОДЕЛЬ ОПИРАЕТСЯ НА ЗАПОМНЕННЫЕ ДАННЫЕ ИЗ ОБУЧАЮЩЕЙ ВЫБОРКИ, "
            "А НЕ ЧИТАЕТ ЦИФРЫ ИЗ ВХОДА.\n"
        )
    elif counts[VERDICT_READS] == 0:
        sys.stdout.write(
            "Вердикт: не на чем делать вывод, модель вообще не называет цифры "
            "из child_context.\n"
        )
    else:
        sys.stdout.write("Вердикт: модель в основном читает цифры из входа.\n")


def run_live(
    model_name: str,
    adapter_path: Optional[str],
    thinking_mode: str,
    cases: List[Dict[str, Any]],
    out_path: str,
    max_tokens: int,
) -> int:
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    sys.stdout.write("Модель: %s\n" % model_name)
    sys.stdout.write("Адаптер: %s\n" % (adapter_path if adapter_path else "нет, чистая база"))
    sys.stdout.write("Размышления: %s\n" % describe_thinking(thinking_mode))
    sys.stdout.write("Примеров: %d, max_tokens: %d\n" % (len(cases), max_tokens))
    sys.stdout.write("Вывод: %s\n" % out_path)
    sys.stdout.write("Загружаю модель, это может занять время...\n\n")
    sys.stdout.flush()

    try:
        model, tokenizer, helpers = load_model_and_tokenizer(model_name, adapter_path)
    except ModelLoadError as model_error:
        sys.stderr.write("%s\n" % model_error)
        return EXIT_CONFIG_ERROR
    stream_generate, make_sampler = helpers
    sampler = make_sampler(temp=TEMPERATURE)

    records: List[Dict[str, Any]] = []
    failed = 0

    sys.stdout.write(
        "%-6s %-6s %-9s %-9s %-13s %s\n"
        % ("idx", "нов/ст", "new_hits", "old_hits", "вердикт", "статус")
    )
    sys.stdout.flush()

    with open(out_path, "w", encoding="utf-8") as handle:
        for case in cases:
            response_text = ""
            error_text: Optional[str] = None
            started = time.time()
            try:
                prompt = build_prompt(tokenizer, case, thinking_mode)
                response_text = generate_one(
                    stream_generate, model, tokenizer, prompt, max_tokens, sampler
                )
            except Exception as generate_error:
                error_text = "%s: %s" % (type(generate_error).__name__, generate_error)
            latency_ms = int((time.time() - started) * MILLISECONDS_IN_SECOND)
            new_hits, old_hits, verdict = analyze_response(
                response_text, case["countable_old"], case["countable_new"]
            )
            record = {
                "index": case["index"],
                "model": model_name,
                "adapter": adapter_path,
                "thinking": thinking_mode,
                "substitutions": case["substitutions"],
                "user": case["user"],
                "response": response_text,
                "new_hits": new_hits,
                "old_hits": old_hits,
                "verdict": verdict,
                "ambiguous_fields": case["ambiguous_fields"],
                "counted_old": case["countable_old"],
                "counted_new": case["countable_new"],
                "latency_ms": latency_ms,
                "error": error_text,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            if error_text is None:
                records.append(record)
                status_label = "ok"
            else:
                failed += 1
                status_label = "ошибка: %s" % error_text[:STATUS_ERROR_CHARS]
            sys.stdout.write(
                "%-6d %-6s %-9d %-9d %-13s %s\n"
                % (
                    case["index"],
                    "%d/%d" % (len(case["countable_new"]), len(case["countable_old"])),
                    new_hits,
                    old_hits,
                    verdict,
                    status_label,
                )
            )
            sys.stdout.flush()

    print_summary(records, failed)
    sys.stdout.write("Строки записаны в %s\n" % out_path)
    return EXIT_OK if failed == 0 else EXIT_DATA_ERROR


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    adapter_path = resolve_adapter_path(args.adapter_path)
    source_path = resolve_source_path(args.source_path)
    out_path = resolve_out_path(args.out_path)

    if args.n <= 0:
        sys.stderr.write("Значение --n должно быть больше нуля.\n")
        return EXIT_CONFIG_ERROR
    if args.max_tokens <= 0:
        sys.stderr.write("Значение --max-tokens должно быть больше нуля.\n")
        return EXIT_CONFIG_ERROR

    adapter_problem = check_adapter_dir(adapter_path)

    cases: List[Dict[str, Any]] = []
    source_problem: Optional[str] = None
    if not os.path.isfile(source_path):
        source_problem = "файл %s не найден (его собирает build_dataset.py)" % source_path
    else:
        try:
            examples = load_source_examples(source_path)
            selected = select_examples(examples, args.n, args.seed)
            cases = [prepare_case(example, args.seed) for example in selected]
        except SourceDatasetError as dataset_error:
            source_problem = str(dataset_error)
        except OSError as os_error:
            source_problem = "не читается %s: %s" % (source_path, os_error)

    if args.dry_run:
        print_dry_run(
            args.model,
            adapter_path,
            adapter_problem,
            args.thinking,
            source_path,
            out_path,
            args.seed,
            args.n,
            cases,
            source_problem,
        )
        return EXIT_OK

    if adapter_problem is not None:
        sys.stderr.write(
            "Не могу взять LoRA-адаптер: %s\n"
            "Укажите каталог, который сделал mlx_lm.lora (в нём лежат %s и %s), "
            "или запустите без --adapter-path.\n"
            % (adapter_problem, ADAPTER_CONFIG_FILE, ADAPTER_WEIGHTS_FILE)
        )
        return EXIT_CONFIG_ERROR

    if source_problem is not None:
        sys.stderr.write("Не могу прочитать примеры: %s\n" % source_problem)
        return EXIT_DATA_ERROR

    if len(cases) < args.n:
        sys.stdout.write(
            "Подходящих примеров с child_context нашлось только %d из запрошенных %d.\n"
            % (len(cases), args.n)
        )

    return run_live(
        args.model, adapter_path, args.thinking, cases, out_path, args.max_tokens
    )


if __name__ == "__main__":
    sys.exit(main())
