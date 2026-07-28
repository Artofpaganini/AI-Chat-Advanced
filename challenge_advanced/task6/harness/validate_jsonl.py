"""Валидатор итогового датасета в формате OpenAI ({"messages": [...]}).

Проверяет структуру строки, роли, непустоту, дрейф системного промпта, дубли,
лишние ключи и утечку секретов. Код возврата 1, если есть хотя бы одна ошибка E_.
Запуск: python3 harness/validate_jsonl.py <файл.jsonl>
"""

import hashlib
import json
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec

EXPECTED_ROLES = ("system", "user", "assistant")


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _add(issues: List[Dict[str, Any]], line: int, code: str, message: str) -> None:
    issues.append({"line": line, "code": code, "message": message})


def validate_file(path: str) -> Dict[str, Any]:
    issues = []
    seen = {}
    total = 0
    valid = 0

    with open(path, encoding="utf-8") as handle:
        for number, raw_line in enumerate(handle, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            total += 1

            for marker in spec.SECRET_MARKERS:
                if marker in raw_line:
                    _add(issues, number, "E_SECRET", "найден маркер %r" % marker)

            try:
                payload = json.loads(stripped)
            except ValueError as error:
                _add(issues, number, "E_JSON", str(error))
                continue

            if not isinstance(payload, dict):
                _add(issues, number, "E_NO_MESSAGES", "строка не объект")
                continue

            extra = sorted([key for key in payload.keys() if key != "messages"])
            if extra:
                _add(issues, number, "E_EXTRA_KEYS", "лишние ключи: %s" % ", ".join(extra))

            messages = payload.get("messages")
            if not isinstance(messages, list):
                _add(issues, number, "E_NO_MESSAGES", "нет ключа messages или это не список")
                continue

            if len(messages) != 3:
                _add(issues, number, "E_LEN", "сообщений %d, ожидалось 3" % len(messages))
                continue

            roles = []
            for message in messages:
                roles.append(message.get("role") if isinstance(message, dict) else None)
            if tuple(roles) != EXPECTED_ROLES:
                _add(issues, number, "E_ROLES", "роли %s" % str(roles))
                continue

            contents = []
            empty = False
            for message in messages:
                content = message.get("content")
                if not isinstance(content, str) or not content.strip():
                    empty = True
                contents.append(content if isinstance(content, str) else "")
            if empty:
                _add(issues, number, "E_EMPTY", "пустой или нестроковый content")
                continue

            system_text, user_text, assistant_text = contents

            if system_text != spec.SYSTEM_PROMPT:
                _add(issues, number, "E_SYSTEM_DRIFT", "system не совпадает со spec.SYSTEM_PROMPT")

            digest = _sha1(user_text + assistant_text)
            if digest in seen:
                _add(issues, number, "E_DUP", "дубль строки %d" % seen[digest])
            else:
                seen[digest] = number

            if len(user_text) < spec.MIN_USER_CHARS:
                _add(
                    issues,
                    number,
                    "W_LEN",
                    "user %d символов, минимум %d" % (len(user_text), spec.MIN_USER_CHARS),
                )
            if len(assistant_text) < spec.MIN_ASSISTANT_CHARS:
                _add(
                    issues,
                    number,
                    "W_LEN",
                    "assistant %d символов, минимум %d"
                    % (len(assistant_text), spec.MIN_ASSISTANT_CHARS),
                )
            elif len(assistant_text) > spec.MAX_ASSISTANT_CHARS:
                _add(
                    issues,
                    number,
                    "W_LEN",
                    "assistant %d символов, максимум %d"
                    % (len(assistant_text), spec.MAX_ASSISTANT_CHARS),
                )
            valid += 1

    errors = [item for item in issues if item["code"].startswith("E_")]
    warnings = [item for item in issues if item["code"].startswith("W_")]
    by_code = {}
    for item in issues:
        by_code[item["code"]] = by_code.get(item["code"], 0) + 1
    return {
        "file": os.path.abspath(path),
        "total_lines": total,
        "valid_lines": valid,
        "errors": len(errors),
        "warnings": len(warnings),
        "by_code": by_code,
        "issues": issues,
    }


def main(argv: List[str]) -> int:
    if not argv:
        print("usage: python3 harness/validate_jsonl.py <файл.jsonl>")
        return 1
    path = argv[0]
    if not os.path.exists(path):
        print("файл не найден: %s" % path)
        return 1

    report = validate_file(path)

    print("%-7s %-16s %s" % ("line", "code", "message"))
    print("-" * 78)
    if not report["issues"]:
        print("проблем нет")
    for item in report["issues"]:
        print("%-7d %-16s %s" % (item["line"], item["code"], item["message"]))
    print("-" * 78)
    print("строк: %d, валидных: %d" % (report["total_lines"], report["valid_lines"]))
    print("ошибок: %d, предупреждений: %d" % (report["errors"], report["warnings"]))
    for code in sorted(report["by_code"].keys()):
        print("  %-16s %d" % (code, report["by_code"][code]))

    if not os.path.isdir(spec.RESULTS_DIR):
        os.makedirs(spec.RESULTS_DIR)
    name = os.path.splitext(os.path.basename(path))[0]
    report_path = os.path.join(spec.RESULTS_DIR, "validation_%s.json" % name)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print("отчёт: %s" % report_path)

    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
