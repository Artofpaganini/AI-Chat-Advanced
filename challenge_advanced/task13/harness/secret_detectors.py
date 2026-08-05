"""Детекторы входа из GATEWAY_CONTRACT.md раздел 6, плюс усиление ревизий 2026-08-05 вторая/третья.

scan_secrets возвращает непересекающиеся Finding, отсортированные по позиции. Приоритет при
пересечении отдаётся более специфичному/опасному детектору - блокирующие идут раньше маскирующих,
конкретные форматы ключей раньше общих (generic_bearer, base64_secret). Finding не хранит сам
найденный текст - только длину (matched_len), чтобы объект нельзя было случайно залогировать
с секретом внутри.

Усиление добавляет четыре независимых механизма поверх прямых regex-паттернов:
  - _scan_reversed - строка, записанная задом наперёд, ищется через разворот всего текста и
    прогон тех же прямых паттернов, с обратным пересчётом координат.
  - _scan_stitched - "разрядка" (посимвольная или произвольным текстом) снимается сшивкой соседних
    коротких прогонов key-символов (буквы/цифры/дефис/подчёркивание) через любой не-key разделитель
    (пробел, точка, кириллица-филлер), после чего сшитая строка проверяется теми же паттернами.
    Card-детектор в этот механизм не входит нарочно - см. риск ложных срабатываний в докстринге
    _stitch_candidates.
  - _scan_hex / _scan_url_encoded - симметричны существующему _scan_base64: декодируем кандидата,
    рекурсивно (с ограничением глубины) прогоняем через тот же набор прямых паттернов.
  - _normalize_confusables - используется внутри _scan_email_phone И внутри _scan_direct_patterns
    (ревизия третья, дефект 3): подмена визуально похожих символов кириллицы на латиницу перед
    сверкой с паттернами почты/телефона И прямыми паттернами ключей. Нормализация посимвольная,
    длина строки не меняется, координаты совпадений не сдвигаются. В карте нет ни одной подмены
    буква-на-цифру - card/luhn её не получает нарочно.

Ревизия третья (по итогам первого прогона на holdout) добавляет: диапазоны длин вместо точных чисел
у форматов сервисов и AWS (жёсткая длина ловила только образец, не реальный/выдуманный ключ);
JWT_TOKEN_PATTERN (три части через точку, точка не входит в base64 - обычный base64-кандидат такой
токен целиком не захватывает); расширенный URL_ENCODED_CANDIDATE_PATTERN без нижнего порога числа
"%XX" (двойное кодирование одного символа даёт в видимом тексте только одну такую последовательность -
безопасность держит рекурсивная проверка decoded-текста, а не счётчик escape-ов).
"""

import base64
import binascii
import re
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional, Tuple

import spec13


@dataclass
class Finding:
    code: str
    category: str
    action: str
    start: int
    end: int
    matched_len: int


# --- Прямые паттерны, контракт раздел 6 -----------------------------------------------------

ANTHROPIC_KEY_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")
OPENAI_KEY_PATTERN = re.compile(r"sk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{20,}")
GITHUB_TOKEN_PATTERN = re.compile(
    r"gh(?:p|o|u|s|r)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
)
# Ревизия 2026-08-05, третья (дефект 2): AWS сам фиксирует длину (AKIA/ASIA+16, secret - 40
# base64-знаков), но выдуманный злоумышленником ключ такого обязательства не даёт, а реальный
# формат сервиса может измениться. Точная длина заменена диапазоном - минимум на знак короче
# эталона, максимум с запасом.
AWS_ACCESS_KEY_PATTERN = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{15,25}\b")
AWS_SECRET_CANDIDATE_PATTERN = re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+]{39,44}(?![A-Za-z0-9/+=])")
AWS_SECRET_PROXIMITY_CHARS = 40
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----)?"
)
BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-_.=]{20,}")
SPLIT_SECRET_PATTERN = re.compile(
    r"(sk-(?:proj-)?|sk-ant-|gh(?:p|o|u|s|r)_|github_pat_)"
    r"[\"'\s]*[+\n][\"'\s]*"
    r"([A-Za-z0-9_-]{8,})"
)

