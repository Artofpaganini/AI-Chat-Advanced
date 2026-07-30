"""Замороженные константы task9: промпты этапов, имена полей, лимиты, коды ошибок, пути.

Логики здесь нет - только значения из SPEC.md, зафиксированные до первого замера.
Всё про саму задачу триажа (маршруты, цены, гарды, промпт монолита) берётся из spec7 task7.

Промпты этапов намеренно короткие. Этап должен быть дешёвым: чем короче системный текст, тем
меньше вход каждого из трёх вызовов, иначе цепочка проигрывает монолиту ещё до первого замера.
"""

import os
import sys

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK9_DIR = os.path.dirname(HARNESS_DIR)
CHALLENGE_DIR = os.path.dirname(TASK9_DIR)
TASK7_DIR = os.path.join(CHALLENGE_DIR, "task7")
TASK7_HARNESS_DIR = os.path.join(TASK7_DIR, "harness")

if TASK7_HARNESS_DIR not in sys.path:
    sys.path.insert(0, TASK7_HARNESS_DIR)

import spec7
import spec_v2

ROUTES = spec_v2.ROUTES
SEVERITY = spec_v2.SEVERITY

MODE_MONOLITHIC = "monolithic"
MODE_MULTISTAGE = "multistage"
MODE_BOTH = "both"
MODES = (MODE_MONOLITHIC, MODE_MULTISTAGE)

STAGE_MONOLITHIC = "monolithic"
STAGE_PARSE = "stage1_parse"
STAGE_DECIDE = "stage2_decide"
STAGE_ANSWER = "stage3_answer"

MULTISTAGE_STAGES = (STAGE_PARSE, STAGE_DECIDE, STAGE_ANSWER)
ALL_STAGES = (STAGE_MONOLITHIC,) + MULTISTAGE_STAGES

STAGE_TITLES = {
    STAGE_MONOLITHIC: "весь запрос",
    STAGE_PARSE: "этап 1, разбор",
    STAGE_DECIDE: "этап 2, решение",
    STAGE_ANSWER: "этап 3, ответ",
}

F_AGE = "AGE_MONTHS"
F_SYMPTOMS = "SYMPTOMS"
F_METRICS = "METRICS"
F_DURATION = "DURATION"
F_PARENT_STATE = "PARENT_STATE"
F_QUESTION_TYPE = "QUESTION_TYPE"

STAGE1_FIELDS = (F_AGE, F_SYMPTOMS, F_METRICS, F_DURATION, F_PARENT_STATE, F_QUESTION_TYPE)

QT_CARE = "CARE"
QT_METRICS = "METRICS"
QT_PARENT = "PARENT"
QT_OTHER = "OTHER"

QUESTION_TYPES = (QT_CARE, QT_METRICS, QT_PARENT, QT_OTHER)

D_ROUTE = "ROUTE"
D_CONFIDENCE = "CONFIDENCE"
D_WHY = "WHY"

STAGE2_FIELDS = (D_ROUTE, D_CONFIDENCE, D_WHY)

NONE_VALUE = "none"
PAIR_SEPARATOR = "="
FIELD_SEPARATOR = "|"
SYMPTOM_SEPARATOR = ";"

MAX_SYMPTOMS = 5
MAX_SYMPTOM_CHARS = 60
MAX_METRICS_CHARS = 120
MAX_DURATION_CHARS = 60
MAX_PARENT_STATE_CHARS = 80
MAX_WHY_CHARS = 100
MIN_ANSWER_CHARS = 20
MAX_ANSWER_CHARS = 1200

MIN_AGE_MONTHS = spec7.MIN_AGE_MONTHS
MAX_AGE_MONTHS = spec7.MAX_AGE_MONTHS
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0

S1_PARSE = "S1_PARSE"
S2_PARSE = "S2_PARSE"
S3_EMPTY = "S3_EMPTY"
S1_ROUTE_LEAKED = "S1_ROUTE_LEAKED"

STAGE_ERROR_CODES = (S1_PARSE, S2_PARSE, S3_EMPTY, S1_ROUTE_LEAKED)

STAGE_ERROR_TITLES = {
    S1_PARSE: "этап 1 вернул неразбираемый формат",
    S2_PARSE: "этап 2 вернул неразбираемый формат или маршрут вне перечисления",
    S3_EMPTY: "этап 3 вернул пустой или слишком короткий текст",
    S1_ROUTE_LEAKED: "этап 1 назвал маршрут, хотя решать ему запрещено",
}

STAGE_ERROR_OWNER = {
    S1_PARSE: STAGE_PARSE,
    S1_ROUTE_LEAKED: STAGE_PARSE,
    S2_PARSE: STAGE_DECIDE,
    S3_EMPTY: STAGE_ANSWER,
}

LEAK_TOKENS = ROUTES

STAGE1_MAX_TOKENS = 200
STAGE2_MAX_TOKENS = 100
STAGE3_MAX_TOKENS = spec7.MAX_TOKENS
MONOLITHIC_MAX_TOKENS = spec7.MAX_TOKENS

