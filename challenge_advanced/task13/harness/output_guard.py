"""Выходной гейт шлюза (GATEWAY_CONTRACT.md раздел 7).

check_output проверяет собранный ответ целиком (режим buffer). check_output_partial проверяет
то, что накопилось на текущий чанк потока (режим incremental, раздел 8) - логика детекторов та
же, разница только в том, что accumulated_text может быть обрезан на полуслове. Обе функции не
знают про сеть и про то, откуда взялся текст - это забота gateway_server.py.

Ревизия 2026-08-05, вторая (класс 7): раньше suspicious_url ловил любой домен не из белого
списка - приложение для родителей по здоровью ребёнка легитимно даёт ссылки на медицинские
организации, и такая ссылка блокировалась наравне с настоящей атакой. Белый список остался
быстрым проходом, но подозрительным теперь делает не домен сам по себе, а признак вывода данных:
сырой IP, сокращатель ссылок, исполняемый файл/скрипт, адрес-в-адресе, длинное значение
query-параметра.

Ревизия 2026-08-05, третья (дефект 1, по итогам замера holdout): пять признаков выше смотрят на
форму ссылки и пропускают фишинг на свежем домене с коротким query. Добавлен шестой, независимый
признак - связка: внешняя ссылка плюс рядом в тексте побуждение ввести/подтвердить платёжные или
учётные данные (_has_nearby_credential_solicitation). Понижать URL_LONG_QUERY_VALUE_CHARS нельзя -
это вернёт ложные срабатывания на обычных ссылках с параметрами, поэтому фишинг ловится связкой,
а не порогом.

Ревизия 2026-08-05, вторая (класс 8): маркеры системного промпта в spec13 ловят только буквальные
куски НАШЕГО промпта. Второй, независимый признак - _detect_generic_instruction_leak - смотрит на
форму текста: обращение к модели во втором лице, перечисление правил/запретов, нумерованный свод
поведения. Работает при пересказе ЧУЖОГО системного промпта, которого в spec13 нет и быть не
может.
"""

import re
import urllib.parse
from dataclasses import dataclass
from typing import List

import secret_detectors
import spec13

URL_PATTERN = re.compile(r"https?://[^\s<>\)\]\"']+")

DANGEROUS_COMMAND_PATTERNS = (
    re.compile(r"curl\s+[^\n|]*\|\s*(sh|bash)\b", re.IGNORECASE),
    re.compile(r"wget\s+[^\n|]*\|\s*(sh|bash)\b", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\s+/", re.IGNORECASE),
    re.compile(r"\bchmod\s+777\b", re.IGNORECASE),
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"base64\s+-d\s*\|\s*bash\b", re.IGNORECASE),
)

NON_DIGIT_PATTERN = re.compile(r"\D+")

IPV4_HOST_PATTERN = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
NESTED_URL_PATTERN = re.compile(r"https?://|https?%3a%2f%2f|www\.[a-z0-9-]+\.[a-z]{2,}", re.IGNORECASE)
# Не привязан к физическому переводу строки: пересказанный (перефразированный) свод правил часто
# приходит одним абзацем, а не оригинальным форматированием с настоящими "\n" между пунктами.
NUMBERED_LIST_MARKER_PATTERN = re.compile(r"(?:^|(?<=[\s.!?:]))\d{1,2}[.)]\s+\S")


@dataclass
class OutputGuardResult:
    verdict: str
    reasons: List[str]
    replacement_text: str


def _url_is_whitelisted(url: str) -> bool:
    host = re.sub(r"^https?://", "", url, flags=re.IGNORECASE).split("/", 1)[0].lower()
    host = host.split(":", 1)[0]
    return any(host == domain or host.endswith("." + domain) for domain in spec13.URL_WHITELIST_DOMAINS)


def _detect_generated_secret(text: str) -> bool:
    findings = secret_detectors.scan_secrets(text)
    return any(finding.category == spec13.CATEGORY_API_KEY for finding in findings)


def _detect_system_prompt_leak(text: str) -> bool:
    lowered = text.lower()
    found = [marker for marker in spec13.SYSTEM_PROMPT_MARKERS if marker.lower() in lowered]
    has_long = any(len(marker) >= spec13.SYSTEM_PROMPT_LEAK_LONG_MARKER_CHARS for marker in found)
    literal_hit = len(found) >= spec13.SYSTEM_PROMPT_LEAK_MIN_MARKERS or has_long
    return literal_hit or _detect_generic_instruction_leak(text)


_INSTRUCTION_RECITATION = re.compile(
    r"(?i)(?:систем\w+\s+инструкц\w+|инструкц\w+\s+глас\w+|инструкц\w+\s+говор\w+|"
    r"мой\s+систем\w+\s+промпт|system\s+instructions?|my\s+(?:system\s+)?(?:prompt|instructions))"
    r"\s*[:—-]"
)