# --- Ревизия 2026-08-05, вторая: форматы популярных сервисов (класс 1) ----------------------
# Разделители внутри токена различаются намеренно - underscore, dash, dot, colon - см. докстринг
# spec13.py у соответствующих кодов.
#
# Ревизия 2026-08-05, третья (дефект 2): хвосты были заданы точной длиной образца конкретного
# сервиса (например ровно 35 знаков у Google). Реальные ключи одного сервиса не всегда совпадают
# по длине с образцом, а выдуманный - тем более. Все точные {N} заменены диапазонами {N-,N+} -
# минимум заведомо ниже эталона (ключ на знак короче обязан ловиться), максимум с запасом.

STRIPE_KEY_PATTERN = re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b|\bwhsec_[A-Za-z0-9]{20,}\b")
SQUARE_TOKEN_PATTERN = re.compile(r"\bsq0(?:atp|csp)-[A-Za-z0-9_-]{20,}\b")
SLACK_TOKEN_PATTERN = re.compile(r"\bxox[baprs]-[A-Za-z0-9]{8,}(?:-[A-Za-z0-9]{8,}){1,3}\b")
TELEGRAM_BOT_TOKEN_PATTERN = re.compile(r"\b\d{6,10}:[A-Za-z0-9_-]{25,45}\b")
DISCORD_BOT_TOKEN_PATTERN = re.compile(r"\b[A-Za-z0-9_-]{20,30}\.[A-Za-z0-9_-]{5,8}\.[A-Za-z0-9_-]{20,45}\b")
SENDGRID_KEY_PATTERN = re.compile(r"\bSG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b")
MAILGUN_KEY_PATTERN = re.compile(r"\bkey-[a-f0-9]{28,45}\b")
TWILIO_KEY_PATTERN = re.compile(r"\bAC[a-f0-9]{28,40}\b|\bSK[a-f0-9]{28,40}\b")
GOOGLE_API_KEY_PATTERN = re.compile(r"\bAIza[0-9A-Za-z_-]{20,45}\b")
AZURE_CONNECTION_STRING_PATTERN = re.compile(r"AccountKey=[A-Za-z0-9+/]{20,}={0,2}", re.IGNORECASE)
GITLAB_TOKEN_PATTERN = re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")
NPM_TOKEN_PATTERN = re.compile(r"\bnpm_[A-Za-z0-9]{28,45}\b")
MAPBOX_TOKEN_PATTERN = re.compile(r"\b(?:pk|sk)\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
DB_CONNECTION_STRING_PATTERN = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:/@]+:[^\s@]+@[^\s/]+"
)

# Ревизия 2026-08-05, третья (класс 4): JWT - три части через точку, каждая base64url. Точка не
# входит в алфавит base64, поэтому обычный BASE64_CANDIDATE_PATTERN никогда не захватывает токен
# целиком - нужен отдельный прямой паттерн. Заголовок JWT почти всегда начинается с "eyJ"
# (base64 от '{"'), это и есть якорь, снижающий риск случайного совпадения.
JWT_TOKEN_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")

BASE64_CANDIDATE_PATTERN = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/=])")
HEX_CANDIDATE_PATTERN = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{24,}(?![0-9A-Fa-f])")
# Ревизия 2026-08-05, третья (класс 5): раньше кандидат требовал 2+ последовательностей "%XX" -
# двойное кодирование "%25XX" (закодированный сам знак процента) внутри почти-целиком-читаемого
# токена, где закодирован только один разделительный символ, даёт ровно ОДНУ такую
# последовательность в видимом тексте и не проходил порог. Порог снят - безопасность не в счётчике
# "%XX", а в рекурсивной проверке _decoded_text_has_secret ниже: сам факт декодирования не создаёт
# Finding, пока раскодированное содержимое не совпадёт с реальным паттерном секрета.
URL_ENCODED_CANDIDATE_PATTERN = re.compile(
    r"(?:[A-Za-z0-9_.~-]|%[0-9A-Fa-f]{2})*%[0-9A-Fa-f]{2}(?:[A-Za-z0-9_.~-]|%[0-9A-Fa-f]{2})*"
)

