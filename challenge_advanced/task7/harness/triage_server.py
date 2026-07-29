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

import child_profile
import guards
import llm_client
import pipeline
import pipeline_v2
import spec7
import spec_v2

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


def data_insight_lines(
    decision: pipeline.Decision, profile: child_profile.ChildProfile
) -> List[str]:
    if not profile.present:
        return [spec_v2.DATA_INSIGHT_NO_PROFILE]
    compared, deviated, has_metrics = child_profile.compare_lines(profile)
    if not compared:
        return [spec_v2.DATA_INSIGHT_NO_AGE]
    if not has_metrics:
        return compared + [spec_v2.DATA_INSIGHT_NO_METRICS]
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


def failed_block(error_text: str, model: str) -> Dict[str, Any]:
    return {
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


def log_line(
    case_text: str, triage: Dict[str, Any], transport: str = LOG_TRANSPORT_JSON
) -> str:
    preview = (case_text or "").replace("\n", " ")[:LOG_TEXT_CHARS]
    profile_mark = (
        PROFILE_LOG_PRESENT if triage.get("child_profile_present") else PROFILE_LOG_ABSENT
    )
    return "%s | %s | %s | %s | conf %.2f | calls %d | %d ms | %s | %s" % (
        time.strftime("%Y-%m-%d %H:%M:%S"),
        transport,
        triage.get("route") or "-",
        triage.get("status"),
        float(triage.get("confidence") or 0.0),
        int(triage.get("calls") or 0),
        int(triage.get("latency_ms") or 0),
        profile_mark,
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
    ) -> None:
        self.client_cfg = client_cfg
        self.critic_cfg = critic_cfg
        self.self_check_trigger = self_check_trigger
        self.spec_version = spec_version


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
            triage = failed_block(str(detail), self.configured_model())
            self.send_json(200, completion_response(SERVICE_UNAVAILABLE_TEXT, triage))
            write_log(log_line("", triage))
        except Exception:
            return

    def configured_model(self) -> str:
        try:
            return self.server.settings.client_cfg.model
        except AttributeError:
            return SERVED_MODEL

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
        triage = failed_block(error_text, self.configured_model())
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
            triage = failed_block(SERVER_ERROR_TEXT % unexpected_error, self.configured_model())
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

    def run_decision(self, payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any], str]:
        settings = self.server.settings
        case_text = last_user_text(payload)
        if settings.spec_version == spec_v2.SPEC_VERSION_V1:
            decision = pipeline.run_pipeline(
                case_text,
                settings.client_cfg,
                "",
                settings.self_check_trigger,
                settings.critic_cfg,
            )
            return case_text, triage_block(decision), answer_text(decision)

        stored = child_profile.sanitize(payload.get(spec_v2.CHILD_PROFILE_KEY))
        from_message = child_profile.parse_message(case_text)
        profile, data_source = child_profile.merge(from_message, stored)
        decision = pipeline_v2.run_pipeline(
            case_text,
            settings.client_cfg,
            "",
            settings.self_check_trigger,
            settings.critic_cfg,
            child_profile.prompt_block(profile),
            stored.present,
            profile.names,
            data_source,
        )
        triage = triage_block(decision)
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


def build_settings(args: argparse.Namespace) -> Tuple[Optional[Settings], Optional[str]]:
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


def describe_startup(args: argparse.Namespace, settings: Settings) -> List[str]:
    critic = settings.critic_cfg or settings.client_cfg
    lines = [
        "Сервер триажа слушает http://%s:%d%s" % (args.host, args.port, CHAT_PATHS[0]),
        "Модель основного прохода: %s (%s)"
        % (settings.client_cfg.model, settings.client_cfg.base_url),
        "Модель критика: %s (%s)" % (critic.model, critic.base_url),
        "Триггер критика: %s - %s"
        % (
            settings.self_check_trigger,
            spec7.SELF_CHECK_TRIGGER_TITLES[settings.self_check_trigger],
        ),
        "Ключ: %s" % llm_client.describe_key_source(args.key_env),
        "Имя модели для клиента: %s" % SERVED_MODEL,
        "Версия набора маршрутов: %s - %s"
        % (settings.spec_version, SPEC_VERSION_TITLES[settings.spec_version]),
    ]
    if settings.client_cfg.adapter:
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
