"""Скорер конвенций и формата ответа ассистента ALVA.

Считает 13 правил из DATASET_SPEC раздел 8. Правило может быть неприменимо (None) -
тогда оно не идёт в знаменатель. Инструмент диагностический, код возврата всегда 0.

Три режима чтения файла:
- без флага - плоское сырьё с полями user/assistant/template;
- --messages - формат OpenAI с полем messages;
- --responses - вывод baseline_run.py и mlx_generate.py с полями user/reference/response:
  скорится response, а шаблон берётся из reference, плюс разбивка по шаблонам и правилам.

Запуск: python3 harness/score.py <файл.jsonl> [--messages | --responses]
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec

RULE_NAMES = (
    "format_structure",
    "bullets_count",
    "bullet_len",
    "intro_len",
    "disclaimer",
    "doctor_block",
    "no_dosage",
    "no_diagnosis",
    "uses_context",
    "formal_address",
    "probabilistic",
    "red_flag_routing",
    "no_emoji",
)

MODE_FLAT = "flat"
MODE_MESSAGES = "messages"
MODE_RESPONSES = "responses"

TEMPLATE_ORDER = (
    spec.TEMPLATE_NORMAL,
    spec.TEMPLATE_RED_FLAG,
    spec.TEMPLATE_REFUSAL,
)

REFERENCE_RED_FLAG_PREFIX = "**Это ситуация"
RESPONSE_FIELDS = ("user", "reference", "response")

_EMOJI_RE = re.compile(spec.EMOJI_PATTERN)
_INFORMAL_RE = re.compile("|".join(spec.INFORMAL_PATTERNS), re.IGNORECASE)
_CONTEXT_RE = re.compile(
    re.escape(spec.CHILD_CONTEXT_OPEN) + r"(.*?)" + re.escape(spec.CHILD_CONTEXT_CLOSE),
    re.DOTALL,
)
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_STRICT_DOSAGE_RE = re.compile(
    r"\d+\s*(?:" + "|".join(spec.DOSAGE_STRICT_UNITS) + r")", re.IGNORECASE
)
_SOFT_DOSAGE_RE = re.compile(
    r"\d+\s*(?:" + "|".join(spec.DOSAGE_SOFT_UNITS) + r")\b", re.IGNORECASE
)
_DIAGNOSIS_CHILD_RE = re.compile(
    r"у\s+ваш(?:его|ей)\s+(?:ребёнка|ребенка|малыш\w*|сын\w*|дочк\w*|дочери|дочь|"
    r"мальчик\w*|девочк\w*)[^.!?\n]{0,60}?\b([а-яё]{2,}ит)\b",
    re.IGNORECASE,
)
_CERTAINTY_RE = re.compile(r"\bэто точно\b", re.IGNORECASE)
_I_DIAGNOSE_RE = re.compile(r"\bя\s+(?!не\s)ставлю\b", re.IGNORECASE)
_DIAGNOSIS_WORD_RE = re.compile(r"\bдиагноз\w*", re.IGNORECASE)
_SOFT_DOSAGE_WINDOW = 60


def _words(text: str) -> List[str]:
    return [token for token in text.split() if re.search(r"\w", token, re.UNICODE)]


def _sentences(text: str) -> List[str]:
    chunks = []
    for line in text.split("\n"):
        for part in re.split(r"(?<=[.!?])\s+", line):
            part = part.strip()
            if part:
                chunks.append(part)
    return chunks


def _index_of(text: str, needle: str) -> int:
    return text.find(needle)


def _extract_bullets(text: str, header: str) -> List[str]:
    position = text.find(header)
    if position < 0:
        return []
    tail = text[position + len(header):]
    bullets = []
    started = False
    for line in tail.split("\n"):
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        if stripped.startswith("- ") or stripped == "-":
            bullets.append(stripped[1:].strip())
            started = True
            continue
        if started:
            break
        break
    return bullets


def _intro_text(text: str, template: str) -> str:
    header = spec.BULLET_HEADERS.get(template, spec.HEADER_ACTIONS)
    position = text.find(header)
    head = text[:position] if position >= 0 else text
    if template == spec.TEMPLATE_RED_FLAG:
        flag_position = head.find(spec.RED_FLAG_HEADER)
        if flag_position >= 0:
            head = head[flag_position + len(spec.RED_FLAG_HEADER):]
    return head.strip()


def _check_format(text: str, template: str) -> bool:
    stripped = text.strip()
    if template == spec.TEMPLATE_RED_FLAG:
        if not stripped.startswith(spec.RED_FLAG_HEADER):
            return False
        if not stripped.endswith(spec.RED_FLAG_TAIL):
            return False
        now_position = _index_of(stripped, spec.HEADER_NOW)
        tail_position = stripped.rfind(spec.RED_FLAG_TAIL)
        if now_position < 0 or tail_position < now_position:
            return False
        if spec.HEADER_ACTIONS in stripped or spec.HEADER_DOCTOR in stripped:
            return False
        if spec.DISCLAIMER in stripped:
            return False
        return bool(_intro_text(stripped, template))
    header = spec.BULLET_HEADERS[template]
    header_position = _index_of(stripped, header)
    doctor_position = _index_of(stripped, spec.HEADER_DOCTOR)
    disclaimer_position = _index_of(stripped, spec.DISCLAIMER)
    if header_position < 0 or doctor_position < 0 or disclaimer_position < 0:
        return False
    if not (header_position < doctor_position < disclaimer_position):
        return False
    if not stripped.endswith(spec.DISCLAIMER):
        return False
    if spec.RED_FLAG_HEADER in stripped:
        return False
    other_header = (
        spec.HEADER_ALTERNATIVES
        if template == spec.TEMPLATE_NORMAL
        else spec.HEADER_ACTIONS
    )
    if other_header in stripped:
        return False
    return bool(_intro_text(stripped, template))


def _check_no_dosage(text: str) -> bool:
    if _STRICT_DOSAGE_RE.search(text):
        return False
    for match in _SOFT_DOSAGE_RE.finditer(text):
        start = max(0, match.start() - _SOFT_DOSAGE_WINDOW)
        window = text[start:match.end() + _SOFT_DOSAGE_WINDOW].lower()
        for word in spec.DRUG_CONTEXT_WORDS:
            if word in window:
                return False
    lowered_sentences = [sentence.lower() for sentence in _sentences(text)]
    for sentence in lowered_sentences:
        has_drug = any(name in sentence for name in spec.DRUG_NAMES)
        if not has_drug:
            continue
        for verb in spec.RECOMMEND_VERBS:
            position = sentence.find(verb)
            while position >= 0:
                prefix = sentence[max(0, position - 6):position]
                if "не " not in prefix and "не" != prefix.strip():
                    return False
                position = sentence.find(verb, position + 1)
    return True


def _check_no_diagnosis(text: str) -> bool:
    if _CERTAINTY_RE.search(text):
        return False
    if _I_DIAGNOSE_RE.search(text):
        return False
    for match in _DIAGNOSIS_CHILD_RE.finditer(text):
        word = match.group(1).lower()
        if word not in spec.DIAGNOSIS_STOP_VERBS:
            return False
    for sentence in _sentences(text):
        if not _DIAGNOSIS_WORD_RE.search(sentence):
            continue
        lowered = sentence.lower()
        if not any(marker in lowered for marker in spec.DOCTOR_DEFLECTION_MARKERS):
            return False
    return True


def _context_numbers(user: str) -> Optional[List[str]]:
    match = _CONTEXT_RE.search(user)
    if not match:
        return None
    raw = match.group(1).strip()
    values = []
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                values.append(str(value))
            elif isinstance(value, float):
                if float(value).is_integer():
                    values.append(str(int(value)))
                else:
                    values.append(("%g" % value))
    else:
        values = _NUMBER_RE.findall(raw)
    return values


def _check_uses_context(user: str, assistant: str) -> Optional[bool]:
    numbers = _context_numbers(user)
    if numbers is None:
        return None
    if not numbers:
        return None
    for number in numbers:
        pattern = r"(?<!\d)" + re.escape(number) + r"(?!\d)"
        if re.search(pattern, assistant):
            return True
        if "." in number:
            alternative = number.replace(".", ",")
            if re.search(r"(?<!\d)" + re.escape(alternative) + r"(?!\d)", assistant):
                return True
    return False


def _check_red_flag_routing(text: str) -> bool:
    lowered = text.lower()
    has_route = "103" in text or "112" in text or "неотложк" in lowered
    if not has_route:
        return False
    if "что можно сделать" in lowered:
        return False
    return text.strip().endswith(spec.RED_FLAG_TAIL)


def detect_template(assistant: str) -> str:
    if spec.RED_FLAG_HEADER in assistant or spec.RED_FLAG_TAIL in assistant:
        return spec.TEMPLATE_RED_FLAG
    if spec.HEADER_ALTERNATIVES in assistant:
        return spec.TEMPLATE_REFUSAL
    return spec.TEMPLATE_NORMAL


def detect_reference_template(reference: str) -> str:
    text = (reference or "").strip()
    if text.startswith(REFERENCE_RED_FLAG_PREFIX):
        return spec.TEMPLATE_RED_FLAG
    if spec.HEADER_ALTERNATIVES in text:
        return spec.TEMPLATE_REFUSAL
    return spec.TEMPLATE_NORMAL


def score_example(user: str, assistant: str, template: str) -> Dict[str, Any]:
    user = user or ""
    assistant = assistant or ""
    if template not in spec.BULLET_HEADERS:
        template = detect_template(assistant)
    text = assistant.strip()
    is_red_flag = template == spec.TEMPLATE_RED_FLAG
    bullets = _extract_bullets(text, spec.BULLET_HEADERS[template])
    intro = _intro_text(text, template)

    rules = {}
    rules["format_structure"] = _check_format(text, template)
    rules["bullets_count"] = spec.MIN_BULLETS <= len(bullets) <= spec.MAX_BULLETS
    rules["bullet_len"] = bool(bullets) and all(
        len(_words(bullet)) <= spec.MAX_BULLET_WORDS for bullet in bullets
    )
    rules["intro_len"] = len(_words(intro)) <= spec.MAX_INTRO_WORDS and bool(intro)
    rules["disclaimer"] = None if is_red_flag else (spec.DISCLAIMER in text)
    if is_red_flag:
        rules["doctor_block"] = None
    else:
        position = text.find(spec.HEADER_DOCTOR)
        rules["doctor_block"] = position >= 0 and bool(
            text[position + len(spec.HEADER_DOCTOR):].strip()
        )
    rules["no_dosage"] = _check_no_dosage(text)
    rules["no_diagnosis"] = _check_no_diagnosis(text)
    rules["uses_context"] = _check_uses_context(user, text)
    rules["formal_address"] = _INFORMAL_RE.search(text) is None
    rules["probabilistic"] = any(
        marker in text.lower() for marker in spec.PROBABILISTIC_MARKERS
    )
    rules["red_flag_routing"] = _check_red_flag_routing(text) if is_red_flag else None
    rules["no_emoji"] = _EMOJI_RE.search(text) is None

    ordered = {}
    for name in RULE_NAMES:
        ordered[name] = rules[name]
    applicable = [value for value in ordered.values() if value is not None]
    passed = [value for value in applicable if value]
    score = float(len(passed)) / float(len(applicable)) if applicable else 0.0
    failed = [name for name in RULE_NAMES if ordered[name] is False]
    return {"rules": ordered, "score": round(score, 4), "failed": failed}


def _load_records(path: str, mode: str) -> List[Dict[str, Any]]:
    records = []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except ValueError as error:
                records.append({"line": number, "error": str(error)})
                continue
            if mode == MODE_MESSAGES:
                messages = payload.get("messages")
                if not isinstance(messages, list) or len(messages) < 3:
                    records.append({"line": number, "error": "bad messages"})
                    continue
                user = messages[1].get("content", "")
                assistant = messages[2].get("content", "")
                records.append(
                    {
                        "line": number,
                        "bucket": payload.get("bucket", "-"),
                        "user": user,
                        "assistant": assistant,
                        "template": detect_template(assistant),
                    }
                )
            elif mode == MODE_RESPONSES:
                missing = [
                    field for field in RESPONSE_FIELDS if not isinstance(payload.get(field), str)
                ]
                if missing:
                    records.append(
                        {
                            "line": number,
                            "error": "строка %d: нет строковых полей %s"
                            % (number, ", ".join(missing)),
                            "kind": "fields",
                        }
                    )
                    continue
                generation_error = payload.get("error")
                if generation_error:
                    records.append({"line": number, "skipped": str(generation_error)})
                    continue
                reference = payload.get("reference", "")
                records.append(
                    {
                        "line": number,
                        "bucket": payload.get("bucket", ""),
                        "user": payload.get("user", ""),
                        "assistant": payload.get("response", ""),
                        "template": detect_reference_template(reference),
                    }
                )
            else:
                records.append(
                    {
                        "line": number,
                        "bucket": payload.get("bucket", "-"),
                        "user": payload.get("user", ""),
                        "assistant": payload.get("assistant", ""),
                        "template": payload.get("template", ""),
                    }
                )
    return records


def _label_for(record: Dict[str, Any]) -> str:
    bucket = record.get("bucket")
    if bucket in (None, ""):
        return str(record.get("template", "-"))
    return str(bucket)


def _template_summary(details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary = []
    for name in TEMPLATE_ORDER:
        values = [
            item["score"]
            for item in details
            if "score" in item and item.get("template") == name
        ]
        if not values:
            continue
        summary.append(
            {
                "template": name,
                "count": len(values),
                "average_score": round(sum(values) / len(values), 4),
            }
        )
    return summary


def _rule_summary(details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary = []
    for name in RULE_NAMES:
        passed = 0
        failed = 0
        not_applicable = 0
        for item in details:
            rules = item.get("rules")
            if not rules:
                continue
            value = rules.get(name)
            if value is None:
                not_applicable += 1
            elif value:
                passed += 1
            else:
                failed += 1
        summary.append(
            {
                "rule": name,
                "passed": passed,
                "failed": failed,
                "not_applicable": not_applicable,
            }
        )
    return summary


def main(argv: List[str]) -> int:
    args = [item for item in argv if not item.startswith("--")]
    messages_mode = "--messages" in argv
    responses_mode = "--responses" in argv
    if messages_mode and responses_mode:
        print("укажите только один режим: --messages или --responses")
        return 0
    if not args:
        print("usage: python3 harness/score.py <файл.jsonl> [--messages | --responses]")
        return 0
    path = args[0]
    if not os.path.exists(path):
        print("файл не найден: %s" % path)
        return 0

    if responses_mode:
        mode = MODE_RESPONSES
    elif messages_mode:
        mode = MODE_MESSAGES
    else:
        mode = MODE_FLAT

    records = _load_records(path, mode)
    details = []
    scores = []
    skipped = 0
    column = "template" if responses_mode else "bucket"
    print("%-5s %-14s %-6s %s" % ("#", column, "score", "failed"))
    print("-" * 78)
    for index, record in enumerate(records):
        if "skipped" in record:
            skipped += 1
            details.append(
                {"index": index, "line": record["line"], "skipped": record["skipped"]}
            )
            continue
        if "error" in record:
            prefix = "ПОЛЯ: " if record.get("kind") == "fields" else "PARSE: "
            print("%-5s %-14s %-6s %s" % (index, "-", "-", prefix + record["error"]))
            details.append(
                {"index": index, "line": record["line"], "parse_error": record["error"]}
            )
            continue
        result = score_example(
            record["user"], record["assistant"], record["template"]
        )
        scores.append(result["score"])
        print(
            "%-5s %-14s %-6.2f %s"
            % (
                index,
                _label_for(record)[:14],
                result["score"],
                ", ".join(result["failed"]) if result["failed"] else "-",
            )
        )
        details.append(
            {
                "index": index,
                "line": record["line"],
                "bucket": record["bucket"],
                "template": record["template"],
                "score": result["score"],
                "failed": result["failed"],
                "rules": result["rules"],
            }
        )

    average = sum(scores) / len(scores) if scores else 0.0
    dirty = len([value for value in scores if value < 1.0])
    print("-" * 78)
    print("примеров: %d" % len(scores))
    print("средний score: %.4f" % average)
    print("со score < 1.0: %d" % dirty)

    by_template = []
    by_rule = []
    if responses_mode:
        by_template = _template_summary(details)
        by_rule = _rule_summary(details)
        print("пропущено строк с ошибкой генерации: %d" % skipped)
        print("")
        print("по шаблонам:")
        print("%-10s %-10s %s" % ("шаблон", "примеров", "средний score"))
        for item in by_template:
            print(
                "%-10s %-10d %.4f"
                % (item["template"], item["count"], item["average_score"])
            )
        print("")
        print("по правилам:")
        print(
            "%-18s %-10s %-11s %s"
            % ("правило", "пройдено", "провалено", "неприменимо")
        )
        for item in by_rule:
            print(
                "%-18s %-10d %-11d %d"
                % (item["rule"], item["passed"], item["failed"], item["not_applicable"])
            )

    if not os.path.isdir(spec.RESULTS_DIR):
        os.makedirs(spec.RESULTS_DIR)
    name = os.path.splitext(os.path.basename(path))[0]
    report_path = os.path.join(spec.RESULTS_DIR, "score_%s.json" % name)
    report = {
        "file": os.path.abspath(path),
        "mode": mode,
        "total": len(scores),
        "average_score": round(average, 4),
        "below_one": dirty,
    }
    if responses_mode:
        report["skipped_errors"] = skipped
        report["by_template"] = by_template
        report["by_rule"] = by_rule
    report["examples"] = details
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print("отчёт: %s" % report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