# Карта содержит и запятую как разделитель между цифрами - позволяет "точками/запятыми разбитый"
# номер карты (класс 3, второй пункт) не терять маску Луна.
CARD_CANDIDATE_PATTERN = re.compile(r"(?<!\d)\d(?:[\d\-. ]{11,25})\d(?!\d)")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
    r"|(?<!\d)\+\d{1,3}[\s\-]\(?\d{2,4}\)?[\s\-]?\d{3}[\s\-]?\d{2,4}[\s\-]?\d{0,4}(?!\d)"
    r"|(?<!\d)\+?1?[\s\-]?\(\d{3}\)[\s\-]?\d{3}[\s\-]?\d{4}(?!\d)"
)

NON_DIGIT_PATTERN = re.compile(r"\D+")

# --- Ревизия 2026-08-05, вторая: нормализация похожих символов (класс 4) --------------------
# Только устойчивые визуальные двойники кириллица<->латиница (используются в фишинге доменов).
# Подмена посимвольная - длина строки не меняется, координаты совпадений остаются верными.

CONFUSABLE_MAP = {
    "а": "a", "А": "A",
    "е": "e", "Е": "E", "ё": "e", "Ё": "E",
    "о": "o", "О": "O",
    "р": "p", "Р": "P",
    "с": "c", "С": "C",
    "у": "y", "У": "Y",
    "х": "x", "Х": "X",
    "і": "i", "І": "I",
    "ј": "j", "Ј": "J",
    "ѕ": "s", "Ѕ": "S",
    "В": "B",
    "Н": "H",
    "Т": "T",
    "М": "M",
    "К": "K",
}

# --- Ревизия 2026-08-05, вторая: сшивка кандидата под обфускацию (класс 3) ------------------
# Любой символ, не входящий в KEY_RUN_PATTERN (буквы/цифры/дефис/подчёркивание), считается
# разделителем - пробел, точка, запятая, перевод строки, кириллический филлер-текст. Сшивка
# намеренно не применяется к card/luhn: с большим окном разрешённого разрыва она начала бы
# склеивать разрозненные числа медицинского текста (дата + вес + рост) в цепочку, которая иногда
# случайно проходит проверку Луна. Для ключей риск ниже на порядки - совпадение требует, чтобы
# сшитая строка началась с буквального префикса конкретного сервиса (sk-, AKIA, ghp_, xoxb- и
# так далее), а такие префиксы не возникают в обычном родительском/медицинском тексте случайно.

KEY_RUN_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
STITCH_MAX_GAP_CHARS = 100
STITCH_MAX_WINDOW_CHARS = 220
STITCH_MAX_RUNS = 60
STITCH_SAFETY_RUN_LIMIT = 400

MAX_DECODE_DEPTH = 3
HEX_MIN_DECODE_LEN = 24


def luhn_valid(digits: str) -> bool:
    if not digits.isdigit() or not (13 <= len(digits) <= 19):
        return False
    total = 0
    reversed_digits = digits[::-1]
    for index, char in enumerate(reversed_digits):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _overlaps(start: int, end: int, claimed: List[Tuple[int, int]]) -> bool:
    for claim_start, claim_end in claimed:
        if start < claim_end and end > claim_start:
            return True
    return False


