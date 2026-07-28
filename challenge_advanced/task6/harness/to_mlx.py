# -*- coding: utf-8 -*-
"""Конвертер датасета ALVA в раскладку данных mlx-lm для локального LoRA-дообучения.

Берёт artifacts/train.jsonl и artifacts/eval.jsonl (формат OpenAI, только ключ messages)
и складывает каталог с файлами train.jsonl, valid.jsonl, test.jsonl - именно так mlx_lm.lora
читает локальные данные через ключ --data.

Формат строки у mlx-lm тот же самый, что у нас: один JSON-объект {"messages": [...]} на строку
(chat-формат). Содержимое примеров не переписывается, меняется только раскладка по файлам.

valid.jsonl отрезается от нашего train доля --valid-ratio с фиксированным seed: mlx-lm показывает
на нём validation loss. test.jsonl - это копия нашего eval.jsonl, он в обучении не участвует и
остаётся честной точкой замера.

Запуск: python3 harness/to_mlx.py
"""

import argparse
import json
import os
import random
import sys
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HARNESS_DIR)
ARTIFACTS_DIR = os.path.join(TASK_DIR, "artifacts")

SOURCE_TRAIN = os.path.join(ARTIFACTS_DIR, "train.jsonl")
SOURCE_EVAL = os.path.join(ARTIFACTS_DIR, "eval.jsonl")
DEFAULT_OUT_DIR = os.path.join(ARTIFACTS_DIR, "mlx_data")

OUT_TRAIN = "train.jsonl"
OUT_VALID = "valid.jsonl"
OUT_TEST = "test.jsonl"

EXPECTED_ROLES = ("system", "user", "assistant")
MESSAGES_KEY = "messages"

DEFAULT_VALID_RATIO = 0.2
DEFAULT_SEED = 1337
MAX_VALID_RATIO = 0.9

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2


