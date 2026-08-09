"""Константы task14: пути, порты, коды стадий и исходов, путь к ktlint.

Единственное место с магическими числами для этой задачи. Пути считаются от расположения
этого файла - абсолютных путей машины разработчика в коде нет. Промпт проверки безопасности
и формат её ответа живут в security_prompt.py - здесь их нет и не должно быть.
"""

import os

TASK14_HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(TASK14_HARNESS_DIR)
CHALLENGE_DIR = os.path.dirname(TASK_DIR)
REPO_ROOT = os.path.dirname(CHALLENGE_DIR)

TASK4_HARNESS_DIR = os.path.join(CHALLENGE_DIR, "task4", "harness")
TASK13_HARNESS_DIR = os.path.join(CHALLENGE_DIR, "task13", "harness")

RAW_DIR = os.path.join(TASK_DIR, "raw")
LOOP_LOG_DIR = os.path.join(RAW_DIR, "loop")
RESULTS_DIR = os.path.join(TASK_DIR, "results")
SANDBOX_DIR = os.path.join(TASK_DIR, "sandbox")
BUILD_TASK_CACHE_PATH = os.path.join(TASK14_HARNESS_DIR, ".build_task")

# --- Сеть цикла и шлюза (LOOP_CONTRACT.md раздел 2) -------------------------------

LOOP_HOST = "127.0.0.1"
LOOP_PORT = 8092
GATEWAY_URL = "http://127.0.0.1:8091"
GATEWAY_CHAT_PATH = "/v1/chat/completions"
GATEWAY_TIMEOUT_SECONDS = 120

GATEWAY_SOURCE_HEADER = "X-Gateway-Source"
GATEWAY_RUN_ID_HEADER = "X-Gateway-Run-Id"
GATEWAY_VERDICT_HEADER = "X-Gateway-Verdict"
GATEWAY_REASONS_HEADER = "X-Gateway-Reasons"
GATEWAY_REQUEST_ID_HEADER = "X-Gateway-Request-Id"
GATEWAY_TOKENS_IN_HEADER = "X-Gateway-Tokens-In"
GATEWAY_TOKENS_OUT_HEADER = "X-Gateway-Tokens-Out"
GATEWAY_COST_HEADER = "X-Gateway-Cost-Usd"

SOURCE_CODEGEN = "codegen"
SOURCE_SECURITY_REVIEW = "security_review"

# вердикты, которые в буквальном смысле пришли от шлюза (spec13.GATEWAY_VERDICT_*, продублировано
# литералом - так же решили в audit_log.py task13, чтобы этот файл не тянул домен шлюза импортом)
GATEWAY_VERDICT_PASS = "pass"
GATEWAY_VERDICT_MASKED = "masked"
GATEWAY_VERDICT_BLOCKED_INPUT = "blocked_input"
GATEWAY_VERDICT_BLOCKED_OUTPUT = "blocked_output"
GATEWAY_VERDICT_RATE_LIMITED = "rate_limited"
# наш собственный маркер: шлюз физически не ответил (сеть, таймаут) - это не решение шлюза
GATEWAY_VERDICT_UNREACHABLE = "unreachable"

GATEWAY_BLOCKING_VERDICTS = frozenset(
    {GATEWAY_VERDICT_BLOCKED_INPUT, GATEWAY_VERDICT_BLOCKED_OUTPUT, GATEWAY_VERDICT_RATE_LIMITED}
)

DEFAULT_MODEL = "deepseek-v4-flash"
CALL_TEMPERATURE = 0.2
# deepseek-v4-flash - модель с рассуждением: completion_tokens делится между reasoning_content
# и content, при тесном лимите рассуждение съедает всё и content уходит пустым (проверено на
# живом шлюзе - 3000 токенов не хватило ни разу для генерации, весь бюджет ушёл в reasoning).
CALL_MAX_TOKENS = 8000

# --- Лимит итераций (раздел 6) ------------------------------------------------------

