"""Замороженные константы task7: маршруты, промпты, пороги, лимиты, цены, пути.

Единственный источник правды для guards.py, pipeline.py, run_eval.py и report.py.
Логики здесь нет - только значения, зафиксированные в SPEC.md до первого замера.
"""

import os

ROUTE_EMERGENCY = "EMERGENCY"
ROUTE_DOCTOR_SOON = "DOCTOR_SOON"
ROUTE_SELF_CARE = "SELF_CARE"
ROUTE_OFF_TOPIC = "OFF_TOPIC"

ROUTES = (ROUTE_EMERGENCY, ROUTE_DOCTOR_SOON, ROUTE_SELF_CARE, ROUTE_OFF_TOPIC)

SEVERITY = {
    ROUTE_EMERGENCY: 3,
    ROUTE_DOCTOR_SOON: 2,
    ROUTE_SELF_CARE: 1,
    ROUTE_OFF_TOPIC: 0,
}

STATUS_OK = "OK"
STATUS_UNSURE = "UNSURE"
STATUS_FAIL = "FAIL"
STATUSES = (STATUS_OK, STATUS_UNSURE, STATUS_FAIL)

MODE_BASELINE = "baseline"
MODE_PIPELINE = "pipeline"

SELF_CHECK_TRIGGER_AGREEMENT = "agreement"
SELF_CHECK_TRIGGER_RISK = "risk"
SELF_CHECK_TRIGGER_ALWAYS = "always"
SELF_CHECK_TRIGGER_NONE = "none"

SELF_CHECK_TRIGGERS = (
    SELF_CHECK_TRIGGER_AGREEMENT,
    SELF_CHECK_TRIGGER_RISK,
    SELF_CHECK_TRIGGER_ALWAYS,
)

SELF_CHECK_TRIGGER_TITLES = {
    SELF_CHECK_TRIGGER_AGREEMENT: "адаптивный, по разбросу голосов или подъёму",
    SELF_CHECK_TRIGGER_RISK: "по признаку риска в сообщении плюс старое условие",
    SELF_CHECK_TRIGGER_ALWAYS: "принудительный, на каждом кейсе",
    SELF_CHECK_TRIGGER_NONE: "критик не предусмотрен",
}

REPLY_KEYS = ("route", "red_flags", "age_months", "confidence", "reason")
CRITIC_KEYS = ("verdict", "risk_missed", "note")

VERDICT_AGREE = "AGREE"
VERDICT_DISAGREE = "DISAGREE"
VERDICTS = (VERDICT_AGREE, VERDICT_DISAGREE)

SOFT_PREFIX = "W_"
W_FENCED = "W_FENCED"

C_IN_EMPTY = "C_IN_EMPTY"
C_IN_NO_LETTERS = "C_IN_NO_LETTERS"

INPUT_CODES = (C_IN_EMPTY, C_IN_NO_LETTERS)

C_JSON = "C_JSON"
C_KEYS = "C_KEYS"
C_TYPES = "C_TYPES"
C_ROUTE_ENUM = "C_ROUTE_ENUM"
C_CONF_RANGE = "C_CONF_RANGE"
C_AGE_RANGE = "C_AGE_RANGE"
C_FLAGS_SHAPE = "C_FLAGS_SHAPE"
C_REASON_LEN = "C_REASON_LEN"
C_INV_EMERGENCY_FLAGS = "C_INV_EMERGENCY_FLAGS"
C_INV_SELFCARE_FLAGS = "C_INV_SELFCARE_FLAGS"
C_INV_OFFTOPIC_CLEAN = "C_INV_OFFTOPIC_CLEAN"
C_INV_CONF_FLOOR = "C_INV_CONF_FLOOR"

CONSTRAINT_CODES = (
    C_JSON,
    C_KEYS,
    C_TYPES,
    C_ROUTE_ENUM,
    C_CONF_RANGE,
    C_AGE_RANGE,
    C_FLAGS_SHAPE,
    C_REASON_LEN,
    C_INV_EMERGENCY_FLAGS,
    C_INV_SELFCARE_FLAGS,
    C_INV_OFFTOPIC_CLEAN,
    C_INV_CONF_FLOOR,
)

