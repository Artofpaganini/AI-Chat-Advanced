"""Константы task10: пути, метки, гиперпараметры обучения, сетка порогов, условия гейта.

Единственное место, где живут магические числа. Всё остальное их импортирует.
Пути считаются от расположения этого файла, абсолютных путей машины в коде нет.
"""

import os

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK10_DIR = os.path.dirname(HARNESS_DIR)
CHALLENGE_DIR = os.path.dirname(TASK10_DIR)
TASK7_DIR = os.path.join(CHALLENGE_DIR, "task7")
TASK7_HARNESS_DIR = os.path.join(TASK7_DIR, "harness")
TASK7_DATA_DIR = os.path.join(TASK7_DIR, "data")

RAW_DIR = os.path.join(TASK10_DIR, "raw")
RESULTS_DIR = os.path.join(TASK10_DIR, "results")

TRAIN_PATH = os.path.join(TASK7_DATA_DIR, "train_triage_full.jsonl")
TRAIN_SMALL_PATH = os.path.join(TASK7_DATA_DIR, "train_triage.jsonl")
CASES_PATH = os.path.join(TASK7_DATA_DIR, "cases.jsonl")

MODEL_PATH = os.path.join(RESULTS_DIR, "micro_model.json")
PARITY_PATH = os.path.join(RESULTS_DIR, "parity_python.json")
REPORT_PATH = os.path.join(RESULTS_DIR, "pipeline_report.json")
TRAIN_REPORT_PATH = os.path.join(RESULTS_DIR, "train_report.json")

TRAIN_RELATIVE_NAME = "task7/data/train_triage_full.jsonl"

LABEL_EMERGENCY = "EMERGENCY"
LABEL_DOCTOR_SOON = "DOCTOR_SOON"
LABEL_SELF_CARE = "SELF_CARE"
LABEL_OFF_TOPIC = "OFF_TOPIC"
LABELS = (LABEL_EMERGENCY, LABEL_DOCTOR_SOON, LABEL_SELF_CARE, LABEL_OFF_TOPIC)

STATUS_OK = "OK"
STATUS_UNSURE = "UNSURE"

SEVERITY = {
    LABEL_EMERGENCY: 3,
    LABEL_DOCTOR_SOON: 2,
    LABEL_SELF_CARE: 1,
    LABEL_OFF_TOPIC: 0,
}

POSTHOC_SEVERITY_MAX = "severity_max"
POSTHOC_NO_FORCE_ESCALATE = "no_force_escalate"
POSTHOC_VARIANTS = (POSTHOC_SEVERITY_MAX, POSTHOC_NO_FORCE_ESCALATE)

POSTHOC_TITLES = {
    POSTHOC_SEVERITY_MAX: "при эскалации итог - более тяжёлый из двух маршрутов",
    POSTHOC_NO_FORCE_ESCALATE: "без принудительной эскалации EMERGENCY, только по порогу",
}

FORMAT_VERSION = 1
SEED = 1337

WORD_NGRAM_MIN = 1
WORD_NGRAM_MAX = 2
CHAR_NGRAM_MIN = 3
CHAR_NGRAM_MAX = 5

WORD_PREFIX = "w:"
CHAR_PREFIX = "c:"

MIN_DF_WORD = 2
MIN_DF_CHAR = 4
MAX_VOCAB_PRETRAIN = 30000
MAX_VOCAB_FINAL = 6000
VOCAB_SHRINK_FACTOR = 0.85
MAX_BUDGET_ATTEMPTS = 6
MAX_MODEL_BYTES = 500 * 1024

WEIGHT_DECIMALS = 5
IDF_DECIMALS = 5
WEIGHT_EPSILON = 1e-6

LEARNING_RATE = 4.0
MOMENTUM = 0.9
EPOCHS = 200
L2_LAMBDA = 1e-4

VALIDATION_SHARE = 0.2
PROB_GRID = (0.50, 0.60, 0.70, 0.80, 0.90)
MARGIN_GRID = (0.00, 0.10, 0.20, 0.30, 0.40)
MIN_PRECISION_ON_OK = 0.95

ALWAYS_ESCALATE_LABELS = (LABEL_EMERGENCY,)

JACCARD_NEAR_DUPLICATE = 0.9

MODE_ONLY_LLM = "only_llm"
MODE_ONLY_MICRO = "only_micro"
MODE_CASCADE = "cascade"
MODE_CASCADE_MAX = "cascade_max"
MODES = (MODE_ONLY_LLM, MODE_ONLY_MICRO, MODE_CASCADE, MODE_CASCADE_MAX)
CASCADE_MODES = (MODE_CASCADE, MODE_CASCADE_MAX)
MODE_ALL = "all"

MODE_TITLES = {
    MODE_ONLY_LLM: "всё в большую модель",
    MODE_ONLY_MICRO: "только micro-model",
    MODE_CASCADE: "каскад, вердикт LLM побеждает (первая редакция контракта)",
    MODE_CASCADE_MAX: "каскад, слияние только вверх (раздел 5.1 контракта)",
}

MODE_USES_LLM = {
    MODE_ONLY_LLM: True,
    MODE_ONLY_MICRO: False,
    MODE_CASCADE: True,
    MODE_CASCADE_MAX: True,
}

MERGE_LLM_WINS = "llm_wins"
MERGE_SEVERITY_MAX = "severity_max"

MODE_MERGE_RULE = {
    MODE_CASCADE: MERGE_LLM_WINS,
    MODE_CASCADE_MAX: MERGE_SEVERITY_MAX,
}

DEFAULT_REPEATS = 3
DEFAULT_WORKERS = 3
MIN_REPEATS = 1

LLM_MODEL = "deepseek-chat"
LLM_BASE_URL = "https://api.deepseek.com/v1"
LLM_KEY_ENV = "DEEPSEEK_API_KEY"

RAW_FILE_PREFIX = "pipeline_"
RAW_FILE_EXTENSION = ".jsonl"
REPEAT_SUFFIX_PREFIX = "_r"

GROUP_CLEAN = "clean"
GROUP_BORDERLINE = "borderline"
GROUP_NOISY = "noisy"
GROUPS = (GROUP_CLEAN, GROUP_BORDERLINE, GROUP_NOISY)

EXPECTED_CASES = 50
PERCENTILE_P50 = 50
PERCENTILE_P95 = 95

GATE_EMERGENCY = "missed_emergency_not_worse_than_only_llm"
GATE_ACCURACY = "accuracy_not_below_only_micro"
GATE_CALLS = "llm_calls_below_only_llm"
GATE_PARITY = "parity_file_complete"
GATE_SIZE = "model_within_500kb"
GATE_CODES = (GATE_EMERGENCY, GATE_ACCURACY, GATE_CALLS, GATE_PARITY, GATE_SIZE)

GATE_TITLES = {
    GATE_EMERGENCY: "пропущенных экстренных у каскада не больше, чем у only_llm",
    GATE_ACCURACY: "точность каскада не ниже, чем у only_micro",
    GATE_CALLS: "вызовов LLM у каскада меньше, чем у only_llm",
    GATE_PARITY: "паритет-файл содержит все 50 кейсов",
    GATE_SIZE: "файл весов не больше 500 КБ",
}