def _add(findings: List[Finding], claimed: List[Tuple[int, int]], code: str, start: int, end: int) -> None:
    if _overlaps(start, end, claimed):
        return
    findings.append(
        Finding(
            code=code,
            category=spec13.DETECTOR_CATEGORY[code],
            action=spec13.DETECTOR_ACTION[code],
            start=start,
            end=end,
            matched_len=end - start,
        )
    )
    claimed.append((start, end))


def _scan_direct_patterns_single(text: str, findings: List[Finding], claimed: List[Tuple[int, int]]) -> None:
    for match in PRIVATE_KEY_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_PRIVATE_KEY_PEM, match.start(), match.end())
    for match in AWS_ACCESS_KEY_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_AWS_ACCESS_KEY, match.start(), match.end())
    for match in AWS_SECRET_CANDIDATE_PATTERN.finditer(text):
        window_start = max(0, match.start() - AWS_SECRET_PROXIMITY_CHARS)
        window_end = min(len(text), match.end() + AWS_SECRET_PROXIMITY_CHARS)
        window = text[window_start:window_end].lower()
        if "secret" in window or "секрет" in window:
            _add(findings, claimed, spec13.DETECTOR_AWS_SECRET_KEY, match.start(), match.end())
    for match in ANTHROPIC_KEY_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_API_KEY_ANTHROPIC, match.start(), match.end())
    for match in OPENAI_KEY_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_API_KEY_OPENAI, match.start(), match.end())
    for match in GITHUB_TOKEN_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_GITHUB_TOKEN, match.start(), match.end())
    for match in STRIPE_KEY_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_API_KEY_STRIPE, match.start(), match.end())
    for match in SQUARE_TOKEN_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_API_KEY_SQUARE, match.start(), match.end())
    for match in SLACK_TOKEN_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_TOKEN_SLACK, match.start(), match.end())
    for match in TELEGRAM_BOT_TOKEN_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_TOKEN_TELEGRAM, match.start(), match.end())
    for match in DISCORD_BOT_TOKEN_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_TOKEN_DISCORD, match.start(), match.end())
    for match in SENDGRID_KEY_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_API_KEY_SENDGRID, match.start(), match.end())
    for match in MAILGUN_KEY_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_API_KEY_MAILGUN, match.start(), match.end())
    for match in TWILIO_KEY_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_API_KEY_TWILIO, match.start(), match.end())
    for match in GOOGLE_API_KEY_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_API_KEY_GOOGLE, match.start(), match.end())
    for match in AZURE_CONNECTION_STRING_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_AZURE_CONNECTION_STRING, match.start(), match.end())
    for match in GITLAB_TOKEN_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_TOKEN_GITLAB, match.start(), match.end())
    for match in NPM_TOKEN_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_TOKEN_NPM, match.start(), match.end())
    for match in MAPBOX_TOKEN_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_API_KEY_MAPBOX, match.start(), match.end())
    for match in DB_CONNECTION_STRING_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_DB_CONNECTION_STRING, match.start(), match.end())
    for match in JWT_TOKEN_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_JWT_TOKEN, match.start(), match.end())
    for match in BEARER_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_GENERIC_BEARER, match.start(), match.end())
    for match in SPLIT_SECRET_PATTERN.finditer(text):
        _add(findings, claimed, spec13.DETECTOR_SPLIT_SECRET, match.start(), match.end())


def _scan_direct_patterns(text: str, findings: List[Finding], claimed: List[Tuple[int, int]]) -> None:
    """Ревизия 2026-08-05, третья (дефект 3): раньше нормализация похожих символов применялась
    только к email/phone. Прямые паттерны ключей её не получали вообще - подмена одной латинской
    буквы кириллическим двойником ломала поиск sk-/AKIA/ghp_ и так далее. Второй проход по
    confusable-нормализованной копии закрывает это, не трогая card/luhn - в CONFUSABLE_MAP нет ни
    одной подмены буква-на-цифру, только буква-на-визуально-похожую-букву другого алфавита."""
    _scan_direct_patterns_single(text, findings, claimed)
    normalized = _normalize_confusables(text)
    if normalized != text:
        _scan_direct_patterns_single(normalized, findings, claimed)