C_CRITIC_JSON = "C_CRITIC_JSON"
C_CRITIC_KEYS = "C_CRITIC_KEYS"
C_CRITIC_TYPES = "C_CRITIC_TYPES"
C_CRITIC_VERDICT_ENUM = "C_CRITIC_VERDICT_ENUM"
C_CRITIC_NOTE_LEN = "C_CRITIC_NOTE_LEN"

CRITIC_CODES = (
    C_CRITIC_JSON,
    C_CRITIC_KEYS,
    C_CRITIC_TYPES,
    C_CRITIC_VERDICT_ENUM,
    C_CRITIC_NOTE_LEN,
)

SOFT_CODES = (W_FENCED,)
ALL_CODES = INPUT_CODES + CONSTRAINT_CODES + CRITIC_CODES + SOFT_CODES

LOCATION_CLOUD = "cloud"
LOCATION_LOCAL = "local"
LOCAL_HOSTS = ("127.0.0.1", "localhost", "0.0.0.0", "::1")

NO_THINKING_PAYLOAD = {"chat_template_kwargs": {"enable_thinking": False}}
LOCAL_MAX_TOKENS = 700

OK_THRESHOLD = 0.75
UNSURE_THRESHOLD = 0.40

W_VOTE = 0.5
W_SELF_CHECK = 0.3
W_SELF_REPORT = 0.2

REDUNDANCY_SAMPLES = 3
TEMPERATURE_BASELINE = 0.0
TEMPERATURE_REDUNDANCY = 0.7
TEMPERATURE_SELF_CHECK = TEMPERATURE_BASELINE
MAX_TOKENS = 400
REPAIR_ATTEMPTS = 1

MAX_RED_FLAGS = 5
MAX_FLAG_CHARS = 60
MIN_REASON_CHARS = 3
MAX_REASON_CHARS = 200
MIN_AGE_MONTHS = 0
MAX_AGE_MONTHS = 60
MAX_NOTE_CHARS = 200

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_KEY_ENV = "DEEPSEEK_API_KEY"
REQUEST_TIMEOUT_SECONDS = 90
RETRY_DELAYS_SECONDS = (2, 5, 15)

PRICE_SOURCE_CONFIRMED = "confirmed"
PRICE_SOURCE_UNKNOWN = "unknown"
PRICE_SOURCE_LOCAL = "local"

DEEPSEEK_PRICE_URL = "https://api-docs.deepseek.com/quick_start/pricing"
OPENAI_PRICE_URL = "https://developers.openai.com/api/docs/pricing"

PRICES = {
    "deepseek-chat": {
        "input": 0.14,
        "cached_input": 0.0028,
        "output": 0.28,
        "source": PRICE_SOURCE_CONFIRMED,
        "source_url": DEEPSEEK_PRICE_URL,
        "resolved_as": "deepseek-v4-flash",
        "note": (
            "Имя deepseek-chat в прайсе отсутствует, это алиас. Проверено живым запросом "
            "2026-07-28: поле model в ответе API равно deepseek-v4-flash, по нему и берётся цена."
        ),
    },
    "deepseek-v4-flash": {
        "input": 0.14,
        "cached_input": 0.0028,
        "output": 0.28,
        "source": PRICE_SOURCE_CONFIRMED,
        "source_url": DEEPSEEK_PRICE_URL,
        "resolved_as": "deepseek-v4-flash",
        "note": "Прямое имя из прайса DeepSeek.",
    },
    "deepseek-v4-pro": {
        "input": 0.435,
        "cached_input": 0.003625,
        "output": 0.87,
        "source": PRICE_SOURCE_CONFIRMED,
        "source_url": DEEPSEEK_PRICE_URL,
        "resolved_as": "deepseek-v4-pro",
        "note": "Прямое имя из прайса DeepSeek.",
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "cached_input": 0.075,
        "output": 0.60,
        "source": PRICE_SOURCE_CONFIRMED,
        "source_url": OPENAI_PRICE_URL,
        "resolved_as": "gpt-4o-mini-2024-07-18",
        "note": (
            "Цена снята 2026-07-28 со страницы цен OpenAI: вход 0.15, кэшированный вход 0.075, "
            "выход 0.60 USD за 1M токенов. Кэш дешевле обычного входа вдвое, а не в 50 раз, "
            "как у DeepSeek."
        ),
    },
}