STAGE_MAX_TOKENS = {
    STAGE_MONOLITHIC: MONOLITHIC_MAX_TOKENS,
    STAGE_PARSE: STAGE1_MAX_TOKENS,
    STAGE_DECIDE: STAGE2_MAX_TOKENS,
    STAGE_ANSWER: STAGE3_MAX_TOKENS,
}

STAGE1_SYSTEM_PROMPT = (
    "Вы - разборщик сообщений родителя в приложении ALVA. Вы только извлекаете факты из текста.\n"
    "Решать, что делать с сообщением, вам ЗАПРЕЩЕНО: не называйте маршрут, не давайте советов, "
    "не оценивайте опасность.\n"
    "\n"
    "Верните ровно шесть строк, по одному полю на строку, без JSON и без markdown:\n"
    "AGE_MONTHS=<целое 0..60, возраст ребёнка в месяцах, либо none>\n"
    "SYMPTOMS=<до пяти симптомов РЕБЁНКА через точку с запятой, словами из текста, либо none>\n"
    "METRICS=<измеренные цифры вида weight=8.1kg;height=68cm;sleep=11h;temp=38.3, либо none>\n"
    "DURATION=<сколько это длится, коротко, либо none>\n"
    "PARENT_STATE=<что взрослый пишет о себе: усталость, слёзы, злость, вина, а также любые слова "
    "о вреде себе или ребёнку и о нежелании жить; либо none>\n"
    "QUESTION_TYPE=<CARE|METRICS|PARENT|OTHER>\n"
    "\n"
    "Правила:\n"
    "- Возраст ребёнка - не показатель. В METRICS идут только измеренные цифры: вес, рост, "
    "температура, объём еды, часы сна.\n"
    "- SYMPTOMS - только про ребёнка. Всё про самочувствие взрослого идёт в PARENT_STATE, "
    "даже если это плохой сон или слёзы.\n"
    "- QUESTION_TYPE: CARE - про уход, сон, кормление, поведение, самочувствие ребёнка; "
    "METRICS - про цифры ребёнка или про норму, в том числе вопрос про норму без цифр; "
    "PARENT - взрослый пишет про себя и своё состояние; OTHER - сообщение не про ребёнка.\n"
    "- Чего в тексте нет - пишите none. Ничего не додумывайте.\n"
    "- Никакого текста до или после этих шести строк."
)

STAGE1_USER_TEMPLATE = "Сообщение родителя:\n{case_text}"

STAGE2_SYSTEM_PROMPT = (
    "Вы - решающий модуль триажа ALVA. На входе только факты, извлечённые из сообщения родителя. "
    "Исходного текста у вас нет, решайте по полям фактов.\n"
    "\n"
    "Шесть маршрутов: EMERGENCY, DOCTOR_SOON, PARENT_SUPPORT, DATA_INSIGHT, SELF_CARE, OFF_TOPIC.\n"
    "\n"
    "Правила читаются сверху вниз. Сработало правило - это и есть ответ, ниже не идите.\n"
    "\n"
    "1. В SYMPTOMS есть опасный признак у ребёнка -> EMERGENCY. Это правило перебивает "
    "QUESTION_TYPE и любые показатели. Опасные признаки: тяжёлое, частое или шумное дыхание, "
    "втяжения на вдохе, синюшность губ или кожи, судороги, потеря сознания, необычная вялость, "
    "невозможность разбудить, температура 38 и выше при AGE_MONTHS меньше 3, сыпь без побледнения "
    "при надавливании, обезвоживание с отказом от питья, травма головы с рвотой, проглоченный "
    "предмет или химия, сильное кровотечение.\n"
    "2. В PARENT_STATE есть слова о вреде себе или ребёнку либо о нежелании жить: не хочу жить, "
    "всем будет лучше без меня, боюсь что-то сделать с ребёнком, боюсь остаться с ним наедине "
    "-> EMERGENCY. Внутри этой темы при малейшем сомнении берите EMERGENCY.\n"
    "3. QUESTION_TYPE=OTHER -> OFF_TOPIC.\n"
    "4. QUESTION_TYPE=PARENT либо PARENT_STATE не none -> PARENT_SUPPORT. Усталость, слёзы, злость, "
    "вина, выгорание и бессонница взрослого сами по себе кризисом не являются: это PARENT_SUPPORT, "
    "а не EMERGENCY.\n"
    "5. QUESTION_TYPE=METRICS -> DATA_INSIGHT. Сюда же METRICS не none вместе с вопросом про норму. "
    "Возраст показателем не является и сам по себе DATA_INSIGHT не даёт.\n"
    "6. QUESTION_TYPE=CARE -> решайте по SYMPTOMS: признак, с которым нужен врач в ближайшие дни "
    "(температура дольше трёх дней, затяжной кашель, сыпь без других тревожных признаков, боль в ухе, "
    "остановка набора веса, медленное ухудшение) -> DOCTOR_SOON, иначе SELF_CARE.\n"
    "\n"
    "SYMPTOMS - всегда про ребёнка, PARENT_STATE - всегда про взрослого, не путайте их. "
    "Сомневаетесь между двумя маршрутами из-за симптома ребёнка - берите тот, что тяжелее: "
    "пропустить опасное хуже ложной тревоги.\n"
    "\n"
    "Ответьте ровно одной строкой и ничем больше:\n"
    "ROUTE=<один из шести>|CONFIDENCE=<число 0.0..1.0>|WHY=<до 100 символов>\n"
    "\n"
    "WHY уходит в текст для родителя, поэтому пишите его про ситуацию человека: без названий "
    "маршрутов, без имён полей и без ссылок на номер правила. "
    "Одна короткая фраза, не длиннее 100 символов."
)

