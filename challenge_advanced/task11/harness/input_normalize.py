"""L0_INPUT_NORMALIZE - раскодирует очевидные кодировки во входе до того, как текст уйдёт в модель
(контракт раздел 5, добавлено 2026-08-03 по находке про generic_t5_devmode - ни один из трёх
слоёв не читает то, что декодируется только внутри модели).

Правило - про класс кодирования, а не про атаку: любая строка, похожая на base64/ROT13/разрядку
пробелами, раскодируется и проверяется на признаки инъекции тем же списком фраз, независимо от
того, что конкретно в ней написано. Список INJECTION_SIGNAL_PHRASES - про механику ("забудь
инструкции", "покажи системный промпт", "developer mode"), не про текст конкретной атаки набора.
"""

import base64
import codecs
import re
from typing import List, Tuple

BASE64_CANDIDATE_PATTERN = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")
# Прогон слов на латинице через простую пунктуацию - весь кусок, не один непрерывный токен
# (ROT13 текст остаётся обычными словами через пробел, а не одной длинной "простынёй" букв).
LATIN_RUN_PATTERN = re.compile(r"[A-Za-z][A-Za-z ,.'\"!?;:]*[A-Za-z]")
MIN_ROT13_LETTERS = 20

MIN_PRINTABLE_RATIO = 0.85

COMMON_ENGLISH_WORDS = (
    "the", "you", "your", "and", "are", "is", "to", "instructions", "ignore", "system",
    "this", "that", "with", "for", "not", "have", "will", "print", "reveal", "developer",
    "mode", "content", "policy", "all", "previous", "prompt",
)

# Про класс, не про атаку: сигнал инъекции - это глагол-отмена (забудь/игнорируй/отмени) рядом
# со словом-целью (инструкции/правила/промпт), ЛИБО прямое упоминание известной джейлбрейк-роли/
# режима. Совместное появление ловится по стемам, а не по точной фразе - иначе "игнорируй все
# предыдущие инструкции" не совпадёт с заготовленной "игнорируй предыдущие инструкции".
OVERRIDE_VERB_STEMS = (
    "игнориру", "забуд", "отмени", "перепиш", "не признаю", "не выполня",
    "ignore", "forget", "disregard", "override", "bypass",
    # reveal-глаголы - другой класс той же T3_EXTRACT механики (не отменить, а показать/повторить)
    "вывед", "вывод", "покажи", "раскрой", "раскры", "повтор",
    "reveal", "show", "print", "output", "display", "repeat",
)
INSTRUCTION_TARGET_STEMS = (
    "инструкц", "правил", "промпт", "ограничен", "instruction", "system prompt",
    "rule", "restriction", "guideline",
)
PERSONA_SIGNAL_PHRASES = (
    "developer mode", "dan mode", "do anything now", "режим разработчика",
    "no content policy", "no restrictions", "without any restrictions", "without restrictions",
    "you are dan", "i am dan", "unfiltered ai", "без цензуры", "без фильтров",
)


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    printable = sum(1 for char in text if char.isprintable() or char in "\n\r\t")
    return printable / len(text)


def decode_base64_candidates(text: str) -> List[str]:
    decoded: List[str] = []
    for match in BASE64_CANDIDATE_PATTERN.finditer(text):
        candidate = match.group()
        padded = candidate + "=" * (-len(candidate) % 4)
        try:
            raw = base64.b64decode(padded, validate=False)
            value = raw.decode("utf-8")
        except Exception:
            continue
        if value.strip() and _printable_ratio(value) >= MIN_PRINTABLE_RATIO:
            decoded.append(value)
    return decoded


LETTER_RUN_PATTERN = re.compile(r"(?:[a-zа-яё][ \-]){4,}[a-zа-яё]", re.IGNORECASE)


def decode_letter_spaced(text: str) -> List[str]:
    """Разрядка встречается и через пробел, и через дефис - оба разделителя внутри одного
    совпадения просто убираются. Границы слов не восстанавливаются, но для проверки на стемы
    инструкций это не нужно: стем ищется подстрокой, а не отдельным словом."""
    decoded: List[str] = []
    for match in LETTER_RUN_PATTERN.finditer(text):
        collapsed = re.sub(r"[ \-]", "", match.group())
        decoded.append(collapsed)
    return decoded


def decode_rot13_candidates(text: str) -> List[str]:
    decoded: List[str] = []
    for match in LATIN_RUN_PATTERN.finditer(text):
        original = match.group()
        if sum(1 for char in original if char.isalpha()) < MIN_ROT13_LETTERS:
            continue
        rotated = codecs.encode(original, "rot13")
        original_words = _count_common_words(original)
        rotated_words = _count_common_words(rotated)
        if rotated_words > original_words and rotated_words >= 2:
            decoded.append(rotated)
    return decoded


def _count_common_words(text: str) -> int:
    lowered = text.lower()
    return sum(1 for word in COMMON_ENGLISH_WORDS if word in lowered)


def extract_decoded_layers(text: str) -> List[str]:
    layers: List[str] = []
    layers.extend(decode_base64_candidates(text))
    layers.extend(decode_letter_spaced(text))
    layers.extend(decode_rot13_candidates(text))
    return layers


def injection_signal_reason(text: str) -> str:
    lowered = text.lower()
    has_override = any(stem in lowered for stem in OVERRIDE_VERB_STEMS)
    has_target = any(stem in lowered for stem in INSTRUCTION_TARGET_STEMS)
    if has_override and has_target:
        return "override_verb_plus_instruction_target"
    for phrase in PERSONA_SIGNAL_PHRASES:
        if phrase in lowered:
            return "persona_signal_%s" % phrase.replace(" ", "_")
    return ""


def normalize_and_check(raw_text: str) -> Tuple[bool, List[str], List[str]]:
    """Возвращает (blocked, decoded_layers, matched_reasons).

    blocked=True - раскодированный слой (или сам исходный текст) содержит признак инъекции,
    сообщение целиком отклоняется, в модель ничего не уходит. Проверяются и исходный текст, и все
    найденные декодированные слои - отклонённая атака могла спрятать сигнал в открытом виде рядом
    с закодированным куском.
    """
    layers = extract_decoded_layers(raw_text)
    # раскодированные фрагменты letter-spaced не хранят границы слов (пример: "выведи", "системный",
    # "промпт" - три отдельных куска) - глагол и цель могут оказаться в разных элементах списка,
    # поэтому дополнительно проверяем все слои разом, склеенными в одну строку.
    all_text_to_check = [raw_text] + layers + ([" ".join(layers)] if len(layers) > 1 else [])
    matched: List[str] = []
    for chunk in all_text_to_check:
        reason = injection_signal_reason(chunk)
        if reason and reason not in matched:
            matched.append(reason)
    return bool(matched), layers, matched