PRICE_UNKNOWN = {
    "input": 0.0,
    "cached_input": 0.0,
    "output": 0.0,
    "source": PRICE_SOURCE_UNKNOWN,
    "source_url": "",
    "resolved_as": "",
    "note": "Модель не найдена в таблице цен, стоимость не считается.",
}

CACHED_TOKEN_KEY = "prompt_cache_hit_tokens"
OPENAI_TOKEN_DETAILS_KEY = "prompt_tokens_details"
OPENAI_CACHED_TOKEN_KEY = "cached_tokens"

TOKENS_PER_MILLION = 1000000

RAW_SAMPLE_CHARS = 2000
CHARS_PER_TOKEN_ESTIMATE = 3.0

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HARNESS_DIR)
DATA_DIR = os.path.join(TASK_DIR, "data")
RAW_DIR = os.path.join(TASK_DIR, "raw")
RESULTS_DIR = os.path.join(TASK_DIR, "results")
REPO_ROOT = os.path.dirname(os.path.dirname(TASK_DIR))
LOCAL_PROPERTIES_PATH = os.path.join(REPO_ROOT, "local.properties")

DEFAULT_CASES_PATH = os.path.join(DATA_DIR, "cases.jsonl")
BASELINE_RUNS_NAME = "baseline_runs.jsonl"
PIPELINE_RUNS_NAME = "pipeline_runs.jsonl"
DEFAULT_REPORT_PATH = os.path.join(RESULTS_DIR, "confidence_report.json")

GROUP_CLEAN = "clean"
GROUP_BORDERLINE = "borderline"
GROUP_NOISY = "noisy"
GROUPS = (GROUP_CLEAN, GROUP_BORDERLINE, GROUP_NOISY)

FALLBACK_ANSWER = (
    "Не могу разобрать вопрос. Если вы тревожитесь за ребёнка - обратитесь к врачу, "
    "а при признаках угрозы жизни вызывайте скорую помощь."
)

RISK_AGE = "age_lt_3m"
RISK_BREATHING = "breathing"
RISK_NEURO = "neuro"
RISK_FEVER = "fever"
RISK_DEHYDRATION = "dehydration"
RISK_SKIN = "skin"
RISK_TRAUMA = "trauma"
RISK_BEHAVIOR = "behavior"

RISK_LABELS = (
    RISK_AGE,
    RISK_BREATHING,
    RISK_NEURO,
    RISK_FEVER,
    RISK_DEHYDRATION,
    RISK_SKIN,
    RISK_TRAUMA,
    RISK_BEHAVIOR,
)

RISK_LABEL_TITLES = {
    RISK_AGE: "возраст младше трёх месяцев",
    RISK_BREATHING: "дыхание и цвет губ",
    RISK_NEURO: "сознание и неврология",
    RISK_FEVER: "температура",
    RISK_DEHYDRATION: "пищеварение и обезвоживание",
    RISK_SKIN: "кожа и сыпь",
    RISK_TRAUMA: "травма и отравление",
    RISK_BEHAVIOR: "плач и поведение",
}

RISK_TEXT_LETTER_YO = "ё"
RISK_TEXT_LETTER_YE = "е"