def _detect_generic_instruction_leak(text: str) -> bool:
    lowered = text.lower()
    # Фраза-вводка «инструкции гласят:» с двоеточием - модель начинает пересказывать свой промпт.
    # Узко: обычный безопасный ответ («не даю диагнозы») так не строится.
    if _INSTRUCTION_RECITATION.search(text):
        return True
    meta_hits = sum(1 for term in spec13.GENERIC_LEAK_META_TERMS if term in lowered)
    if meta_hits == 0:
        return False
    if meta_hits >= spec13.GENERIC_LEAK_MIN_META_HITS_ALONE:
        return True
    numbered_markers = len(NUMBERED_LIST_MARKER_PATTERN.findall(text))
    if numbered_markers >= spec13.GENERIC_LEAK_MIN_NUMBERED_LINES:
        return True
    prohibition_hits = sum(lowered.count(term) for term in spec13.GENERIC_LEAK_PROHIBITION_TERMS)
    return prohibition_hits >= spec13.GENERIC_LEAK_MIN_PROHIBITION_HITS


def _is_raw_ip_host(hostname: str) -> bool:
    if not hostname:
        return False
    if ":" in hostname:
        return True
    return bool(IPV4_HOST_PATTERN.match(hostname))


def _is_shortener_host(hostname: str) -> bool:
    return any(
        hostname == domain or hostname.endswith("." + domain) for domain in spec13.URL_SHORTENER_DOMAINS
    )


def _path_is_executable(path: str) -> bool:
    lowered = path.lower()
    return any(lowered.endswith(extension) for extension in spec13.URL_EXECUTABLE_EXTENSIONS)


def _has_nested_url(parsed: urllib.parse.SplitResult) -> bool:
    haystack = parsed.path + "?" + parsed.query
    if NESTED_URL_PATTERN.search(haystack):
        return True
    return bool(NESTED_URL_PATTERN.search(urllib.parse.unquote(haystack)))


def _has_long_query_value(query: str) -> bool:
    for _, value in urllib.parse.parse_qsl(query, keep_blank_values=True):
        if len(value) >= spec13.URL_LONG_QUERY_VALUE_CHARS:
            return True
    return False


def _url_has_exfiltration_signal(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    hostname = (parsed.hostname or "").lower()
    if _is_raw_ip_host(hostname):
        return True
    if _is_shortener_host(hostname):
        return True
    if _path_is_executable(parsed.path):
        return True
    if _has_nested_url(parsed):
        return True
    if _has_long_query_value(parsed.query):
        return True
    return False


def _has_nearby_credential_solicitation(text: str, url_start: int, url_end: int) -> bool:
    window_start = max(0, url_start - spec13.PHISHING_PROXIMITY_WINDOW_CHARS)
    window_end = min(len(text), url_end + spec13.PHISHING_PROXIMITY_WINDOW_CHARS)
    window = text[window_start:window_end].lower()
    has_action = any(term in window for term in spec13.PHISHING_ACTION_TERMS)
    has_target = any(term in window for term in spec13.PHISHING_TARGET_TERMS)
    return has_action and has_target


def _detect_suspicious_url(text: str) -> bool:
    for match in URL_PATTERN.finditer(text):
        url = match.group()
        if _url_is_whitelisted(url):
            continue
        if _url_has_exfiltration_signal(url):
            return True
        if _has_nearby_credential_solicitation(text, match.start(), match.end()):
            return True
    return False


def _detect_dangerous_command(text: str) -> bool:
    return any(pattern.search(text) for pattern in DANGEROUS_COMMAND_PATTERNS)


def _detect_pii_echo(response_text: str, input_text: str) -> bool:
    findings = secret_detectors.scan_secrets(response_text)
    input_digits = NON_DIGIT_PATTERN.sub("", input_text)
    input_lower = input_text.lower()
    for finding in findings:
        if finding.category not in (spec13.CATEGORY_CARD, spec13.CATEGORY_EMAIL, spec13.CATEGORY_PHONE):
            continue
        matched = response_text[finding.start : finding.end]
        if finding.category == spec13.CATEGORY_EMAIL:
            if matched.lower() not in input_lower:
                return True
            continue
        matched_digits = NON_DIGIT_PATTERN.sub("", matched)
        if matched_digits and matched_digits not in input_digits:
            return True
    return False


def _run_checks(text: str, input_text: str) -> OutputGuardResult:
    reasons: List[str] = []
    if _detect_generated_secret(text):
        reasons.append(spec13.OUT_DETECTOR_GENERATED_SECRET)
    if _detect_system_prompt_leak(text):
        reasons.append(spec13.OUT_DETECTOR_SYSTEM_PROMPT_LEAK)
    if _detect_suspicious_url(text):
        reasons.append(spec13.OUT_DETECTOR_SUSPICIOUS_URL)
    if _detect_dangerous_command(text):
        reasons.append(spec13.OUT_DETECTOR_DANGEROUS_COMMAND)
    if _detect_pii_echo(text, input_text):
        reasons.append(spec13.OUT_DETECTOR_PII_ECHO)

    if reasons:
        return OutputGuardResult(
            verdict=spec13.VERDICT_BLOCKED,
            reasons=reasons,
            replacement_text=spec13.OUTPUT_GUARD_FALLBACK,
        )
    return OutputGuardResult(verdict=spec13.VERDICT_PASS, reasons=[], replacement_text="")


def check_output(response_text: str, input_text: str) -> OutputGuardResult:
    return _run_checks(response_text or "", input_text or "")


def check_output_partial(accumulated_text: str, input_text: str) -> OutputGuardResult:
    return _run_checks(accumulated_text or "", input_text or "")
