"""Входной гейт шлюза (GATEWAY_CONTRACT.md раздел 6, раздел 6.1).

check_input проверяет КАЖДОЕ сообщение запроса, не только последнее. Иначе, если что-то
замаскировано - запрос идёт наверх с маскированным текстом. Маскированная копия строится всегда,
даже при blocked - она нужна для превью в журнале аудита, куда сырой секрет попадать не должен
ни в каком виде.

Ревизия 2026-08-05, вторая (класс 5): секрет может быть разорван между двумя соседними сообщениями
истории - каждое сообщение по отдельности чистое, но при склейке образует настоящий ключ.
Дополнительно сканируется текст истории, склеенный переводом строки. Перевод строки выбран
разделителем нарочно: card/base64/hex-кандидаты по построению не могут захватить символ новой
строки внутри себя, поэтому склейка не может сложить два безобидных числа из разных сообщений в
номер карты или декодируемую строку - а вот сшивка ключевых префиксов (_scan_stitched в
secret_detectors) видит перевод строки как обычный разделитель и продолжает искать префикс+хвост
через него, то есть только целенаправленные форматы ключей могут "перепрыгнуть" стык сообщений.

Ревизия 2026-08-05, четвёртая (контракт раздел 6.1, дефект "мёртвый чат"): раньше блокирующий
детектор в ЛЮБОМ сообщении блокировал весь запрос навсегда - если пользователь один раз прислал
ключ, история уходит наверх при каждом следующем запросе, и старый ключ в ней блокирует чат снова
и снова, без выхода. Правило теперь: последнее сообщение с ролью "user" - новое, всё остальное -
история. Блок остаётся только за находками в новом сообщении (пользователь прямо сейчас пытается
отправить секрет - это стоит остановить). Находки только в старых сообщениях (включая склейку
между двумя старыми сообщениями) понижаются с блока до маски - секрет всё равно не уйдёт наверх,
но чат не умирает. Если секрет есть и там, и там - решает новое сообщение, блок остаётся.

Ревизия 2026-08-05, пятая (контракт раздел 6.1, второй дефект): мета-причина
DETECTOR_SECRET_IN_HISTORY раньше была привязана к понижению блока - у card/email/phone политика
и так mask, понижать нечего, поэтому признак никогда не вставал, и человек не понимал, что маска
сработала на СТАРОМ сообщении, а не на только что отправленном. Признак развязан с понижением: он
ставится, если находки есть и НИ ОДНА из них не задевает новое сообщение - независимо от action
детектора. Если хоть одна находка в новом сообщении - признак не ставится вообще, потому что
человек только что сам отправил секрет и должен смотреть на своё сообщение. Понижение блока до
маски (has_block) - отдельный, не связанный с этим признаком механизм, его не трогаем.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import secret_detectors
import spec13


@dataclass
class InputGuardResult:
    verdict: str
    reasons: List[str]
    masked_count: int
    messages: List[Dict[str, Any]]
    warning_text: str = ""


def _message_text(message: Dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        return "\n".join(parts)
    return ""


def _combined_text_with_offsets(texts: List[str]) -> Tuple[str, List[Tuple[int, int]]]:
    parts: List[str] = []
    offsets: List[Tuple[int, int]] = []
    cursor = 0
    for text in texts:
        start = cursor
        parts.append(text)
        cursor += len(text)
        offsets.append((start, cursor))
        parts.append("\n")
        cursor += 1
    return "".join(parts), offsets


def _message_index_at(position: int, offsets: List[Tuple[int, int]]) -> Optional[int]:
    for index, (start, end) in enumerate(offsets):
        if start <= position < end:
            return index
    return None


def _crosses_message_boundary(finding: secret_detectors.Finding, offsets: List[Tuple[int, int]]) -> bool:
    start_index = _message_index_at(finding.start, offsets)
    end_index = _message_index_at(max(finding.end - 1, finding.start), offsets)
    return start_index is None or end_index is None or start_index != end_index


def _local_overlaps(candidate: secret_detectors.Finding, existing: List[secret_detectors.Finding]) -> bool:
    return any(candidate.start < finding.end and candidate.end > finding.start for finding in existing)


def _new_message_index(messages: List[Dict[str, Any]]) -> int:
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].get("role") == "user":
            return index
    return len(messages) - 1


def check_input(messages: List[Dict[str, Any]]) -> InputGuardResult:
    texts = [_message_text(message) for message in messages]
    per_message_findings = [secret_detectors.scan_secrets(text) for text in texts]

    combined_text, offsets = _combined_text_with_offsets(texts)
    combined_findings = secret_detectors.scan_secrets(combined_text)
    boundary_findings = [
        finding for finding in combined_findings if _crosses_message_boundary(finding, offsets)
    ]

    if messages:
        new_index = _new_message_index(messages)
        new_start, new_end = offsets[new_index]
    else:
        new_index = -1
        new_start, new_end = 0, 0

    all_codes: List[str] = []
    has_block = False
    any_finding = False
    any_finding_in_new_message = False

    for index, findings in enumerate(per_message_findings):
        is_new_message = index == new_index
        for finding in findings:
            if finding.code not in all_codes:
                all_codes.append(finding.code)
            any_finding = True
            if is_new_message:
                any_finding_in_new_message = True
                if finding.action == spec13.ACTION_BLOCK:
                    has_block = True

    for finding in boundary_findings:
        if finding.code not in all_codes:
            all_codes.append(finding.code)
        any_finding = True
        touches_new_message = finding.start < new_end and finding.end > new_start
        if touches_new_message:
            any_finding_in_new_message = True
            if finding.action == spec13.ACTION_BLOCK:
                has_block = True

    if any_finding and not any_finding_in_new_message:
        all_codes.append(spec13.DETECTOR_SECRET_IN_HISTORY)

    masked_messages: List[Dict[str, Any]] = []
    total_masked = 0
    for index, message in enumerate(messages):
        text = texts[index]
        local_findings = list(per_message_findings[index])
        msg_start, msg_end = offsets[index]
        for finding in boundary_findings:
            overlap_start = max(finding.start, msg_start)
            overlap_end = min(finding.end, msg_end)
            if overlap_start >= overlap_end:
                continue
            local_finding = secret_detectors.Finding(
                code=finding.code,
                category=finding.category,
                action=finding.action,
                start=overlap_start - msg_start,
                end=overlap_end - msg_start,
                matched_len=overlap_end - overlap_start,
            )
            if not _local_overlaps(local_finding, local_findings):
                local_findings.append(local_finding)
        masked_text, count = secret_detectors.mask_text(text, local_findings)
        total_masked += count
        masked_message = dict(message)
        if isinstance(message.get("content"), str):
            masked_message["content"] = masked_text
        masked_messages.append(masked_message)

    if has_block:
        verdict = spec13.VERDICT_BLOCKED
        warning_text = spec13.INPUT_BLOCKED_WARNING
    elif all_codes:
        verdict = spec13.VERDICT_MASKED
        warning_text = ""
    else:
        verdict = spec13.VERDICT_PASS
        warning_text = ""

    return InputGuardResult(
        verdict=verdict,
        reasons=sorted(all_codes),
        masked_count=total_masked,
        messages=masked_messages,
        warning_text=warning_text,
    )
