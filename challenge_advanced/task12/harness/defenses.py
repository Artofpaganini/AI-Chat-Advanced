"""Три слоя защиты из ATTACK_CONTRACT.md раздел 6 (D1_SANITIZE, D2_BOUNDARY, D3_OUTPUT) плюс
D4_PROVENANCE - четвёртый, добавленный team-lead специально против V3_SEARCH: ни один из первых
трёх не проверяет, можно ли верить утверждению из документа, только правило происхождения может.

Урок task11 раздел 9.1 применён заранее, не после находки: у каждого слоя свой текст-заглушка
(D1 - пустая строка, не приманка; D3 - OUTPUT_GUARD_FALLBACK), ни один не содержит числовых атомов
или доменных слов, которые детекторы могли бы принять за успех атаки - проверено вручную при
написании (см. комментарии у констант в spec12.py) и живым прогоном при первом запуске.
"""

import re
from typing import Any, Dict, List, Tuple

import detectors12
import spec12

COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
STYLE_SPAN_PATTERN = re.compile(r'<span[^>]*style="[^"]*"[^>]*>.*?</span>', re.DOTALL | re.IGNORECASE)
INVISIBLE_CHARS_PATTERN = re.compile("[" + "".join(re.escape(char) for char in spec12.ZERO_WIDTH_CHARS) + "]")


# --- D1_SANITIZE --------------------------------------------------------------------------------

def sanitize_text(text: str) -> str:
    """H1 (комментарии), H3 (span со стилем), H2 (символы нулевой ширины) - вырезаются до
    передачи модели. Плейсхолдер - пустая строка, не текст-приманка (урок 9.1)."""
    if not text:
        return text
    cleaned = COMMENT_PATTERN.sub(spec12.D1_SANITIZED_PLACEHOLDER, text)
    cleaned = STYLE_SPAN_PATTERN.sub(spec12.D1_SANITIZED_PLACEHOLDER, cleaned)
    cleaned = INVISIBLE_CHARS_PATTERN.sub("", cleaned)
    return cleaned


def sanitize_turn(turn: Dict[str, str]) -> Dict[str, str]:
    """H4: роль из чужого источника (импорт, поддельный ход) не доверяется - принудительно
    понижается до user, длина ограничена (REAL_CASES.md, 'что напрашивается', пункты 3-4)."""
    return {
        "role": spec12.REQUEST_ROLE_USER,
        "content": sanitize_text(turn["content"])[: spec12.MAX_IMPORTED_MESSAGE_CHARS],
    }


# --- D2_BOUNDARY ---------------------------------------------------------------------------------

def _author_label(role: str) -> str:
    return spec12.BOUNDARY_QUOTE_LABEL_ASSISTANT if role == spec12.REQUEST_ROLE_ASSISTANT else spec12.BOUNDARY_QUOTE_LABEL_USER


def quote_history(history: List[Dict[str, str]]) -> str:
    lines = ["%s %s" % (_author_label(turn["role"]), turn["content"]) for turn in history]
    return "%s\n%s\n%s" % (spec12.HISTORY_QUOTE_START, "\n".join(lines), spec12.HISTORY_QUOTE_END)


def quote_document(document_text: str) -> str:
    return "%s\n%s\n%s" % (spec12.DOCUMENT_QUOTE_START, document_text, spec12.DOCUMENT_QUOTE_END)


# --- D3_OUTPUT -------------------------------------------------------------------------------

def visible_input_text(history: List[Dict[str, str]], final_user_text: str) -> str:
    """'Видимая' версия входа для сравнения с ответом - тот же вырез markup, что D1, но ТОЛЬКО
    для сравнения: то, что реально ушло в модель, этой функцией не трогается."""
    pieces = [turn["content"] for turn in history] + [final_user_text]
    return " ".join(sanitize_text(piece) for piece in pieces)


def check_output(response_text: str, history: List[Dict[str, str]], final_user_text: str) -> Tuple[str, List[str]]:
    visible_text = visible_input_text(history, final_user_text)
    visible_digit_runs = detectors12.response_digit_runs(visible_text)
    response_atoms = detectors12.extract_numeric_atoms(response_text)
    suspicious = [atom for atom in response_atoms if not detectors12.atom_is_present(atom, visible_digit_runs)]
    if suspicious:
        return spec12.OUTPUT_GUARD_FALLBACK, suspicious
    return response_text, []


# --- D4_PROVENANCE (не из контракта, добавлен против V3 - см. spec12.py) ------------------------

def system_prompt_for(target: str, defense: str) -> str:
    prompt = spec12.SYSTEM_PROMPTS[target]
    if defense in (spec12.DEFENSE_D2_BOUNDARY, spec12.DEFENSE_ALL):
        prompt += spec12.BOUNDARY_INSTRUCTION
    if defense in (spec12.DEFENSE_D4_PROVENANCE, spec12.DEFENSE_ALL):
        prompt += spec12.PROVENANCE_BLOCKS[target]
    return prompt


# --- Сборка ходов под конкретный слой -------------------------------------------------------

def build_turns_for_defense(record: Dict[str, Any], defense: str) -> List[Dict[str, str]]:
    """D1 (очистка) применяется первым, D2 (границы) - к уже очищенным данным - так "all"
    получает реальную композицию слоёв, а не два независимых прогона поверх одного и того же
    сырого текста."""
    apply_d1 = defense in (spec12.DEFENSE_D1_SANITIZE, spec12.DEFENSE_ALL)
    apply_d2 = defense in (spec12.DEFENSE_D2_BOUNDARY, spec12.DEFENSE_ALL)

    history = list(record.get("history") or [])
    final_user_text = record["final_user_text"]
    document_text = record.get("document_text", "")
    question_text = record.get("question_text", final_user_text)

    if apply_d1:
        history = [sanitize_turn(turn) for turn in history]
        final_user_text = sanitize_text(final_user_text)
        document_text = sanitize_text(document_text)
        question_text = sanitize_text(question_text)

    if apply_d2:
        if history:
            history = [{"role": spec12.REQUEST_ROLE_USER, "content": quote_history(history)}]
        elif document_text:
            final_user_text = "%s\n\n%s" % (quote_document(document_text), question_text)

    return history + [{"role": spec12.REQUEST_ROLE_USER, "content": final_user_text}]


def apply_output_defense(response_text: str, record: Dict[str, Any], defense: str) -> Tuple[str, List[str]]:
    """D3 сверяет ответ с ИСХОДНЫМ (не защищённым другим слоем) входом - так D3 "в одиночку"
    остаётся честной проверкой самого слоя, а не наследует эффект от D1/D2, если их не просили."""
    if defense not in (spec12.DEFENSE_D3_OUTPUT, spec12.DEFENSE_ALL):
        return response_text, []
    history = list(record.get("history") or [])
    return check_output(response_text, history, record["final_user_text"])