RISK_TRIGGER_PATTERNS = (
    (RISK_AGE, r"новорожд"),
    (RISK_AGE, r"\b(?:[1-9]|1[0-2])\s*(?:-|–)?\s*недел"),
    (RISK_AGE, r"\b(?:[1-9]|1[0-2])\s*нед\b"),
    (RISK_AGE, r"\b(?:одну|одна|две|три|четыре|пять|шесть|семь|восемь|девять|десять|полторы|пару)\s*недел"),
    (RISK_AGE, r"\b(?:[0-2]|один|одного|два|полтора|полутора)\s*(?:-|–)?\s*месяц"),
    (RISK_AGE, r"\b[0-2][.,]\d\s*месяц"),
    (RISK_AGE, r"\b(?:нам|ему|ей|ребенку|малышу|сыну|дочери|дочке)\s+(?:всего\s+|только\s+)?месяц\b"),
    (RISK_AGE, r"\b(?:всего|только)\s+месяц\b"),
    (RISK_AGE, r"месяц\s+назад\s+родил"),
    (RISK_AGE, r"недел\w*\s+назад\s+родил"),
    (RISK_AGE, r"родил(?:ся|ась|ись)\s+(?:\w+\s+){0,2}(?:недел|дн|мес)"),
    (RISK_AGE, r"роддом"),
    (RISK_AGE, r"\b(?:дн(?:ей|я)|суток)\s+(?:от\s+роду|жизни)"),
    (RISK_AGE, r"перв(?:ые|ых)\s+(?:дни|дней|недел)\s+жизни"),
    (RISK_BREATHING, r"дыш"),
    (RISK_BREATHING, r"дыхан"),
    (RISK_BREATHING, r"одышк"),
    (RISK_BREATHING, r"хрип"),
    (RISK_BREATHING, r"задыха"),
    (RISK_BREATHING, r"втяг"),
    (RISK_BREATHING, r"втяжен"),
    (RISK_BREATHING, r"свистящ"),
    (RISK_BREATHING, r"апно"),
    (RISK_BREATHING, r"кряхт"),
    (RISK_BREATHING, r"поперхн"),
    (RISK_BREATHING, r"подавил"),
    (RISK_BREATHING, r"синеет"),
    (RISK_BREATHING, r"посинел"),
    (RISK_BREATHING, r"синюшн"),
    (RISK_BREATHING, r"цианоз"),
    (RISK_BREATHING, r"губы\s+син"),
    (RISK_NEURO, r"судорог"),
    (RISK_NEURO, r"конвульс"),
    (RISK_NEURO, r"обмяк"),
    (RISK_NEURO, r"обвис"),
    (RISK_NEURO, r"не\s+(?:могу\s+)?(?:раз)?буд"),
    (RISK_NEURO, r"не\s+просыпа"),
    (RISK_NEURO, r"не\s+реагир"),
    (RISK_NEURO, r"без\s+сознан"),
    (RISK_NEURO, r"сознан"),
    (RISK_NEURO, r"вял"),
    (RISK_NEURO, r"затормож"),
    (RISK_NEURO, r"закатыва"),
    (RISK_NEURO, r"подергив"),
    (RISK_NEURO, r"запрокид"),
    (RISK_NEURO, r"родничок"),
    (RISK_NEURO, r"родничк"),
    (RISK_FEVER, r"температур"),
    (RISK_FEVER, r"лихорад"),
    (RISK_FEVER, r"градус"),
    (RISK_FEVER, r"\bжар(?:а|ом|у)?\b"),
    (RISK_FEVER, r"озноб"),
    (RISK_FEVER, r"горяч"),
    (RISK_FEVER, r"\b3[89](?:[.,]\d)?\b"),
    (RISK_FEVER, r"\b4[01](?:[.,]\d)?\b"),
    (RISK_DEHYDRATION, r"рвот"),
    (RISK_DEHYDRATION, r"рвет"),
    (RISK_DEHYDRATION, r"вырвал"),
    (RISK_DEHYDRATION, r"фонтан"),
    (RISK_DEHYDRATION, r"обезвож"),
    (RISK_DEHYDRATION, r"не\s+писа"),
    (RISK_DEHYDRATION, r"не\s+мочит"),
    (RISK_DEHYDRATION, r"сух(?:ой|ие|ими)\s+(?:памперс|подгузник)"),
    (RISK_DEHYDRATION, r"памперс\w*\s+(?:\w+\s+){0,2}сух"),
    (RISK_DEHYDRATION, r"понос"),
    (RISK_DEHYDRATION, r"диаре"),
    (RISK_DEHYDRATION, r"жидкий\s+стул"),
    (RISK_DEHYDRATION, r"отказ\w*\s+от\s+(?:груди|еды|питья|бутылочки|смеси)"),
    (RISK_DEHYDRATION, r"не\s+пьет"),
    (RISK_DEHYDRATION, r"не\s+ест"),
    (RISK_DEHYDRATION, r"запавш"),
    (RISK_DEHYDRATION, r"сухой\s+язык"),
    (RISK_DEHYDRATION, r"без\s+слез"),
    (RISK_SKIN, r"сып[ьи]"),
    (RISK_SKIN, r"высыпан"),
    (RISK_SKIN, r"пятн"),
    (RISK_SKIN, r"красн\w*\s+точк"),
    (RISK_SKIN, r"не\s+бледне"),
    (RISK_SKIN, r"надавлив"),
    (RISK_SKIN, r"при\s+надав"),
    (RISK_SKIN, r"синяк"),
    (RISK_SKIN, r"кровоподт"),
    (RISK_SKIN, r"геморраг"),
    (RISK_SKIN, r"петехи"),
    (RISK_SKIN, r"бледн"),
    (RISK_SKIN, r"мраморн"),
    (RISK_SKIN, r"желтуш"),
    (RISK_SKIN, r"желтизн"),
    (RISK_TRAUMA, r"упал"),
    (RISK_TRAUMA, r"свалил"),
    (RISK_TRAUMA, r"удар"),
    (RISK_TRAUMA, r"стукнул"),
    (RISK_TRAUMA, r"травм"),
    (RISK_TRAUMA, r"проглот"),
    (RISK_TRAUMA, r"глотнул"),
    (RISK_TRAUMA, r"выпил"),
    (RISK_TRAUMA, r"отрав"),
    (RISK_TRAUMA, r"ожог"),
    (RISK_TRAUMA, r"обварил"),
    (RISK_TRAUMA, r"кипятк"),
    (RISK_TRAUMA, r"таблетк"),
    (RISK_TRAUMA, r"бытов\w*\s+хими"),
    (RISK_TRAUMA, r"засунул"),
    (RISK_TRAUMA, r"застрял"),
    (RISK_TRAUMA, r"кровотеч"),
    (RISK_TRAUMA, r"кровь"),
    (RISK_BEHAVIOR, r"плач\w*\s+(?:уже\s+)?(?:\d+|неск\w*|полтора|два|три)\s*час"),
    (RISK_BEHAVIOR, r"плачет\s+(?:уже\s+)?час"),
    (RISK_BEHAVIOR, r"безутешн"),
    (RISK_BEHAVIOR, r"не\s+успокаива"),
    (RISK_BEHAVIOR, r"не\s+могу\s+успокоить"),
    (RISK_BEHAVIOR, r"необычн"),
    (RISK_BEHAVIOR, r"не\s+как\s+всегда"),
    (RISK_BEHAVIOR, r"сам\s+не\s+свой"),
    (RISK_BEHAVIOR, r"странно\s+себя\s+вед"),
    (RISK_BEHAVIOR, r"пронзительн"),
    (RISK_BEHAVIOR, r"монотонн"),
    (RISK_BEHAVIOR, r"крик\s+на\s+одной\s+ноте"),
)

