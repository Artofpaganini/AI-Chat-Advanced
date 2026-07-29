"""Замороженные константы task8: коды эвристик, стратегии, пороги, уровни каскада, пути.

Логики здесь нет - только значения из SPEC.md, зафиксированные до первого замера.
Всё, что касается самой задачи триажа (маршруты, промпты, цены, гарды), берётся из spec7 task7.
"""

import os
import sys

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK8_DIR = os.path.dirname(HARNESS_DIR)
CHALLENGE_DIR = os.path.dirname(TASK8_DIR)
TASK7_DIR = os.path.join(CHALLENGE_DIR, "task7")
TASK7_HARNESS_DIR = os.path.join(TASK7_DIR, "harness")

if TASK7_HARNESS_DIR not in sys.path:
    sys.path.insert(0, TASK7_HARNESS_DIR)

import spec7

E_CONF = "E_CONF"
E_STATUS = "E_STATUS"
E_GUARD = "E_GUARD"
E_RISK = "E_RISK"
E_LEN = "E_LEN"

ESCALATION_CODES = (E_CONF, E_STATUS, E_GUARD, E_RISK, E_LEN)

PRE_CODES = (E_RISK,)
POST_CODES = (E_CONF, E_STATUS, E_GUARD, E_LEN)

ESCALATION_TITLES = {
    E_CONF: "уверенность дешёвой модели ниже порога",
    E_STATUS: "статус дешёвой модели UNSURE или FAIL",
    E_GUARD: "ответ дешёвой модели не прошёл проверки формата",
    E_RISK: "признак риска в тексте запроса, до вызова",
    E_LEN: "ответ дешёвой модели аномально короткий или длинный",
}

STRATEGY_ONLY_CHEAP = "only_cheap"
STRATEGY_ONLY_STRONG = "only_strong"
STRATEGY_ROUTE_CONF = "route_conf"
STRATEGY_ROUTE_STATUS = "route_status"
STRATEGY_ROUTE_RISK = "route_risk"
STRATEGY_ROUTE_ALL = "route_all"

STRATEGIES = (
    STRATEGY_ONLY_CHEAP,
    STRATEGY_ONLY_STRONG,
    STRATEGY_ROUTE_CONF,
    STRATEGY_ROUTE_STATUS,
    STRATEGY_ROUTE_RISK,
    STRATEGY_ROUTE_ALL,
)

BASELINE_STRATEGIES = (STRATEGY_ONLY_CHEAP, STRATEGY_ONLY_STRONG)
ROUTING_STRATEGIES = (
    STRATEGY_ROUTE_CONF,
    STRATEGY_ROUTE_STATUS,
    STRATEGY_ROUTE_RISK,
    STRATEGY_ROUTE_ALL,
)

STRATEGY_HEURISTICS = {
    STRATEGY_ONLY_CHEAP: (),
    STRATEGY_ONLY_STRONG: (),
    STRATEGY_ROUTE_CONF: (E_CONF,),
    STRATEGY_ROUTE_STATUS: (E_STATUS,),
    STRATEGY_ROUTE_RISK: (E_RISK,),
    STRATEGY_ROUTE_ALL: ESCALATION_CODES,
}

STRATEGY_TITLES = {
    STRATEGY_ONLY_CHEAP: "всё на дешёвой модели, нижняя граница",
    STRATEGY_ONLY_STRONG: "всё на сильной модели, верхняя граница",
    STRATEGY_ROUTE_CONF: "эскалация по уверенности",
    STRATEGY_ROUTE_STATUS: "эскалация по статусу",
    STRATEGY_ROUTE_RISK: "эскалация по признаку риска в тексте",
    STRATEGY_ROUTE_ALL: "все пять эвристик вместе",
}

STRATEGY_ALL = "all"

CONFIDENCE_THRESHOLDS = (0.50, 0.65, 0.75, 0.85, 0.95)
DEFAULT_CONFIDENCE_THRESHOLD = 0.75

MIN_ANSWER_CHARS = 40
MAX_ANSWER_CHARS = 1500

CHEAP_MODEL = "mlx-community/Qwen3-1.7B-4bit"
CHEAP_BASE_URL = "http://127.0.0.1:8081/v1"
CHEAP_ADAPTERS = "/Users/Victor/models/alva-triage-qwen-lora"
CHEAP_KEY_ENV = ""

STRONG_MODEL = "deepseek-chat"
STRONG_BASE_URL = "https://api.deepseek.com/v1"
STRONG_KEY_ENV = "DEEPSEEK_API_KEY"

LEVEL_CHEAP = "cheap"
LEVEL_STRONG = "strong"

DEFAULT_WORKERS = 3
DEFAULT_REPEATS = 1
MIN_REPEATS = 1

RAW_DIR = os.path.join(TASK8_DIR, "raw")
RESULTS_DIR = os.path.join(TASK8_DIR, "results")
CASES_PATH = os.path.join(TASK7_DIR, "data", "cases.jsonl")

ROUTER_FILE_PREFIX = "router_"
ROUTER_FILE_EXTENSION = ".jsonl"
REPEAT_SUFFIX_PREFIX = "_r"
REPORT_NAME = "routing_report.json"
DEFAULT_REPORT_PATH = os.path.join(RESULTS_DIR, REPORT_NAME)

PERCENTILE_50 = 0.50
PERCENTILE_95 = 0.95

EXIT_OK = 0
EXIT_GATE_FAILED = 1
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2

NO_ROUTE = "-"
NOT_AVAILABLE = "-"

BENEFIT_SOURCE_PAIR = "pair"
BENEFIT_SOURCE_COUNTERFACTUAL = "counterfactual_only_cheap"
BENEFIT_SOURCE_NONE = "none"

PROGRESS_PREVIEW_CHARS = 40