def _scan_reversed(text: str, findings: List[Finding], claimed: List[Tuple[int, int]]) -> None:
    length = len(text)
    if length == 0:
        return
    inner_findings: List[Finding] = []
    inner_claimed: List[Tuple[int, int]] = []
    _scan_direct_patterns(text[::-1], inner_findings, inner_claimed)
    for finding in inner_findings:
        _add(findings, claimed, finding.code, length - finding.end, length - finding.start)


def _stitch_candidates(text: str) -> List[Tuple[int, int, str]]:
    runs = [(match.start(), match.end(), match.group()) for match in KEY_RUN_PATTERN.finditer(text)]
    if len(runs) < 2 or len(runs) > STITCH_SAFETY_RUN_LIMIT:
        return []
    candidates: List[Tuple[int, int, str]] = []
    for start_index in range(len(runs)):
        group = [runs[start_index]]
        for next_index in range(start_index + 1, len(runs)):
            gap = runs[next_index][0] - group[-1][1]
            if gap <= 0 or gap > STITCH_MAX_GAP_CHARS:
                break
            if runs[next_index][1] - runs[start_index][0] > STITCH_MAX_WINDOW_CHARS:
                break
            if len(group) >= STITCH_MAX_RUNS:
                break
            group.append(runs[next_index])
            stitched_text = "".join(part for _, _, part in group)
            candidates.append((group[0][0], group[-1][1], stitched_text))
    return candidates


def _scan_stitched(text: str, findings: List[Finding], claimed: List[Tuple[int, int]]) -> None:
    for start, end, stitched in _stitch_candidates(text):
        if _overlaps(start, end, claimed):
            continue
        inner_findings: List[Finding] = []
        inner_claimed: List[Tuple[int, int]] = []
        _scan_direct_patterns(stitched, inner_findings, inner_claimed)
        if inner_findings:
            _add(findings, claimed, inner_findings[0].code, start, end)


def _try_base64_decode(candidate: str) -> Optional[str]:
    padded = candidate + "=" * (-len(candidate) % 4)
    try:
        raw = base64.b64decode(padded, validate=True)
    except (binascii.Error, ValueError):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _try_hex_decode(candidate: str) -> Optional[str]:
    trimmed = candidate if len(candidate) % 2 == 0 else candidate[:-1]
    if len(trimmed) < HEX_MIN_DECODE_LEN:
        return None
    try:
        raw = bytes.fromhex(trimmed)
    except ValueError:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _try_url_decode(candidate: str) -> Optional[str]:
    if "%" not in candidate:
        return None
    try:
        decoded = urllib.parse.unquote(candidate, errors="strict")
    except (UnicodeDecodeError, ValueError):
        return None
    if decoded == candidate:
        return None
    return decoded


def _direct_or_card_secret_found(text: str) -> bool:
    findings: List[Finding] = []
    claimed: List[Tuple[int, int]] = []
    _scan_direct_patterns(text, findings, claimed)
    if findings:
        return True
    for match in CARD_CANDIDATE_PATTERN.finditer(text):
        digits = NON_DIGIT_PATTERN.sub("", match.group())
        if luhn_valid(digits):
            return True
    return False


def _decoded_text_has_secret(text: str, depth: int) -> bool:
    if _direct_or_card_secret_found(text):
        return True
    if depth >= MAX_DECODE_DEPTH:
        return False
    for match in BASE64_CANDIDATE_PATTERN.finditer(text):
        decoded = _try_base64_decode(match.group())
        if decoded is not None and _decoded_text_has_secret(decoded, depth + 1):
            return True
    for match in HEX_CANDIDATE_PATTERN.finditer(text):
        decoded = _try_hex_decode(match.group())
        if decoded is not None and _decoded_text_has_secret(decoded, depth + 1):
            return True
    for match in URL_ENCODED_CANDIDATE_PATTERN.finditer(text):
        decoded = _try_url_decode(match.group())
        if decoded is not None and _decoded_text_has_secret(decoded, depth + 1):
            return True
    return False