TRIAGE_SYSTEM_PROMPT = (
    "Вы - модуль триажа приложения ALVA для родителей детей от 0 до 5 лет. "
    "Родитель присылает свободный текст, вы решаете, что с этим сообщением делать.\n"
    "\n"
    "Маршруты:\n"
    "- EMERGENCY - есть признаки состояния, угрожающего жизни или требующего помощи прямо сейчас: "
    "затруднённое или частое дыхание, синюшность губ и кожи, судороги, потеря сознания, "
    "необычная вялость или невозможность разбудить, температура 38 и выше у ребёнка младше 3 месяцев, "
    "сыпь, не бледнеющая при надавливании, признаки обезвоживания с отказом от питья, "
    "травма головы с рвотой или потерей сознания, проглоченный предмет или химия, сильное кровотечение.\n"
    "- DOCTOR_SOON - врач нужен в ближайшие дни, но угрозы жизни сейчас нет: температура держится "
    "больше трёх дней, затяжной кашель, сыпь без других тревожных признаков, боль в ухе, "
    "остановка набора веса, состояние ухудшается медленно.\n"
    "- SELF_CARE - обычный родительский вопрос про сон, кормление, развитие, поведение, уход. "
    "Тревожных признаков в сообщении нет.\n"
    "- OFF_TOPIC - сообщение не про ребёнка и не про здоровье.\n"
    "\n"
    "Правило безопасности: если сомневаетесь между двумя маршрутами - выбирайте тот, что выше по тяжести. "
    "Пропустить опасное состояние хуже, чем поднять ложную тревогу.\n"
    "\n"
    "ВЕРНИТЕ ТОЛЬКО JSON-объект ровно такой схемы и ничего больше:\n"
    '{"route": "EMERGENCY", "red_flags": ["затруднённое дыхание"], "age_months": 8, '
    '"confidence": 0.93, "reason": "Дыхательная недостаточность у грудного ребёнка"}\n'
    "\n"
    "Поля:\n"
    "- route - ровно одно из значений: EMERGENCY, DOCTOR_SOON, SELF_CARE, OFF_TOPIC.\n"
    "- red_flags - список строк, от 0 до 5 элементов, каждый до 60 символов. "
    "Только те тревожные признаки, которые действительно есть в сообщении.\n"
    "- age_months - целое число от 0 до 60, либо null, если возраст в сообщении не указан. "
    "Возраст не выдумывайте.\n"
    "- confidence - число от 0.0 до 1.0, ваша честная самооценка. Не завышайте её: "
    "если случай спорный или данных мало, ставьте низкое значение.\n"
    "- reason - строка от 3 до 200 символов, одна короткая фраза.\n"
    "\n"
    "Инварианты, нарушать которые нельзя:\n"
    "- route = EMERGENCY -> red_flags непустой и confidence не меньше 0.5.\n"
    "- route = SELF_CARE -> red_flags пустой.\n"
    "- route = OFF_TOPIC -> red_flags пустой и age_months = null.\n"
    "\n"
    "Запрещено: markdown-заборы, любой текст до или после JSON, лишние или пропущенные ключи, "
    "комментарии внутри JSON. В ответе должен быть только объект с пятью ключами."
)