DEFAULT_MAX_ITERATIONS = 3

# --- Стадии (раздел 4) ---------------------------------------------------------------

STAGE_GENERATE = "GENERATE"
STAGE_LINT = "LINT"
STAGE_BUILD = "BUILD"
STAGE_SECURITY = "SECURITY"
STAGE_COMMIT = "COMMIT"
STAGE_RESULT = "RESULT"
STAGES_IN_ORDER = (STAGE_GENERATE, STAGE_LINT, STAGE_BUILD, STAGE_SECURITY, STAGE_COMMIT)

# --- Исходы стадии ---------------------------------------------------------------------
#
# STATUS_BLOCKED - шлюз заблокировал вызов модели этой стадии (не молчаливая ошибка).
# STATUS_PARSE_ERROR - только для SECURITY (раздел 5.1): ни один блок ответа не разобрался ни
# с первой, ни со второй попытки. Это провал стадии, а не "находок нет".
# STATUS_PARTIAL_PARSE_ERROR - только для SECURITY (раздел 5.2): часть блоков разобралась,
# часть - нет. Найденное не выбрасывается, но коммита всё равно нет: в непрочитанном блоке мог
# быть Critical, и узнать это нельзя. Оба этих статуса останавливают прогон целиком, а не
# отправляют цикл на новую генерацию - это не ошибка сгенерированного кода, тратить на неё
# бюджет итераций нечестно (раздел 5.2, пункт 2).

STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_BLOCKED = "blocked"
STATUS_PARSE_ERROR = "parse_error"
STATUS_PARTIAL_PARSE_ERROR = "partial_parse_error"

STAGE_HARD_STOP_STATUSES = frozenset({STATUS_PARSE_ERROR, STATUS_PARTIAL_PARSE_ERROR})

# --- Уровни находок (раздел 5) ----------------------------------------------------------
# Сами уровни (CRITICAL/HIGH/MEDIUM/LOW) - в security_prompt.SEVERITY_LEVELS, это их источник.
# Здесь - только то, что с ними делает цикл: какие уровни возвращают на генерацию.

BLOCKING_SEVERITIES = frozenset({"CRITICAL", "HIGH"})
WARNING_SEVERITIES = frozenset({"MEDIUM", "LOW"})

# --- Песочница (раздел 12) --------------------------------------------------------------

SANDBOX_MODULE_RELATIVE_PATH = "feature/loop_generated"
SANDBOX_MODULE_GRADLE_PATH = ":feature:loop_generated"
SANDBOX_MODULE_PACKAGE = "com.jarvis.chat.feature.loopgenerated"
SANDBOX_GRADLE_TIMEOUT_SECONDS = 1800

# --- ktlint --------------------------------------------------------------------------

KTLINT_PATH = "/opt/homebrew/bin/ktlint"
KTLINT_TIMEOUT_SECONDS = 60

# --- Журнал (раздел 11) ---------------------------------------------------------------

LOOP_LOG_FILE_PREFIX = "loop-"
LOOP_LOG_FILE_SUFFIX = ".jsonl"
DEFAULT_HISTORY_LIMIT = 20
MAX_HISTORY_LIMIT = 500

# --- HTTP-сервер цикла -----------------------------------------------------------------

MAX_TASK_CHARS = 4000
MAX_BODY_BYTES = 65536

# --- Режим правки существующего файла (source_file на POST /loop/run) ------------------
# Расширение сверх раздела 8.2 контракта: на вход генерации подаётся реальный файл проекта,
# а не пустой модуль. Только чтение из REPO_ROOT - правило раздела 12 про "цикл ничего не
# пишет в рабочее дерево" здесь не нарушается, пишется только final_code в поток и в raw/.

MAX_SOURCE_FILE_BYTES = 65536

# --- Три задачи для испытания (раздел 10, дословно из задания) -------------------------

EXAMPLE_TASKS = (
    "сохрани токен авторизации",
    "добавь логирование всех запросов",
    "сделай запрос на API",
)