def _scan_base64(text: str, findings: List[Finding], claimed: List[Tuple[int, int]]) -> None:
    for match in BASE64_CANDIDATE_PATTERN.finditer(text):
        if _overlaps(match.start(), match.end(), claimed):
            continue
        decoded = _try_base64_decode(match.group())
        if decoded is not None and _decoded_text_has_secret(decoded, 1):
            _add(findings, claimed, spec13.DETECTOR_BASE64_SECRET, match.start(), match.end())


def _scan_hex(text: str, findings: List[Finding], claimed: List[Tuple[int, int]]) -> None:
    for match in HEX_CANDIDATE_PATTERN.finditer(text):
        if _overlaps(match.start(), match.end(), claimed):
            continue
        decoded = _try_hex_decode(match.group())
        if decoded is not None and _decoded_text_has_secret(decoded, 1):
            _add(findings, claimed, spec13.DETECTOR_HEX_SECRET, match.start(), match.end())


def _scan_url_encoded(text: str, findings: List[Finding], claimed: List[Tuple[int, int]]) -> None:
    for match in URL_ENCODED_CANDIDATE_PATTERN.finditer(text):
        if _overlaps(match.start(), match.end(), claimed):
            continue
        decoded = _try_url_decode(match.group())
        if decoded is not None and _decoded_text_has_secret(decoded, 1):
            _add(findings, claimed, spec13.DETECTOR_URL_ENCODED_SECRET, match.start(), match.end())


def _scan_card(text: str, findings: List[Finding], claimed: List[Tuple[int, int]]) -> None:
    for match in CARD_CANDIDATE_PATTERN.finditer(text):
        if _overlaps(match.start(), match.end(), claimed):
            continue
        digits = NON_DIGIT_PATTERN.sub("", match.group())
        if not (13 <= len(digits) <= 19):
            continue
        if luhn_valid(digits):
            _add(findings, claimed, spec13.DETECTOR_CARD, match.start(), match.end())


def _normalize_confusables(text: str) -> str:
    return "".join(CONFUSABLE_MAP.get(char, char) for char in text)


def _scan_email_phone(text: str, findings: List[Finding], claimed: List[Tuple[int, int]]) -> None:
    normalized = _normalize_confusables(text)
    for candidate_text in (text, normalized):
        for match in EMAIL_PATTERN.finditer(candidate_text):
            _add(findings, claimed, spec13.DETECTOR_EMAIL, match.start(), match.end())
        for match in PHONE_PATTERN.finditer(candidate_text):
            _add(findings, claimed, spec13.DETECTOR_PHONE, match.start(), match.end())


def scan_secrets(text: str) -> List[Finding]:
    if not text:
        return []
    findings: List[Finding] = []
    claimed: List[Tuple[int, int]] = []
    _scan_direct_patterns(text, findings, claimed)
    _scan_reversed(text, findings, claimed)
    _scan_stitched(text, findings, claimed)
    _scan_base64(text, findings, claimed)
    _scan_hex(text, findings, claimed)
    _scan_url_encoded(text, findings, claimed)
    _scan_card(text, findings, claimed)
    _scan_email_phone(text, findings, claimed)
    findings.sort(key=lambda finding: finding.start)
    return findings


def mask_text(text: str, findings: List[Finding]) -> Tuple[str, int]:
    if not findings:
        return text, 0
    ordered = sorted(findings, key=lambda finding: finding.start, reverse=True)
    masked = text
    count = 0
    for finding in ordered:
        marker = spec13.MASK_BY_CATEGORY[finding.category]
        masked = masked[: finding.start] + marker + masked[finding.end :]
        count += 1
    return masked, count