CRITIC_SYSTEM_PROMPT = (
    "Вы - независимый критик решения триажа в приложении ALVA. "
    "Вам дают исходное сообщение родителя и маршрут, который предложил первый проход. "
    "Ваша работа - не согласиться из вежливости, а проверить.\n"
    "\n"
    "Прежде чем отвечать, отдельно продумайте про себя: нет ли в сообщении опасного признака, "
    "который первый проход упустил или недооценил. Пройдитесь по списку: дыхание, сознание и реакция, "
    "судороги, цвет кожи и губ, признаки обезвоживания, возраст младше 3 месяцев с температурой, "
    "травма головы, сыпь, не бледнеющая при надавливании, отравление или проглоченный предмет. "
    "Только после этой проверки формируйте вердикт.\n"
    "\n"
    "Маршруты по возрастанию тяжести: OFF_TOPIC, SELF_CARE, DOCTOR_SOON, EMERGENCY.\n"
    "\n"
    "ВЕРНИТЕ ТОЛЬКО JSON-объект такой схемы и ничего больше:\n"
    '{"verdict": "AGREE", "risk_missed": false, "note": "коротко почему"}\n'
    "\n"
    "Поля:\n"
    "- verdict - AGREE, если предложенный маршрут вас устраивает, иначе DISAGREE.\n"
    "- risk_missed - true только если вы видите опасный признак, который предложенный маршрут "
    "не учитывает. Это автоматически поднимет случай до экстренного, поэтому ставьте true осознанно, "
    "но не молчите, если признак действительно есть.\n"
    "- note - строка до 200 символов.\n"
    "\n"
    "Запрещено: markdown-заборы, текст до или после JSON, лишние ключи."
)

CRITIC_USER_TEMPLATE = (
    "Сообщение родителя:\n"
    "{case_text}\n"
    "\n"
    "Предложенный маршрут: {route}\n"
    "Названные тревожные признаки: {red_flags}\n"
    "Обоснование первого прохода: {reason}\n"
    "\n"
    "Проверьте это решение и верните JSON."
)

REPAIR_HINT = (
    "Ваш прошлый ответ нарушил ограничения формата: {violations}.\n"
    "Верните исправленный ответ на то же сообщение родителя. "
    "Только JSON-объект с пятью ключами route, red_flags, age_months, confidence, reason. "
    "Без markdown-заборов, без текста вокруг, без лишних ключей. "
    "Соблюдите инварианты: EMERGENCY требует непустой red_flags и confidence не меньше 0.5, "
    "SELF_CARE требует пустой red_flags, OFF_TOPIC требует пустой red_flags и age_months = null."
)

EMPTY_FLAGS_PLACEHOLDER = "нет"