class DatasetError(Exception):
    """Данные не соответствуют контракту: битый JSON, не те роли, пустой content."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Конвертация artifacts/*.jsonl в раскладку данных mlx-lm.",
    )
    parser.add_argument("--out", dest="out_dir", default=None)
    parser.add_argument(
        "--valid-ratio",
        dest="valid_ratio",
        type=float,
        default=DEFAULT_VALID_RATIO,
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def check_record(payload: Any, source: str, line_number: int) -> None:
    where = "%s строка %d" % (source, line_number)
    if not isinstance(payload, dict):
        raise DatasetError("%s: строка не JSON-объект" % where)

    messages = payload.get(MESSAGES_KEY)
    if not isinstance(messages, list):
        raise DatasetError("%s: нет ключа %r или это не список" % (where, MESSAGES_KEY))
    if len(messages) != len(EXPECTED_ROLES):
        raise DatasetError(
            "%s: сообщений %d, нужно ровно %d в порядке %s"
            % (where, len(messages), len(EXPECTED_ROLES), "/".join(EXPECTED_ROLES))
        )

    for position, expected_role in enumerate(EXPECTED_ROLES):
        message = messages[position]
        if not isinstance(message, dict):
            raise DatasetError("%s: сообщение %d не объект" % (where, position + 1))
        role = message.get("role")
        if role != expected_role:
            raise DatasetError(
                "%s: сообщение %d с ролью %r, ожидалась %r"
                % (where, position + 1, role, expected_role)
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise DatasetError(
                "%s: пустой или нестроковый content у роли %r" % (where, expected_role)
            )


def load_records(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        raise DatasetError("файл не найден: %s (его собирает build_dataset.py)" % path)

    source = os.path.basename(path)
    records = []
    try:
        handle = open(path, "r", encoding="utf-8")
    except OSError as os_error:
        raise DatasetError("не читается %s: %s" % (path, os_error))
    try:
        for line_number, raw_line in enumerate(handle, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except ValueError as parse_error:
                raise DatasetError(
                    "%s строка %d: не парсится как JSON: %s"
                    % (source, line_number, parse_error)
                )
            check_record(payload, source, line_number)
            records.append({MESSAGES_KEY: payload[MESSAGES_KEY]})
    finally:
        handle.close()

    if not records:
        raise DatasetError("файл пустой: %s" % path)
    return records


def split_train(
    records: List[Dict[str, Any]],
    valid_ratio: float,
    seed: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    shuffled = list(records)
    random.Random(seed).shuffle(shuffled)
    if valid_ratio <= 0:
        return shuffled, []
    valid_size = int(round(len(shuffled) * valid_ratio))
    valid_size = max(1, valid_size)
    valid_size = min(valid_size, len(shuffled) - 1)
    return shuffled[valid_size:], shuffled[:valid_size]


def write_jsonl(path: str, records: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def record_chars(record: Dict[str, Any]) -> int:
    return sum(len(message["content"]) for message in record[MESSAGES_KEY])


def describe(path: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = len(records)
    total_chars = sum(record_chars(record) for record in records)
    return {
        "name": os.path.basename(path),
        "rows": rows,
        "avg_chars": int(round(float(total_chars) / rows)) if rows else 0,
        "bytes": os.path.getsize(path),
    }


def verify_written(path: str, expected_rows: int) -> None:
    written = load_records(path)
    if len(written) != expected_rows:
        raise DatasetError(
            "%s: записано %d строк, ожидалось %d"
            % (os.path.basename(path), len(written), expected_rows)
        )


def print_summary(
    out_dir: str,
    valid_ratio: float,
    seed: int,
    stats: List[Dict[str, Any]],
) -> None:
    print("Источник: %s" % SOURCE_TRAIN)
    print("Источник: %s" % SOURCE_EVAL)
    print("Каталог:  %s" % out_dir)
    print("Сплит:    valid_ratio=%s, seed=%d" % (valid_ratio, seed))
    print("")
    print("%-14s %-8s %-14s %s" % ("файл", "строк", "ср. символов", "байт"))
    print("-" * 50)
    total_rows = 0
    total_bytes = 0
    for item in stats:
        total_rows += item["rows"]
        total_bytes += item["bytes"]
        print(
            "%-14s %-8d %-14d %d"
            % (item["name"], item["rows"], item["avg_chars"], item["bytes"])
        )
    print("-" * 50)
    print("%-14s %-8d %-14s %d" % ("итого", total_rows, "", total_bytes))
    print("")
    print("Проверка пройдена: в каждой строке ровно 3 сообщения system/user/assistant.")
    print("Дальше: mlx_lm.lora --train --data %s" % out_dir)


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.valid_ratio < 0 or args.valid_ratio > MAX_VALID_RATIO:
        sys.stderr.write(
            "Значение --valid-ratio должно быть в диапазоне от 0 до %s, получено %s.\n"
            % (MAX_VALID_RATIO, args.valid_ratio)
        )
        return EXIT_CONFIG_ERROR

    out_dir = os.path.abspath(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR

    try:
        source_train = load_records(SOURCE_TRAIN)
        source_eval = load_records(SOURCE_EVAL)
    except DatasetError as dataset_error:
        sys.stderr.write("Датасет не прошёл проверку: %s\n" % dataset_error)
        return EXIT_DATA_ERROR

    train_records, valid_records = split_train(source_train, args.valid_ratio, args.seed)

    if not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir)
        except OSError as os_error:
            sys.stderr.write("Не удалось создать каталог %s: %s\n" % (out_dir, os_error))
            return EXIT_CONFIG_ERROR

    targets = [
        (os.path.join(out_dir, OUT_TRAIN), train_records),
        (os.path.join(out_dir, OUT_VALID), valid_records),
        (os.path.join(out_dir, OUT_TEST), source_eval),
    ]

    stats = []
    try:
        for path, records in targets:
            write_jsonl(path, records)
            verify_written(path, len(records))
            stats.append(describe(path, records))
    except DatasetError as dataset_error:
        sys.stderr.write("Записанные данные не прошли проверку: %s\n" % dataset_error)
        return EXIT_DATA_ERROR
    except OSError as os_error:
        sys.stderr.write("Ошибка записи в %s: %s\n" % (out_dir, os_error))
        return EXIT_DATA_ERROR

    print_summary(out_dir, args.valid_ratio, args.seed, stats)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
