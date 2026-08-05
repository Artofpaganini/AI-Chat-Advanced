"""Печатает набор кейсов человеку глазами - декодирует .jsonl.b64 (или читает обычный .jsonl)
и выводит каждый кейс как отформатированный JSON.

Запуск: python3 harness/show_cases.py data/holdout_cases.jsonl.b64
"""

import json
import os
import sys

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import case_codec


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: show_cases.py <path.jsonl[.b64]>\n")
        return 2
    path = sys.argv[1]
    if not os.path.isfile(path):
        sys.stderr.write("файл не найден: %s\n" % path)
        return 2
    for index, line in enumerate(case_codec.read_case_lines(path), start=1):
        case = json.loads(line)
        sys.stdout.write("--- %d: %s ---\n" % (index, case.get("id", "?")))
        sys.stdout.write(json.dumps(case, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
