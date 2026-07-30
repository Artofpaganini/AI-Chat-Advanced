"""HTTP-обёртка пайплайна контроля уверенности из task7 в виде OpenAI-совместимого сервера.

Один эндпоинт POST /v1/chat/completions принимает обычное тело chat/completions, берёт последнее
сообщение с ролью user и прогоняет его через pipeline.run_pipeline. Системные сообщения от клиента
игнорируются: системный промпт триажа заморожен в spec7 и подменять его снаружи нельзя.

Ответ - стандартное тело chat.completion плюс поле triage верхнего уровня, где лежит вся кухня
контроля: маршрут, статус, голоса, вердикт критика, число вызовов, деньги и короткое объяснение
на русском. Текст в choices собирается детерминированно по маршруту и статусу, без лишнего вызова
модели: маршрут и признаки берутся из решения пайплайна.

Версия набора маршрутов выбирается флагом --spec-version. v1 - замороженные четыре маршрута из
spec7, ровно прежнее поведение. v2 - дефолт: те же четыре плюс PARENT_SUPPORT и DATA_INSIGHT,
плюс кризисный подтип экстренного маршрута.

Необязательное поле child_profile в теле запроса несёт цифры ребёнка. Они уходят в системный
промпт коротким блоком и в текст ответа, но в логи не попадают - там виден только факт, что
профиль передан, и имена заполненных полей.

Флаг --routing включает каскад из task8. При off - прежнее поведение, каждый запрос идёт в модель
из --model. При smart работает стратегия route_smart: сначала дешёвый локальный уровень, наверх
только при расхождении признака риска со спокойным ответом, при сломанном формате или низкой
уверенности. Правила эскалации импортированы из task8, а не написаны здесь заново.

Проверки, которые каскада не касаются: пустой ввод, чужой язык и кризисный гейт разбираются внутри
пайплайна до сети и стоят ноль вызовов на обоих уровнях. Кризисный ответ наверх не отправляется
никогда - иначе сильная модель получила бы право его отменить.

При stream: true тот же ответ уходит потоком SSE: текст режется на куски по несколько слов,
поле triage едет в последнем чанке с finish_reason stop, после него data: [DONE]. При stream: false
или без поля отдаётся обычный JSON.

Сервер многопоточный, ошибки внутри обработки не роняют процесс - клиент получает статус FAIL,
человеческий текст и поле error внутри triage. HTML стандартного http.server наружу не выходит
никогда: send_error переопределён на тот же JSON. Ключ модели не печатается и в ответ не попадает.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

TASK7_DIR = os.path.dirname(HARNESS_DIR)
CHALLENGE_DIR = os.path.dirname(TASK7_DIR)
TASK8_HARNESS_DIR = os.path.join(CHALLENGE_DIR, "task8", "harness")
if TASK8_HARNESS_DIR not in sys.path:
    sys.path.insert(0, TASK8_HARNESS_DIR)

import child_profile
import guards
import llm_client
import pipeline
import pipeline_v2
import spec7
import spec_v2

import cascade
import router
import router_spec

DEFAULT_PORT = 8090
DEFAULT_HOST = "0.0.0.0"
SERVED_MODEL = "triage-pipeline"
SERVED_MODEL_OWNER = "alva-triage"
EMERGENCY_PHONE = "103"
LOG_TEXT_CHARS = 40
MAX_BODY_BYTES = 262144
JSON_CONTENT_TYPE = "application/json; charset=utf-8"
SSE_CONTENT_TYPE = "text/event-stream; charset=utf-8"
CHAT_PATHS = ("/v1/chat/completions", "/chat/completions")
MODELS_PATHS = ("/v1/models", "/models")
HEALTH_PATHS = ("/health", "/")
STREAM_WORDS_PER_CHUNK = 3
STREAM_DELAY_SECONDS = 0.04
STREAM_DONE_MARKER = b"data: [DONE]\n\n"
WORD_PATTERN = re.compile(r"\S+\s*")

ROUTE_LABELS = dict(spec_v2.ROUTE_LABELS)

STATUS_LABELS = {
    spec7.STATUS_OK: "Ответ проверен",
    spec7.STATUS_UNSURE: "Требует внимания",
    spec7.STATUS_FAIL: "Не могу ответить",
}

UNKNOWN_ROUTE_LABEL = "Маршрут не определён"

UNSURE_NOTE = (
    "Я не уверен в этом ответе - проверьте его у врача, особенно если состояние ребёнка меняется."
)

EMERGENCY_LEAD = (
    "Похоже, ребёнку нужна помощь прямо сейчас. Вызовите скорую по номеру %s или везите ребёнка "
    "в ближайшее отделение неотложной помощи." % EMERGENCY_PHONE
)
EMERGENCY_FLAGS_LEAD = "Что настораживает в вашем сообщении: %s."
EMERGENCY_TAIL = (
    "Пока едет помощь, не давайте ребёнку лекарств по своему усмотрению - дозировку и диагноз "
    "определяет врач."
)

DOCTOR_SOON_LEAD = (
    "Прямо сейчас это не выглядит как угроза жизни, но ребёнка нужно показать врачу "
    "в ближайшие дни."
)
DOCTOR_SOON_FLAGS_LEAD = "Обратите внимание на: %s."
DOCTOR_SOON_TAIL = (
    "Если состояние ухудшится или появятся затруднённое дыхание, судороги, сильная вялость - "
    "не ждите записи и вызывайте скорую."
)

SELF_CARE_LEAD = (
    "Судя по описанию, это обычная родительская ситуация: срочно к врачу бежать не нужно."
)
SELF_CARE_TAIL = (
    "Если картина изменится или появятся тревожные признаки - покажите ребёнка врачу."
)

OFF_TOPIC_ANSWER = (
    "Я отвечаю только на вопросы о здоровье и уходе за ребёнком до пяти лет, поэтому с этим "
    "вопросом помочь не смогу."
)

EXPLAIN_INPUT_REJECTED = "сообщение пустое или без слов, к модели не обращались"
EXPLAIN_NO_VOTES = "модель ни разу не вернула разборчивый ответ"
EXPLAIN_CRITIC_AGREE = "критик согласен"
EXPLAIN_CRITIC_DISAGREE = "критик не согласен"
EXPLAIN_CRITIC_UNREADABLE = "критик не дал разборчивый вердикт"
EXPLAIN_CRITIC_SKIPPED = "критик не понадобился"
EXPLAIN_RISK_MISSED = "критик увидел упущенный опасный признак"
EXPLAIN_ESCALATED = "маршрут поднят по правилу безопасности"
EXPLAIN_REPAIRED = "формат ответа пришлось чинить"
EXPLAIN_FORMAT_FAILED = "проверки формата нашли ошибки"
EXPLAIN_CALL_ERROR = "было сбойное обращение к модели"
EXPLAIN_CRISIS_FALLBACK = "кризисный признак в сообщении родителя"

ROUTING_EXPLAIN_CHEAP = "ответила локальная модель, проверка не потребовалась"
ROUTING_EXPLAIN_STRONG_TAIL = "перепроверено облачной моделью"
ROUTING_EXPLAIN_FORCED = "запрос сразу ушёл в облачную модель"

ROUTING_REASON_EXPLAIN = {
    router_spec.E_CONFLICT: "локальная модель ответила спокойно при тревожном признаке",
    router_spec.E_GUARD: "локальная модель ответила в неверном формате",
    router_spec.E_CONF: "локальная модель не уверена в ответе",
    router_spec.E_STATUS: "локальная модель пометила ответ как неуверенный",
    router_spec.E_LEN: "ответ локальной модели неправдоподобной длины",
    router_spec.E_RISK: "в сообщении есть тревожный признак",
}

PROFILE_LOG_PRESENT = "профиль есть"
PROFILE_LOG_ABSENT = "профиля нет"

LOG_TRANSPORT_JSON = "json"
LOG_TRANSPORT_STREAM = "sse"

SPEC_VERSION_TITLES = {
    spec_v2.SPEC_VERSION_V1: "четыре маршрута, замороженный spec7",
    spec_v2.SPEC_VERSION_V2: "шесть маршрутов, поддержка родителя и данные ребёнка, кризисный гейт",
}

SERVICE_UNAVAILABLE_TEXT = (
    "Ассистент временно недоступен - запрос не удалось обработать. Попробуйте ещё раз чуть позже. "
    "Если вы тревожитесь за ребёнка - обратитесь к врачу, а при признаках угрозы жизни вызывайте "
    "скорую помощь."
)

SERVER_ERROR_TEXT = "внутренняя ошибка сервера триажа: %s"
BAD_BODY_TEXT = "тело запроса не разбирается как JSON: %s"
BODY_TOO_LARGE_TEXT = "тело запроса больше %d байт" % MAX_BODY_BYTES
UNKNOWN_PATH_TEXT = "неизвестный путь: %s"
EXPLAIN_UNPROCESSABLE = "запрос не удалось обработать"

_id_lock = threading.Lock()
_id_counter = 0


def next_response_id() -> str:
    global _id_counter
    with _id_lock:
        _id_counter += 1
        return "triage-%d" % _id_counter


def votes_word(count: int) -> str:
    tail = count % 100
    if 11 <= tail <= 14:
        return "голосов"
    last = count % 10
    if last == 1:
        return "голос"
    if 2 <= last <= 4:
        return "голоса"
    return "голосов"


def as_sentence(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    if value[-1] in ".!?":
        return value
    return value + "."


def agreed_votes(decision: pipeline.Decision) -> int:
    return int(round(decision.agreement * len(decision.votes)))


def explain_decision(decision: pipeline.Decision) -> str:
    if decision.input_rejected:
        return EXPLAIN_INPUT_REJECTED
    if getattr(decision, "language_rejected", False):
        return spec_v2.LANGUAGE_REJECT_EXPLAIN
    if getattr(decision, "crisis", False):
        return decision.crisis_source or EXPLAIN_CRISIS_FALLBACK
    parts: List[str] = []
    if not decision.votes:
        parts.append(EXPLAIN_NO_VOTES)
    else:
        agreed = agreed_votes(decision)
        parts.append(
            "совпало %d %s из %d" % (agreed, votes_word(agreed), len(decision.votes))
        )
    if decision.self_check_ran:
        if decision.self_check_verdict == spec7.VERDICT_AGREE:
            parts.append(EXPLAIN_CRITIC_AGREE)
        elif decision.self_check_verdict == spec7.VERDICT_DISAGREE:
            parts.append(EXPLAIN_CRITIC_DISAGREE)
        else:
            parts.append(EXPLAIN_CRITIC_UNREADABLE)
    else:
        parts.append(EXPLAIN_CRITIC_SKIPPED)
    if decision.risk_missed:
        parts.append(EXPLAIN_RISK_MISSED)
    if decision.escalated_by_safety:
        parts.append(EXPLAIN_ESCALATED)
    if decision.retried:
        parts.append(EXPLAIN_REPAIRED)
    elif guards.has_hard_violation(decision.violations):
        parts.append(EXPLAIN_FORMAT_FAILED)
    if decision.error:
        parts.append(EXPLAIN_CALL_ERROR)
    return ", ".join(parts)


def explain_routing(outcome: cascade.CascadeOutcome) -> str:
    if outcome.answered_by == cascade.LEVEL_NONE:
        return ""
    parts: List[str] = []
    if not outcome.escalated:
        parts.append(ROUTING_EXPLAIN_CHEAP)
    elif not outcome.escalation_reasons:
        parts.append(ROUTING_EXPLAIN_FORCED)
    else:
        reasons = [
            ROUTING_REASON_EXPLAIN.get(code, router_spec.ESCALATION_TITLES.get(code, code))
            for code in outcome.escalation_reasons
        ]
        parts.append("%s - %s" % (", ".join(reasons), ROUTING_EXPLAIN_STRONG_TAIL))
    if outcome.note:
        parts.append(outcome.note)
    return ", ".join(parts)


def apply_routing(
    block: Dict[str, Any], routing: str, outcome: Optional[cascade.CascadeOutcome]
) -> Dict[str, Any]:
    block["routing"] = routing
    if outcome is None:
        calls = int(block.get("calls") or 0)
        block["escalated"] = False
        block["escalation_reasons"] = []
        block["answered_by"] = (
            router_spec.LEVEL_STRONG if calls else cascade.LEVEL_NONE
        )
        block["calls_cheap"] = 0
        block["calls_strong"] = calls
        return block
    block["escalated"] = outcome.escalated
    block["escalation_reasons"] = list(outcome.escalation_reasons)
    block["answered_by"] = outcome.answered_by
    block["calls_cheap"] = outcome.calls_cheap
    block["calls_strong"] = outcome.calls_strong
    block["calls"] = outcome.calls_cheap + outcome.calls_strong
    block["cost_usd"] = outcome.cost_usd
    block["latency_ms"] = outcome.latency_ms
    note = explain_routing(outcome)
    if note:
        block["explain"] = "%s, %s" % (block["explain"], note)
    return block


def emergency_lines(decision: pipeline.Decision) -> List[str]:
    lines = [EMERGENCY_LEAD]
    if decision.red_flags:
        lines.append(EMERGENCY_FLAGS_LEAD % ", ".join(decision.red_flags))
    lines.append(EMERGENCY_TAIL)
    return lines


def doctor_soon_lines(decision: pipeline.Decision) -> List[str]:
    lines = [DOCTOR_SOON_LEAD]
    reason = as_sentence(decision.reason)
    if reason:
        lines.append(reason)
    if decision.red_flags:
        lines.append(DOCTOR_SOON_FLAGS_LEAD % ", ".join(decision.red_flags))
    lines.append(DOCTOR_SOON_TAIL)
    return lines


def self_care_lines(decision: pipeline.Decision) -> List[str]:
    lines = [SELF_CARE_LEAD]
    reason = as_sentence(decision.reason)
    if reason:
        lines.append(reason)
    lines.append(SELF_CARE_TAIL)
    return lines


def crisis_lines() -> List[str]:
    return list(spec_v2.CRISIS_LINES)


def support_ack_lines(themes: List[str]) -> List[str]:
    lines = [
        spec_v2.PARENT_SUPPORT_ACK[theme]
        for theme in themes
        if theme in spec_v2.PARENT_SUPPORT_ACK
    ]
    if not lines:
        return [spec_v2.PARENT_SUPPORT_ACK_DEFAULT]
    return lines[: spec_v2.MAX_SUPPORT_ACK_LINES]


def support_step_line(themes: List[str]) -> str:
    for theme in spec_v2.SUPPORT_STEP_PRIORITY:
        if theme in themes:
            return spec_v2.PARENT_SUPPORT_STEP[theme]
    return spec_v2.PARENT_SUPPORT_STEP_DEFAULT


def parent_support_lines(decision: pipeline.Decision) -> List[str]:
    themes = list(getattr(decision, "support_themes", []) or [])
    lines = [spec_v2.PARENT_SUPPORT_OPENING]
    lines.extend(support_ack_lines(themes))
    if spec_v2.THEME_ANGER_SHAME in themes:
        lines.append(spec_v2.PARENT_SUPPORT_GUILT_ANGER)
    else:
        lines.append(spec_v2.PARENT_SUPPORT_GUILT)
    if spec_v2.THEME_NIGHTS in themes:
        lines.append(spec_v2.PARENT_SUPPORT_FINITE_NIGHTS)
    else:
        lines.append(spec_v2.PARENT_SUPPORT_FINITE)
    lines.append(support_step_line(themes))
    if getattr(decision, "support_prolonged", False):
        lines.append(spec_v2.PARENT_SUPPORT_SPECIALIST)
        lines.append(spec_v2.PARENT_SUPPORT_HELPLINE)
    return lines


def missing_data_line(profile: child_profile.ChildProfile) -> str:
    if profile.age_months is not None:
        return spec_v2.DATA_INSIGHT_ASK_METRICS
    if profile.has_metrics:
        return spec_v2.DATA_INSIGHT_ASK_AGE
    return spec_v2.DATA_INSIGHT_ASK_ALL


def data_insight_lines(
    decision: pipeline.Decision, profile: child_profile.ChildProfile
) -> List[str]:
    compared, deviated, has_metrics = child_profile.compare_lines(profile)
    if not compared or not has_metrics:
        lines = self_care_lines(decision)
        lines.append(missing_data_line(profile))
        return lines
    lines = [spec_v2.DATA_INSIGHT_LEAD]
    lines.extend(compared)
    lines.append(spec_v2.DATA_INSIGHT_OUT_TAIL if deviated else spec_v2.DATA_INSIGHT_ALL_IN_TAIL)
    if spec_v2.FIELD_SLEEP_HOURS in profile.values:
        lines.append(spec_v2.DATA_INSIGHT_SOURCE_NOTE_SLEEP)
    else:
        lines.append(spec_v2.DATA_INSIGHT_SOURCE_NOTE)
    return lines


def answer_text(
    decision: pipeline.Decision, profile: Optional[child_profile.ChildProfile] = None
) -> str:
    if getattr(decision, "language_rejected", False):
        return spec_v2.LANGUAGE_REJECT_ANSWER
    if getattr(decision, "crisis", False):
        return "\n".join(crisis_lines())
    if decision.status == spec7.STATUS_FAIL:
        return spec7.FALLBACK_ANSWER
    if decision.route == spec7.ROUTE_EMERGENCY:
        lines = emergency_lines(decision)
    elif decision.route == spec7.ROUTE_DOCTOR_SOON:
        lines = doctor_soon_lines(decision)
    elif decision.route == spec_v2.ROUTE_PARENT_SUPPORT:
        lines = parent_support_lines(decision)
    elif decision.route == spec_v2.ROUTE_DATA_INSIGHT:
        lines = data_insight_lines(decision, profile or child_profile.ChildProfile())
    elif decision.route == spec7.ROUTE_SELF_CARE:
        lines = self_care_lines(decision)
    elif decision.route == spec7.ROUTE_OFF_TOPIC:
        lines = [OFF_TOPIC_ANSWER]
    else:
        return spec7.FALLBACK_ANSWER
    if decision.status == spec7.STATUS_UNSURE:
        lines.append(UNSURE_NOTE)
    return "\n".join(lines)


def triage_block(decision: pipeline.Decision) -> Dict[str, Any]:
    block: Dict[str, Any] = {
        "route": decision.route,
        "route_label": ROUTE_LABELS.get(decision.route, UNKNOWN_ROUTE_LABEL),
        "status": decision.status,
        "status_label": STATUS_LABELS.get(decision.status, decision.status),
        "confidence": decision.confidence_final,
        "red_flags": list(decision.red_flags),
        "votes": list(decision.votes),
        "agreement": decision.agreement,
        "self_check_ran": decision.self_check_ran,
        "self_check_verdict": decision.self_check_verdict,
        "escalated_by_safety": decision.escalated_by_safety,
        "violations": list(decision.violations),
        "calls": decision.calls,
        "latency_ms": decision.latency_ms,
        "cost_usd": decision.cost_usd,
        "model": decision.model,
        "explain": explain_decision(decision),
    }
    if getattr(decision, "spec_version", ""):
        block["spec_version"] = decision.spec_version
        block["language_rejected"] = bool(decision.language_rejected)
        block["crisis"] = bool(decision.crisis)
        block["child_profile_present"] = bool(decision.child_profile_present)
        block["child_profile_fields"] = list(decision.child_profile_fields)
        block["data_source"] = decision.data_source
        block["data_source_label"] = spec_v2.DATA_SOURCE_TITLES.get(decision.data_source, "")
        if decision.route == spec_v2.ROUTE_PARENT_SUPPORT:
            block["support_themes"] = list(decision.support_themes)
            block["support_prolonged"] = bool(decision.support_prolonged)
        if decision.crisis:
            block["emergency_subtype"] = decision.emergency_subtype
            block["crisis_markers"] = list(decision.crisis_markers)
            block["helpline"] = [spec_v2.HELPLINE_TRUST, spec_v2.HELPLINE_EMERGENCY]
    if decision.error:
        block["error"] = decision.error
    return block


def failed_block(error_text: str, model: str, routing: str = cascade.ROUTING_OFF) -> Dict[str, Any]:
    block: Dict[str, Any] = {
        "route": None,
        "route_label": UNKNOWN_ROUTE_LABEL,
        "status": spec7.STATUS_FAIL,
        "status_label": STATUS_LABELS[spec7.STATUS_FAIL],
        "confidence": 0.0,
        "red_flags": [],
        "votes": [],
        "agreement": 0.0,
        "self_check_ran": False,
        "self_check_verdict": None,
        "escalated_by_safety": False,
        "violations": [],
        "calls": 0,
        "latency_ms": 0,
        "cost_usd": 0.0,
        "model": model,
        "explain": EXPLAIN_UNPROCESSABLE,
        "error": error_text,
    }
    return apply_routing(block, routing, None)


def completion_response(content: str, triage: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": next_response_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": SERVED_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "triage": triage,
    }


def stream_chunk(
    response_id: str,
    created: int,
    delta: Dict[str, Any],
    finish_reason: Optional[str],
    triage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    chunk: Dict[str, Any] = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": SERVED_MODEL,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    if triage is not None:
        chunk["triage"] = triage
    return chunk


def text_chunks(text: str, words_per_chunk: int = STREAM_WORDS_PER_CHUNK) -> List[str]:
    words = WORD_PATTERN.findall(text or "")
    if not words:
        return []
    return [
        "".join(words[start : start + words_per_chunk])
        for start in range(0, len(words), words_per_chunk)
    ]


def stream_requested(payload: Dict[str, Any]) -> bool:
    value = payload.get("stream")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def models_response() -> Dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": SERVED_MODEL,
                "object": "model",
                "created": int(time.time()),
                "owned_by": SERVED_MODEL_OWNER,
            }
        ],
    }


def content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""
    chunks: List[str] = []
    for part in value:
        if isinstance(part, str):
            chunks.append(part)
            continue
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    return "".join(chunks)


def last_user_text(payload: Dict[str, Any]) -> str:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user":
            continue
        return content_text(message.get("content"))
    return ""


def normalized_path(raw_path: str) -> str:
    path = (raw_path or "").split("?")[0].split("#")[0]
    if len(path) > 1:
        path = path.rstrip("/")
    if not path:
        return "/"
    return path


def routing_mark(triage: Dict[str, Any]) -> str:
    routing = triage.get("routing") or cascade.ROUTING_OFF
    if routing == cascade.ROUTING_OFF:
        return routing
    reasons = ",".join(triage.get("escalation_reasons") or []) or "-"
    return "%s %s д%d/с%d %s" % (
        routing,
        triage.get("answered_by") or cascade.LEVEL_NONE,
        int(triage.get("calls_cheap") or 0),
        int(triage.get("calls_strong") or 0),
        reasons,
    )


def log_line(
    case_text: str, triage: Dict[str, Any], transport: str = LOG_TRANSPORT_JSON
) -> str:
    preview = (case_text or "").replace("\n", " ")[:LOG_TEXT_CHARS]
    profile_mark = (
        PROFILE_LOG_PRESENT if triage.get("child_profile_present") else PROFILE_LOG_ABSENT
    )
    return "%s | %s | %s | %s | conf %.2f | calls %d | %d ms | %s | %s | %s" % (
        time.strftime("%Y-%m-%d %H:%M:%S"),
        transport,
        triage.get("route") or "-",
        triage.get("status"),
        float(triage.get("confidence") or 0.0),
        int(triage.get("calls") or 0),
        int(triage.get("latency_ms") or 0),
        profile_mark,
        routing_mark(triage),
        preview,
    )


def parse_payload(body: Optional[bytes]) -> Tuple[Dict[str, Any], Optional[str]]:
    try:
        payload = json.loads((body or b"").decode("utf-8", "replace") or "{}")
    except ValueError as parse_error:
        return {}, BAD_BODY_TEXT % parse_error
    if not isinstance(payload, dict):
        return {}, BAD_BODY_TEXT % "тело не объект JSON"
    return payload, None


def write_log(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


class Settings:
    def __init__(
        self,
        client_cfg: llm_client.ClientConfig,
        critic_cfg: Optional[llm_client.ClientConfig],
        self_check_trigger: str,
        spec_version: str = spec_v2.SPEC_VERSION_V2,
        routing: str = cascade.ROUTING_OFF,
        cheap_cfg: Optional[llm_client.ClientConfig] = None,
        strong_cfg: Optional[llm_client.ClientConfig] = None,
        policy: Optional[router.RoutePolicy] = None,
    ) -> None:
        self.client_cfg = client_cfg
        self.critic_cfg = critic_cfg
        self.self_check_trigger = self_check_trigger
        self.spec_version = spec_version
        self.routing = routing
        self.cheap_cfg = cheap_cfg
        self.strong_cfg = strong_cfg
        self.policy = policy

    @property
    def cascade_on(self) -> bool:
        return self.routing != cascade.ROUTING_OFF

    def level_config(self, level: str) -> llm_client.ClientConfig:
        if not self.cascade_on:
            return self.client_cfg
        if level == router_spec.LEVEL_STRONG:
            return self.strong_cfg
        return self.cheap_cfg

    def level_critic(self, level: str) -> Optional[llm_client.ClientConfig]:
        if not self.cascade_on or level == router_spec.LEVEL_STRONG:
            return self.critic_cfg
        return None

    def answer_model(self) -> str:
        if self.cascade_on:
            return self.strong_cfg.model
        return self.client_cfg.model


class TriageServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: Tuple[str, int], handler_class, settings: Settings) -> None:
        self.settings = settings
        super().__init__(address, handler_class)


class TriageHandler(BaseHTTPRequestHandler):
    server_version = "TriageServer/1.0"
    protocol_version = "HTTP/1.1"
    response_started = False

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_error(self, code: Any, message: Any = None, explain: Any = None) -> None:
        self.close_connection = True
        if self.response_started:
            return
        self.response_started = True
        detail = explain or message or ("HTTP %s" % code)
        try:
            triage = failed_block(
                str(detail), self.configured_model(), self.configured_routing()
            )
            self.send_json(200, completion_response(SERVICE_UNAVAILABLE_TEXT, triage))
            write_log(log_line("", triage))
        except Exception:
            return

    def configured_model(self) -> str:
        try:
            return self.server.settings.answer_model()
        except AttributeError:
            return SERVED_MODEL

    def configured_routing(self) -> str:
        try:
            return self.server.settings.routing
        except AttributeError:
            return cascade.ROUTING_OFF

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")

    def send_json(self, status: int, payload: Dict[str, Any]) -> None:
        self.response_started = True
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_failure(self, error_text: str) -> None:
        triage = failed_block(error_text, self.configured_model(), self.configured_routing())
        self.send_json(200, completion_response(SERVICE_UNAVAILABLE_TEXT, triage))
        write_log(log_line("", triage))

    def start_stream(self) -> None:
        self.response_started = True
        self.send_response(200)
        self.send_header("Content-Type", SSE_CONTENT_TYPE)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("X-Accel-Buffering", "no")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.flush()

    def write_stream_bytes(self, data: bytes) -> None:
        self.wfile.write(b"%x\r\n" % len(data))
        self.wfile.write(data)
        self.wfile.write(b"\r\n")
        self.wfile.flush()

    def send_event(self, chunk: Dict[str, Any]) -> None:
        payload = "data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n"
        self.write_stream_bytes(payload.encode("utf-8"))

    def end_stream(self) -> None:
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def read_body(self) -> Tuple[Optional[bytes], Optional[str]]:
        raw_length = self.headers.get("Content-Length") or "0"
        try:
            length = int(raw_length)
        except ValueError:
            return None, "заголовок Content-Length не число"
        if length < 0:
            return None, "заголовок Content-Length отрицательный"
        if length > MAX_BODY_BYTES:
            return None, BODY_TOO_LARGE_TEXT
        if length == 0:
            return b"", None
        return self.rfile.read(length), None

    def do_OPTIONS(self) -> None:
        self.response_started = True
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        self.response_started = False
        path = normalized_path(self.path)
        if path in MODELS_PATHS:
            self.send_json(200, models_response())
            return
        if path in HEALTH_PATHS:
            self.send_json(200, {"status": "ok", "model": SERVED_MODEL})
            return
        self.send_json(404, {"error": {"message": UNKNOWN_PATH_TEXT % path}})

    def do_POST(self) -> None:
        self.response_started = False
        path = normalized_path(self.path)
        body, read_error = self.read_body()
        if read_error is not None:
            self.close_connection = True
            self.send_failure(read_error)
            return
        if path not in CHAT_PATHS:
            self.send_failure(UNKNOWN_PATH_TEXT % path)
            return
        try:
            self.handle_completion(body)
        except Exception as unexpected_error:
            self.close_connection = True
            if self.response_started:
                return
            try:
                self.send_failure(SERVER_ERROR_TEXT % unexpected_error)
            except Exception:
                return

    def handle_completion(self, body: Optional[bytes]) -> None:
        payload, parse_error = parse_payload(body)
        if parse_error is not None:
            self.send_failure(parse_error)
            return
        if stream_requested(payload):
            self.stream_completion(payload)
            return
        case_text, triage, content = self.run_decision(payload)
        self.send_json(200, completion_response(content, triage))
        write_log(log_line(case_text, triage, LOG_TRANSPORT_JSON))

    def stream_completion(self, payload: Dict[str, Any]) -> None:
        response_id = next_response_id()
        created = int(time.time())
        self.start_stream()
        case_text = ""
        try:
            case_text, triage, content = self.run_decision(payload)
        except Exception as unexpected_error:
            triage = failed_block(
                SERVER_ERROR_TEXT % unexpected_error,
                self.configured_model(),
                self.configured_routing(),
            )
            content = SERVICE_UNAVAILABLE_TEXT
        try:
            self.send_event(stream_chunk(response_id, created, {"role": "assistant"}, None))
            for piece in text_chunks(content):
                self.send_event(stream_chunk(response_id, created, {"content": piece}, None))
                time.sleep(STREAM_DELAY_SECONDS)
            self.send_event(stream_chunk(response_id, created, {}, "stop", triage))
            self.write_stream_bytes(STREAM_DONE_MARKER)
            self.end_stream()
        except OSError:
            self.close_connection = True
            return
        write_log(log_line(case_text, triage, LOG_TRANSPORT_STREAM))

    def run_level_v1(self, case_text: str, level: str) -> pipeline.Decision:
        settings = self.server.settings
        return pipeline.run_pipeline(
            case_text,
            settings.level_config(level),
            "",
            settings.self_check_trigger,
            settings.level_critic(level),
        )

    def run_level_v2(
        self,
        case_text: str,
        level: str,
        profile_block: str,
        profile_present: bool,
        profile_names: List[str],
        data_source: str,
    ) -> pipeline.Decision:
        settings = self.server.settings
        return pipeline_v2.run_pipeline(
            case_text,
            settings.level_config(level),
            "",
            settings.self_check_trigger,
            settings.level_critic(level),
            profile_block,
            profile_present,
            profile_names,
            data_source,
        )

    def decide(
        self, case_text: str, run_level: cascade.RunLevel
    ) -> Tuple[pipeline.Decision, Optional[cascade.CascadeOutcome]]:
        settings = self.server.settings
        if not settings.cascade_on:
            return run_level(router_spec.LEVEL_STRONG), None
        outcome = cascade.run_cascade(case_text, settings.policy, run_level)
        return outcome.decision, outcome

    def run_decision(self, payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any], str]:
        settings = self.server.settings
        case_text = last_user_text(payload)
        if settings.spec_version == spec_v2.SPEC_VERSION_V1:

            def run_level_v1(level: str) -> pipeline.Decision:
                return self.run_level_v1(case_text, level)

            decision, outcome = self.decide(case_text, run_level_v1)
            triage = apply_routing(triage_block(decision), settings.routing, outcome)
            return case_text, triage, answer_text(decision)

        stored = child_profile.sanitize(payload.get(spec_v2.CHILD_PROFILE_KEY))
        from_message = child_profile.parse_message(case_text)
        profile, data_source = child_profile.merge(from_message, stored)
        profile_block = child_profile.prompt_block(profile)

        def run_level_v2(level: str) -> pipeline.Decision:
            return self.run_level_v2(
                case_text, level, profile_block, stored.present, profile.names, data_source
            )

        decision, outcome = self.decide(case_text, run_level_v2)
        triage = apply_routing(triage_block(decision), settings.routing, outcome)
        if stored.issues:
            triage["child_profile_issues"] = list(stored.issues)
        return case_text, triage, answer_text(decision, profile)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OpenAI-совместимый сервер триажа поверх пайплайна task7"
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--model", default=spec7.DEFAULT_MODEL)
    parser.add_argument("--base-url", dest="base_url", default=spec7.DEFAULT_BASE_URL)
    parser.add_argument("--key-env", dest="key_env", default=spec7.DEFAULT_KEY_ENV)
    parser.add_argument("--adapters", dest="adapters", default="")
    parser.add_argument(
        "--self-check-trigger",
        dest="self_check_trigger",
        choices=list(spec7.SELF_CHECK_TRIGGERS),
        default=spec7.SELF_CHECK_TRIGGER_RISK,
    )
    parser.add_argument("--critic-model", dest="critic_model", default="")
    parser.add_argument("--critic-base-url", dest="critic_base_url", default="")
    parser.add_argument("--critic-key-env", dest="critic_key_env", default="")
    parser.add_argument("--critic-adapters", dest="critic_adapters", default="")
    parser.add_argument("--timeout", type=int, default=spec7.REQUEST_TIMEOUT_SECONDS)
    parser.add_argument("--thinking", dest="thinking", action="store_true")
    parser.add_argument(
        "--spec-version",
        dest="spec_version",
        choices=list(spec_v2.SPEC_VERSIONS),
        default=spec_v2.SPEC_VERSION_V2,
    )
    parser.add_argument(
        "--routing",
        dest="routing",
        choices=list(cascade.ROUTING_MODES),
        default=cascade.ROUTING_OFF,
        help="off - каждый запрос в модель из --model, smart - каскад task8",
    )
    parser.add_argument("--cheap-model", dest="cheap_model", default=router_spec.CHEAP_MODEL)
    parser.add_argument(
        "--cheap-base-url", dest="cheap_base_url", default=router_spec.CHEAP_BASE_URL
    )
    parser.add_argument(
        "--cheap-adapters", dest="cheap_adapters", default=router_spec.CHEAP_ADAPTERS
    )
    parser.add_argument("--strong-model", dest="strong_model", default=router_spec.STRONG_MODEL)
    parser.add_argument(
        "--strong-base-url", dest="strong_base_url", default=router_spec.STRONG_BASE_URL
    )
    parser.add_argument(
        "--strong-key-env", dest="strong_key_env", default=router_spec.STRONG_KEY_ENV
    )
    return parser


def build_extra_payload(thinking_off: bool, adapters: str) -> Optional[Dict[str, Any]]:
    payload: Dict[str, Any] = {}
    if thinking_off:
        payload.update(spec7.NO_THINKING_PAYLOAD)
    if adapters:
        payload[spec7.ADAPTERS_PAYLOAD_KEY] = adapters
    if not payload:
        return None
    return payload


def critic_endpoint(args: argparse.Namespace) -> Dict[str, str]:
    model = args.critic_model or args.model
    base_url = args.critic_base_url or args.base_url
    key_env = args.critic_key_env or args.key_env
    same_target = model == args.model and base_url == args.base_url and key_env == args.key_env
    adapters = args.critic_adapters
    if not adapters and same_target:
        adapters = args.adapters
    return {"model": model, "base_url": base_url, "key_env": key_env, "adapters": adapters}


def critic_is_separate(args: argparse.Namespace) -> bool:
    endpoint = critic_endpoint(args)
    return (
        endpoint["model"] != args.model
        or endpoint["base_url"] != args.base_url
        or endpoint["key_env"] != args.key_env
        or endpoint["adapters"] != args.adapters
    )


def resolve_key(base_url: str, key_env: str) -> Tuple[str, Optional[str]]:
    location = llm_client.inference_location(base_url)
    if location == spec7.LOCATION_LOCAL:
        return "", None
    api_key = llm_client.read_api_key(key_env)
    if not api_key:
        return "", (
            "Ключ %s не найден ни в окружении, ни в %s. "
            "Экспортируйте переменную окружения и повторите: export %s=<ваш ключ>"
            % (key_env, spec7.LOCAL_PROPERTIES_PATH, key_env)
        )
    return api_key, None


def build_client_config(
    model: str, base_url: str, key_env: str, adapters: str, timeout: int, thinking: bool
) -> Tuple[Optional[llm_client.ClientConfig], Optional[str]]:
    api_key, key_error = resolve_key(base_url, key_env)
    if key_error is not None:
        return None, key_error
    location = llm_client.inference_location(base_url)
    thinking_off = location == spec7.LOCATION_LOCAL and not thinking
    config = llm_client.ClientConfig(
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        extra_payload=build_extra_payload(thinking_off, adapters),
    )
    return config, None


def critic_flags_given(args: argparse.Namespace) -> bool:
    return bool(
        args.critic_model or args.critic_base_url or args.critic_key_env or args.critic_adapters
    )


def build_cascade_settings(args: argparse.Namespace) -> Tuple[Optional[Settings], Optional[str]]:
    cheap_cfg = router.cheap_config(
        args.cheap_model, args.cheap_base_url, args.cheap_adapters, args.timeout
    )
    _, key_error = resolve_key(args.strong_base_url, args.strong_key_env)
    if key_error is not None:
        return None, key_error
    strong_cfg = router.strong_config(
        args.strong_model, args.strong_base_url, args.strong_key_env, args.timeout
    )
    critic_cfg: Optional[llm_client.ClientConfig] = None
    if critic_flags_given(args):
        critic_cfg, critic_error = build_client_config(
            args.critic_model or args.strong_model,
            args.critic_base_url or args.strong_base_url,
            args.critic_key_env or args.strong_key_env,
            args.critic_adapters,
            args.timeout,
            args.thinking,
        )
        if critic_error is not None:
            return None, critic_error
    policy = cascade.policy_for(
        args.routing,
        router_spec.DEFAULT_CONFIDENCE_THRESHOLD,
        router_spec.CONFLICT_SEVERITY_CEILING,
    )
    settings = Settings(
        strong_cfg,
        critic_cfg,
        args.self_check_trigger,
        args.spec_version,
        args.routing,
        cheap_cfg,
        strong_cfg,
        policy,
    )
    return settings, None


def build_settings(args: argparse.Namespace) -> Tuple[Optional[Settings], Optional[str]]:
    if args.routing != cascade.ROUTING_OFF:
        return build_cascade_settings(args)
    client_cfg, client_error = build_client_config(
        args.model, args.base_url, args.key_env, args.adapters, args.timeout, args.thinking
    )
    if client_error is not None:
        return None, client_error
    critic_cfg: Optional[llm_client.ClientConfig] = None
    if critic_is_separate(args):
        endpoint = critic_endpoint(args)
        critic_cfg, critic_error = build_client_config(
            endpoint["model"],
            endpoint["base_url"],
            endpoint["key_env"],
            endpoint["adapters"],
            args.timeout,
            args.thinking,
        )
        if critic_error is not None:
            return None, critic_error
    return Settings(client_cfg, critic_cfg, args.self_check_trigger, args.spec_version), None


def key_env_of(args: argparse.Namespace) -> str:
    if args.routing != cascade.ROUTING_OFF:
        return args.strong_key_env
    return args.key_env


def describe_routing(settings: Settings) -> List[str]:
    if not settings.cascade_on:
        return [
            "Роутинг: %s - %s"
            % (cascade.ROUTING_OFF, cascade.ROUTING_TITLES[cascade.ROUTING_OFF])
        ]
    policy = settings.policy
    lines = [
        "Роутинг: %s - %s" % (settings.routing, cascade.ROUTING_TITLES[settings.routing]),
        "Стратегия каскада: %s - %s"
        % (policy.strategy, router_spec.STRATEGY_TITLES[policy.strategy]),
        "Правила эскалации: %s" % ", ".join(policy.heuristics),
        "Дешёвый уровень: %s (%s)"
        % (settings.cheap_cfg.model, settings.cheap_cfg.base_url),
        "Сильный уровень: %s (%s)"
        % (settings.strong_cfg.model, settings.strong_cfg.base_url),
        "Порог уверенности для E_CONF: %.2f" % policy.confidence_threshold,
    ]
    if settings.cheap_cfg.adapter:
        lines.append("Адаптер дешёвого уровня: %s" % settings.cheap_cfg.adapter)
    return lines


def describe_startup(args: argparse.Namespace, settings: Settings) -> List[str]:
    critic = settings.critic_cfg or settings.client_cfg
    lines = [
        "Сервер триажа слушает http://%s:%d%s" % (args.host, args.port, CHAT_PATHS[0]),
    ]
    if not settings.cascade_on:
        lines.append(
            "Модель основного прохода: %s (%s)"
            % (settings.client_cfg.model, settings.client_cfg.base_url)
        )
    if settings.cascade_on and settings.critic_cfg is None:
        lines.append("Критик: каждый уровень проверяет сам себя")
    else:
        lines.append("Модель критика: %s (%s)" % (critic.model, critic.base_url))
    lines += [
        "Триггер критика: %s - %s"
        % (
            settings.self_check_trigger,
            spec7.SELF_CHECK_TRIGGER_TITLES[settings.self_check_trigger],
        ),
        "Ключ: %s" % llm_client.describe_key_source(key_env_of(args)),
        "Имя модели для клиента: %s" % SERVED_MODEL,
        "Версия набора маршрутов: %s - %s"
        % (settings.spec_version, SPEC_VERSION_TITLES[settings.spec_version]),
    ]
    lines.extend(describe_routing(settings))
    if not settings.cascade_on and settings.client_cfg.adapter:
        lines.append("Адаптер основного прохода: %s" % settings.client_cfg.adapter)
    if critic.adapter:
        lines.append("Адаптер критика: %s" % critic.adapter)
    return lines


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    settings, error = build_settings(args)
    if settings is None:
        sys.stderr.write((error or "не удалось собрать конфигурацию") + "\n")
        return 2
    server = TriageServer((args.host, args.port), TriageHandler, settings)
    for line in describe_startup(args, settings):
        write_log(line)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        write_log("Остановка по Ctrl+C")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