STAGE2_USER_TEMPLATE = "Факты:\n{facts}\n\nВерните одну строку."

ROUTE_ANSWER_STRUCTURE = {
    spec7.ROUTE_EMERGENCY: (
        "первой фразой что делать прямо сейчас - вызвать скорую или ехать в приёмный покой, "
        "затем один-два признака из фактов, затем чего не делать; до четырёх предложений. "
        "Если тревога про самого взрослого, срочность та же, но текст про него: предложите "
        "позвонить в кризисную службу и не оставаться одному"
    ),
    spec7.ROUTE_DOCTOR_SOON: (
        "врач нужен в ближайшие дни, назовите признак, дайте что делать до приёма и при каких "
        "признаках звонить в скорую; до четырёх предложений"
    ),
    spec7.ROUTE_SELF_CARE: (
        "коротко ответьте по существу вопроса и назовите признаки, при которых нужен врач; "
        "до четырёх предложений"
    ),
    spec7.ROUTE_OFF_TOPIC: (
        "вежливо скажите, что помогаете только с вопросами о ребёнке до пяти лет; "
        "одно-два предложения"
    ),
    spec_v2.ROUTE_PARENT_SUPPORT: (
        "сначала признайте чувства взрослого своими словами, без советов лечиться, затем один "
        "посильный шаг и напоминание, что просить помощи нормально; до четырёх предложений"
    ),
    spec_v2.ROUTE_DATA_INSIGHT: (
        "сравните названные цифры с возрастным ориентиром и скажите, вписываются они или нет, "
        "затем что с этим делать; без диагнозов; до четырёх предложений"
    ),
}

STAGE3_SYSTEM_PROMPT = (
    "Вы - модуль ответа приложения ALVA. Маршрут уже выбран, менять его нельзя. "
    "Соберите короткий текст родителю по структуре маршрута.\n"
    "\n"
    + "\n".join("- %s: %s." % (route, ROUTE_ANSWER_STRUCTURE[route]) for route in ROUTES)
    + "\n"
    "\n"
    "Пишите простыми словами, на «вы», без диагнозов и без назначения лекарств. "
    "Только текст, без markdown и без заголовков."
)

STAGE3_USER_TEMPLATE = (
    "Маршрут: {route}\n"
    "Причина решения: {why}\n"
    "Факты:\n"
    "{facts}\n"
    "\n"
    "Напишите ответ родителю."
)

MONOLITHIC_SYSTEM_PROMPT = spec_v2.TRIAGE_SYSTEM_PROMPT
FALLBACK_ANSWER = spec7.FALLBACK_ANSWER

DEFAULT_MODEL = spec7.DEFAULT_MODEL
DEFAULT_BASE_URL = spec7.DEFAULT_BASE_URL
DEFAULT_KEY_ENV = spec7.DEFAULT_KEY_ENV

DEFAULT_WORKERS = 3
DEFAULT_REPEATS = 1
MIN_REPEATS = 1

RAW_DIR = os.path.join(TASK9_DIR, "raw")
RESULTS_DIR = os.path.join(TASK9_DIR, "results")
CASES_PATH = os.path.join(TASK7_DIR, "data", "cases.jsonl")
CASES_V2_PATH = os.path.join(TASK7_DIR, "data", "cases_v2.jsonl")

RUNS_FILE_SUFFIX = "_runs"
RUNS_FILE_EXTENSION = ".jsonl"
REPEAT_SUFFIX_PREFIX = "_r"
REPORT_NAME = "stages_report.json"
DEFAULT_REPORT_PATH = os.path.join(RESULTS_DIR, REPORT_NAME)

PERCENTILE_50 = 0.50
PERCENTILE_95 = 0.95

GROUPS = spec7.GROUPS

EXIT_OK = 0
EXIT_GATE_FAILED = 1
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2

NO_ROUTE = "-"
NOT_AVAILABLE = "-"
PROGRESS_PREVIEW_CHARS = 40

HYPOTHESES = {
    1: "цепочка точнее на пограничных случаях, ждём прирост на группе borderline",
    2: "цепочка дороже и медленнее, ждём рост стоимости примерно втрое",
    3: "цепочка устойчивее к шуму, ждём прирост на группе noisy",
    4: "цепочка чинит дефект с показателями через QUESTION_TYPE",
}
