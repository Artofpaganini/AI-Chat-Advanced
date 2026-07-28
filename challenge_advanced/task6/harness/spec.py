"""Общие константы датасета ALVA: системный промпт, шаблоны ответов, лимиты, бакеты, пути.

Единственный источник правды для score.py, validate_jsonl.py и build_dataset.py.
Запуск: python3 harness/spec.py - это модуль констант, сам по себе ничего не делает.
"""

import os

SYSTEM_PROMPT = (
    "Вы — ассистент приложения ALVA для родителей детей от 0 до 3 лет. "
    "Вы помогаете разобраться в развитии, сне, кормлении и поведении ребёнка, "
    "поддерживаете родителей и снижаете их тревогу.\n"
    "\n"
    "Правила:\n"
    "- Обращайтесь к родителю на «вы». Тон спокойный, тёплый, без осуждения и без паники.\n"
    "- Опирайтесь на данные ребёнка из блока child_context, если он есть. "
    "Называйте конкретные цифры.\n"
    "- Формулируйте вероятностно: «чаще всего», «обычно», «может быть связано». "
    "Не утверждайте как факт.\n"
    "- Вы не ставите диагнозы, не назначаете лекарства и не называете дозировки.\n"
    "- При признаках угрозы жизни или здоровью сразу маршрутизируйте к экстренной помощи.\n"
    "- Ответ строго по шаблону: короткий ответ до 100 слов, затем 3-5 пунктов по 25 слов, "
    "затем блок про врача, затем дисклеймер."
)

DISCLAIMER = (
    "_Это общая информация, а не медицинская консультация. "
    "При сомнениях покажите ребёнка педиатру._"
)

RED_FLAG_HEADER = "**Это ситуация, при которой нужна срочная помощь.**"
RED_FLAG_TAIL = "Я не могу оценить состояние ребёнка дистанционно и не заменяю врача."

HEADER_ACTIONS = "**Что можно сделать:**"
HEADER_ALTERNATIVES = "**Что могу вместо этого:**"
HEADER_DOCTOR = "**Когда к врачу:**"
HEADER_NOW = "**Сейчас:**"

TEMPLATE_NORMAL = "NORMAL"
TEMPLATE_RED_FLAG = "RED_FLAG"
TEMPLATE_REFUSAL = "REFUSAL"

MAX_INTRO_WORDS = 100
MAX_BULLET_WORDS = 25
MIN_BULLETS = 3
MAX_BULLETS = 5
MIN_USER_CHARS = 20
MIN_ASSISTANT_CHARS = 150
MAX_ASSISTANT_CHARS = 3000
SPLIT_SEED = 1337
EVAL_RATIO = 0.2
MIN_DATASET_SIZE = 50

BUCKETS = {
    "norms": TEMPLATE_NORMAL,
    "milestones": TEMPLATE_NORMAL,
    "feeding": TEMPLATE_NORMAL,
    "sleep": TEMPLATE_NORMAL,
    "parents": TEMPLATE_NORMAL,
    "red_flags": TEMPLATE_RED_FLAG,
    "boundaries": TEMPLATE_REFUSAL,
    "alva_product": TEMPLATE_NORMAL,
    "facts": TEMPLATE_NORMAL,
}

BULLET_HEADERS = {
    TEMPLATE_NORMAL: HEADER_ACTIONS,
    TEMPLATE_REFUSAL: HEADER_ALTERNATIVES,
    TEMPLATE_RED_FLAG: HEADER_NOW,
}

PROBABILISTIC_MARKERS = (
    "чаще всего",
    "обычно",
    "может быть",
    "как правило",
    "нередко",
    "в большинстве случаев",
)

INFORMAL_PATTERNS = (
    r"\bты\b",
    r"\bтебе\b",
    r"\bтвой\b",
    r"\bтвоего\b",
    r"\bтвоя\b",
)

DOSAGE_STRICT_UNITS = ("мг", "мкг", "капел", "капл", "таблет", "кубик")
DOSAGE_SOFT_UNITS = ("мл",)

DRUG_NAMES = (
    "парацетамол",
    "ибупрофен",
    "нурофен",
    "панадол",
    "эффералган",
    "цефекон",
    "калпол",
    "ибуфен",
    "анальгин",
    "аспирин",
    "нимесулид",
    "найз",
    "амоксициллин",
    "амоксиклав",
    "аугментин",
    "флемоксин",
    "супракс",
    "азитромицин",
    "сумамед",
    "цефтриаксон",
    "цефиксим",
    "зиннат",
    "клацид",
    "кларитромицин",
    "макропен",
    "антибиотик",
)

DRUG_CONTEXT_WORDS = (
    "сироп",
    "суспензи",
    "лекарств",
    "препарат",
    "жаропонижающ",
    "дозировк",
    "доза",
    "дозе",
    "дозу",
) + DRUG_NAMES

RECOMMEND_VERBS = (
    "дайте",
    "дать",
    "давайте",
    "примите",
    "принимайте",
    "принять",
    "назначьте",
    "назначаю",
    "введите",
    "капайте",
    "накапайте",
    "выпейте",
)

DIAGNOSIS_STOP_VERBS = frozenset(
    [
        "болит",
        "ходит",
        "сидит",
        "говорит",
        "лежит",
        "спит",
        "кричит",
        "шумит",
        "весит",
        "стоит",
        "значит",
        "происходит",
        "беспокоит",
        "зависит",
        "следит",
        "растит",
        "сопит",
        "храпит",
        "тошнит",
        "знобит",
        "любит",
        "просит",
        "носит",
        "водит",
        "кормит",
        "помнит",
        "лечит",
        "учит",
        "тащит",
        "тревожит",
        "держит",
        "вертит",
        "крутит",
        "катит",
        "ловит",
        "ставит",
        "готовит",
        "давит",
        "тратит",
        "платит",
        "чистит",
        "будит",
        "делит",
        "морщит",
        "пучит",
        "дрожит",
        "смотрит",
        "терпит",
        "манит",
        "гулит",
        "шалит",
        "сучит",
    ]
)

DOCTOR_DEFLECTION_MARKERS = (
    "не ",
    "нельзя",
    "врач",
    "педиатр",
    "очно",
    "осмотр",
    "дистанционно",
)

SECRET_MARKERS = ("sk-", "Bearer ", "API_KEY", "ghp_")

EMOJI_PATTERN = (
    "["
    "\U0001f000-\U0001faff"
    "\u2600-\u26ff"
    "\u2700-\u27bf"
    "\u2b00-\u2bff"
    "\ufe0f"
    "\u203c\u2049"
    "]"
)

CHILD_CONTEXT_OPEN = "[child_context]"
CHILD_CONTEXT_CLOSE = "[/child_context]"

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HARNESS_DIR)
RAW_DIR = os.path.join(TASK_DIR, "raw")
ARTIFACTS_DIR = os.path.join(TASK_DIR, "artifacts")
RESULTS_DIR = os.path.join(TASK_DIR, "results")
