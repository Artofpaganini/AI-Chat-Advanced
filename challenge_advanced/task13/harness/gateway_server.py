"""HTTP-шлюз перед DeepSeek: OpenAI-совместимый POST /v1/chat/completions плюс три
служебных GET-эндпоинта. Реализация строго по GATEWAY_CONTRACT.md, разделы 2-11.

Ключ апстрима читается один раз при старте через llm_client.read_api_key и подставляется
в исходящий запрос сам. Заголовок Authorization от клиента нигде не читается - его нельзя
случайно залогировать, если его вообще не трогать.

Входной гейт (input_guard.check_input) проверяет все сообщения запроса. При verdict
"blocked" апстрим не вызывается вовсе - клиент получает 200 с предупреждением вместо
ответа модели, стоимость нулевая. При "masked" наверх уходят уже маскированные сообщения.
Выходной гейт (output_guard.check_output) проверяет собранный ответ модели; при блокировке
текст ответа подменяется, остальная форма тела (включая нестандартное поле triage, если
апстрим его вернул) не трогается.

Стрим при stream: true идёт в одном из двух режимов (--stream-guard):
buffer (по умолчанию) - шлюз копит весь ответ, проверяет и только потом отдаёт клиенту
одним куском, эффект печатающей машинки теряется, зато заголовок X-Gateway-Verdict в
несущем ответе всегда точный. incremental - чанки идут клиенту сразу по мере получения от
апстрима, и шлюз обрывает поток, как только check_output_partial на накопленном тексте
находит нарушение. Ограничение HTTP: заголовки уходят раньше тела, поэтому X-Gateway-Verdict
в заголовке отражает только исход входного гейта на момент старта потока. Раздел 8.1: если
выходной гейт сработал позже, шлюз перед data: [DONE] отправляет отдельным SSE-событием
{"gateway_output_verdict", "gateway_output_reasons", "gateway_truncated_at_chars"} - это не
обычный chat.completion.chunk, а отдельная структура, чтобы клиент, который её не ждёт, не
пытался распарсить её как чанк. Поле truncated_at_chars и в этом событии, и в журнале аудита -
одно и то же число символов, реально ушедших клиенту до обрыва.

Ограничение частоты - скользящее окно 60 секунд по IP клиента (rate_limit.RateLimiter).
Превышение - 429 с полем error и заголовком Retry-After, входной и выходной гейты в этом
случае не считаются вовсе.

В журнал аудита (audit_log.AuditLog) никогда не попадают: найденный секрет, полный текст
ответа модели, заголовок Authorization. Только превью первых 200 знаков уже
замаскированного текста запроса и хеш исходного текста для сверки повторов.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

TASK13_DIR = os.path.dirname(HARNESS_DIR)
CHALLENGE_DIR = os.path.dirname(TASK13_DIR)
TASK7_HARNESS_DIR = os.path.join(CHALLENGE_DIR, "task7", "harness")
if TASK7_HARNESS_DIR not in sys.path:
    sys.path.insert(0, TASK7_HARNESS_DIR)

import llm_client
import spec13
from audit_log import AuditLog
from cost import compute_cost, estimate_tokens
from input_guard import check_input
from output_guard import check_output, check_output_partial
from rate_limit import RateLimiter

VERDICT_PASS = spec13.GATEWAY_VERDICT_PASS
VERDICT_MASKED = spec13.GATEWAY_VERDICT_MASKED
VERDICT_BLOCKED_INPUT = spec13.GATEWAY_VERDICT_BLOCKED_INPUT
VERDICT_BLOCKED_OUTPUT = spec13.GATEWAY_VERDICT_BLOCKED_OUTPUT
VERDICT_RATE_LIMITED = spec13.GATEWAY_VERDICT_RATE_LIMITED

GUARD_VERDICT_PASS = spec13.VERDICT_PASS
GUARD_VERDICT_MASKED = spec13.VERDICT_MASKED
GUARD_VERDICT_BLOCKED = spec13.VERDICT_BLOCKED

STREAM_GUARD_BUFFER = spec13.STREAM_GUARD_BUFFER
STREAM_GUARD_INCREMENTAL = spec13.STREAM_GUARD_INCREMENTAL
STREAM_GUARD_MODES = spec13.STREAM_GUARD_MODES

CHAT_PATH = "/v1/chat/completions"
AUDIT_PATH = "/gateway/audit"
STATS_PATH = "/gateway/stats"
HEALTH_PATH = "/gateway/health"

JSON_CONTENT_TYPE = "application/json; charset=utf-8"
SSE_CONTENT_TYPE = "text/event-stream; charset=utf-8"
STREAM_DONE_MARKER = b"data: [DONE]\n\n"

MAX_BODY_BYTES = 262144
REQUEST_TIMEOUT_SECONDS = 90
PREVIEW_CHARS = 200
DEFAULT_AUDIT_LIMIT = 20
MAX_AUDIT_LIMIT = 500
UNKNOWN_MODEL = "unknown"
GATEWAY_OUTPUT_EVENT_VERDICT_KEY = "gateway_output_verdict"
GATEWAY_OUTPUT_EVENT_REASONS_KEY = "gateway_output_reasons"
GATEWAY_OUTPUT_EVENT_TRUNCATED_KEY = "gateway_truncated_at_chars"

BAD_BODY_TEXT = "тело запроса не разбирается как JSON: %s"
BODY_TOO_LARGE_TEXT = "тело запроса больше %d байт" % MAX_BODY_BYTES
UNKNOWN_PATH_TEXT = "неизвестный путь: %s"
RATE_LIMITED_TEXT = "превышена частота запросов, повторите через %d сек"
NO_UPSTREAM_KEY_TEXT = (
    "ключ апстрима не найден ни в окружении, ни в local.properties - запрос наверх не ушёл"
)
UPSTREAM_UNREACHABLE_TEXT = "апстрим недоступен: %s"


def write_log(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def normalized_path(raw_path: str) -> str:
    path = (raw_path or "").split("?")[0].split("#")[0]
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""
    chunks: List[str] = []
    for part in value:
        if isinstance(part, str):
            chunks.append(part)
        elif isinstance(part, dict) and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    return "".join(chunks)


def sanitized_messages(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = payload.get("messages")
    if not isinstance(raw, list):
        return []
    cleaned: List[Dict[str, Any]] = []
    for message in raw:
        if isinstance(message, dict) and isinstance(message.get("role"), str):
            cleaned.append(message)
    return cleaned


def join_messages_text(messages: List[Dict[str, Any]]) -> str:
    parts = [content_text(message.get("content")) for message in messages]
    return "\n".join(part for part in parts if part)


def messages_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_request_id() -> str:
    return "gw-" + uuid.uuid4().hex[:20]


def stream_requested(payload: Dict[str, Any]) -> bool:
    value = payload.get("stream")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def passthrough_input_result(messages: List[Dict[str, Any]]) -> SimpleNamespace:
    return SimpleNamespace(
        verdict=GUARD_VERDICT_PASS, reasons=[], masked_count=0, messages=messages, warning_text=""
    )


def passthrough_output_result() -> SimpleNamespace:
    return SimpleNamespace(verdict=GUARD_VERDICT_PASS, reasons=[], replacement_text="")


def dedup_reasons(input_reasons: List[str], output_reasons: List[str]) -> List[str]:
    seen: List[str] = []
    for reason in list(input_reasons) + list(output_reasons):
        if reason not in seen:
            seen.append(reason)
    return seen


def response_choice_text(parsed: Dict[str, Any]) -> str:
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    text = message.get("content")
    return text if isinstance(text, str) else ""


def set_choice_text(parsed: Dict[str, Any], text: str) -> None:
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        return
    message = choices[0].get("message")
    if isinstance(message, dict):
        message["content"] = text


def token_usage(parsed: Dict[str, Any]) -> Tuple[int, int, bool]:
    usage = parsed.get("usage")
    if isinstance(usage, dict) and usage:
        tokens_in = llm_client.token_count(usage, "prompt_tokens")
        tokens_out = llm_client.token_count(usage, "completion_tokens")
        if tokens_in or tokens_out:
            return tokens_in, tokens_out, False
    return 0, 0, True


def completion_response(model: str, content: str) -> Dict[str, Any]:
    return {
        "id": new_request_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model or UNKNOWN_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def stream_chunk(
    response_id: str, created: int, delta: Dict[str, Any], finish_reason: Optional[str]
) -> Dict[str, Any]:
    return {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def output_truncation_event(reasons: List[str], truncated_at_chars: int) -> Dict[str, Any]:
    return {
        GATEWAY_OUTPUT_EVENT_VERDICT_KEY: VERDICT_BLOCKED_OUTPUT,
        GATEWAY_OUTPUT_EVENT_REASONS_KEY: reasons,
        GATEWAY_OUTPUT_EVENT_TRUNCATED_KEY: truncated_at_chars,
    }


def iter_upstream_deltas(response: Any):
    for raw_line in response:
        line = raw_line.decode("utf-8", "replace").strip()
        if not line or not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            return
        try:
            chunk = json.loads(payload)
        except ValueError:
            continue
        delta_text = ""
        finish_reason = None
        choices = chunk.get("choices")
        if isinstance(choices, list) and choices:
            delta = choices[0].get("delta") or {}
            delta_text = delta.get("content") or ""
            finish_reason = choices[0].get("finish_reason")
        yield delta_text, finish_reason, chunk.get("usage")


class GatewaySettings:
    def __init__(
        self,
        upstream_base_url: str,
        rate_limiter: RateLimiter,
        stream_guard: str,
        audit: AuditLog,
        input_guard_enabled: bool,
        output_guard_enabled: bool,
        api_key: str,
        timeout: int,
    ) -> None:
        self.upstream_base_url = upstream_base_url
        self.rate_limiter = rate_limiter
        self.stream_guard = stream_guard
        self.audit = audit
        self.input_guard_enabled = input_guard_enabled
        self.output_guard_enabled = output_guard_enabled
        self.api_key = api_key
        self.timeout = timeout


class GatewayServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: Tuple[str, int], handler_class, settings: GatewaySettings) -> None:
        self.settings = settings
        super().__init__(address, handler_class)


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "LLMGateway/1.0"
    protocol_version = "HTTP/1.1"
    response_started = False

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_error(self, code: Any, message: Any = None, explain: Any = None) -> None:
        self.close_connection = True
        if self.response_started:
            return
        detail = explain or message or ("HTTP %s" % code)
        try:
            self.send_plain_json(int(code), {"error": {"message": str(detail)}})
        except Exception:
            return

    @property
    def settings(self) -> GatewaySettings:
        return self.server.settings

    def send_plain_json(self, status: int, payload: Dict[str, Any]) -> None:
        self.response_started = True
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_gateway_json(
        self,
        status: int,
        payload: Dict[str, Any],
        verdict: str,
        reasons: List[str],
        masked_count: int,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        rate_limit: int,
        rate_remaining: int,
        request_id: str,
    ) -> None:
        self.response_started = True
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.write_gateway_headers(
            verdict, reasons, masked_count, tokens_in, tokens_out, cost_usd,
            rate_limit, rate_remaining, request_id,
        )
        self.end_headers()
        self.wfile.write(body)

    def send_raw_upstream(
        self,
        status: int,
        raw_body: bytes,
        verdict: str,
        reasons: List[str],
        masked_count: int,
        rate_limit: int,
        rate_remaining: int,
        request_id: str,
    ) -> None:
        self.response_started = True
        self.send_response(status)
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(raw_body)))
        self.write_gateway_headers(
            verdict, reasons, masked_count, 0, 0, 0.0, rate_limit, rate_remaining, request_id
        )
        self.end_headers()
        self.wfile.write(raw_body)

    def write_gateway_headers(
        self,
        verdict: str,
        reasons: List[str],
        masked_count: int,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        rate_limit: int,
        rate_remaining: int,
        request_id: str,
    ) -> None:
        self.send_header("X-Gateway-Verdict", verdict)
        self.send_header("X-Gateway-Reasons", ",".join(reasons))
        self.send_header("X-Gateway-Masked-Count", str(masked_count))
        self.send_header("X-Gateway-Tokens-In", str(tokens_in))
        self.send_header("X-Gateway-Tokens-Out", str(tokens_out))
        self.send_header("X-Gateway-Cost-Usd", "%.6f" % cost_usd)
        self.send_header("X-Gateway-RateLimit-Limit", str(rate_limit))
        self.send_header("X-Gateway-RateLimit-Remaining", str(rate_remaining))
        self.send_header("X-Gateway-Request-Id", request_id)

    def start_stream(
        self,
        verdict: str,
        reasons: List[str],
        masked_count: int,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        rate_limit: int,
        rate_remaining: int,
        request_id: str,
    ) -> None:
        self.response_started = True
        self.send_response(200)
        self.send_header("Content-Type", SSE_CONTENT_TYPE)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.write_gateway_headers(
            verdict, reasons, masked_count, tokens_in, tokens_out, cost_usd,
            rate_limit, rate_remaining, request_id,
        )
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

    def do_GET(self) -> None:
        self.response_started = False
        parsed = urllib.parse.urlparse(self.path)
        path = normalized_path(parsed.path)
        if path == HEALTH_PATH:
            self.handle_health()
            return
        if path == AUDIT_PATH:
            self.handle_audit(urllib.parse.parse_qs(parsed.query))
            return
        if path == STATS_PATH:
            self.handle_stats()
            return
        self.send_plain_json(404, {"error": {"message": UNKNOWN_PATH_TEXT % path}})

    def handle_health(self) -> None:
        settings = self.settings
        self.send_plain_json(
            200,
            {
                "status": "ok",
                "upstream": settings.upstream_base_url,
                "input_guard": settings.input_guard_enabled,
                "output_guard": settings.output_guard_enabled,
                "stream_guard": settings.stream_guard,
                "rate_limit_per_minute": settings.rate_limiter.limit_per_minute,
                "key_present": bool(settings.api_key),
            },
        )

    def handle_audit(self, query: Dict[str, List[str]]) -> None:
        raw_limit = (query.get("limit") or [str(DEFAULT_AUDIT_LIMIT)])[0]
        try:
            limit = int(raw_limit)
        except ValueError:
            limit = DEFAULT_AUDIT_LIMIT
        limit = max(1, min(limit, MAX_AUDIT_LIMIT))
        items = self.settings.audit.tail(limit)
        self.send_plain_json(200, {"items": items, "count": len(items)})

    def handle_stats(self) -> None:
        self.send_plain_json(200, self.settings.audit.stats())

    def do_POST(self) -> None:
        self.response_started = False
        path = normalized_path(self.path)
        body, read_error = self.read_body()
        if read_error is not None:
            self.close_connection = True
            self.send_plain_json(400, {"error": {"message": read_error}})
            return
        if path != CHAT_PATH:
            self.send_plain_json(404, {"error": {"message": UNKNOWN_PATH_TEXT % path}})
            return
        try:
            self.handle_completion(body)
        except Exception as unexpected_error:
            self.close_connection = True
            if self.response_started:
                return
            try:
                self.send_plain_json(500, {"error": {"message": str(unexpected_error)}})
            except Exception:
                return

    def handle_completion(self, body: Optional[bytes]) -> None:
        started = time.time()
        settings = self.settings
        client_ip = self.client_address[0]
        request_id = new_request_id()

        allowed, remaining, retry_after = settings.rate_limiter.check(client_ip)
        if not allowed:
            self.reply_rate_limited(request_id, client_ip, retry_after, settings.rate_limiter.limit_per_minute)
            return

        try:
            payload = json.loads((body or b"").decode("utf-8", "replace") or "{}")
        except ValueError as parse_error:
            self.send_plain_json(400, {"error": {"message": BAD_BODY_TEXT % parse_error}})
            return
        if not isinstance(payload, dict):
            self.send_plain_json(400, {"error": {"message": BAD_BODY_TEXT % "тело не объект JSON"}})
            return

        model = payload.get("model")
        model = model if isinstance(model, str) else UNKNOWN_MODEL
        original_messages = sanitized_messages(payload)
        raw_text = join_messages_text(original_messages)
        hash_value = messages_hash(raw_text)
        rate_limit_value = settings.rate_limiter.limit_per_minute

        if settings.input_guard_enabled:
            guard_result = check_input(original_messages)
        else:
            guard_result = passthrough_input_result(original_messages)

        if guard_result.verdict == GUARD_VERDICT_BLOCKED:
            self.reply_blocked_input(
                request_id, model, guard_result, hash_value, client_ip,
                rate_limit_value, remaining, started,
            )
            return

        if guard_result.verdict == GUARD_VERDICT_MASKED:
            outgoing_messages = guard_result.messages
            masked_count = guard_result.masked_count
            input_reasons = guard_result.reasons
        else:
            outgoing_messages = guard_result.messages
            masked_count = 0
            input_reasons = []

        outgoing_payload = dict(payload)
        outgoing_payload["messages"] = outgoing_messages
        outgoing_text = join_messages_text(outgoing_messages)

        if not settings.api_key:
            self.reply_upstream_unreachable(
                request_id, model, NO_UPSTREAM_KEY_TEXT, input_reasons, masked_count,
                rate_limit_value, remaining, hash_value, outgoing_text, client_ip, started,
            )
            return

        if stream_requested(payload):
            self.handle_stream(
                request_id, model, outgoing_payload, outgoing_text, input_reasons,
                masked_count, rate_limit_value, remaining, hash_value, client_ip, started,
            )
            return

        self.handle_plain(
            request_id, model, outgoing_payload, outgoing_text, input_reasons,
            masked_count, rate_limit_value, remaining, hash_value, client_ip, started,
        )

    def reply_rate_limited(self, request_id: str, client_ip: str, retry_after: int, limit: int) -> None:
        self.response_started = True
        body = json.dumps(
            {"error": {"message": RATE_LIMITED_TEXT % retry_after, "type": VERDICT_RATE_LIMITED}},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(429)
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Retry-After", str(retry_after))
        self.write_gateway_headers(
            VERDICT_RATE_LIMITED, [], 0, 0, 0, 0.0, limit, 0, request_id
        )
        self.end_headers()
        self.wfile.write(body)
        self.write_audit(
            request_id, client_ip, "", VERDICT_RATE_LIMITED, [], [], 0, "", "",
            0, 0, 0.0, 0, None, False,
        )

    def reply_blocked_input(
        self, request_id: str, model: str, guard_result: Any, hash_value: str,
        client_ip: str, rate_limit: int, rate_remaining: int, started: float,
    ) -> None:
        content = guard_result.warning_text
        body = completion_response(model, content)
        latency_ms = int((time.time() - started) * 1000)
        self.send_gateway_json(
            200, body, VERDICT_BLOCKED_INPUT, guard_result.reasons, 0, 0, 0, 0.0,
            rate_limit, rate_remaining, request_id,
        )
        self.write_audit(
            request_id, client_ip, model, VERDICT_BLOCKED_INPUT, guard_result.reasons, [],
            0, hash_value, content[:PREVIEW_CHARS], 0, 0, 0.0, latency_ms, None, False,
        )

    def reply_upstream_unreachable(
        self, request_id: str, model: str, reason: str, input_reasons: List[str],
        masked_count: int, rate_limit: int, rate_remaining: int, hash_value: str,
        outgoing_text: str, client_ip: str, started: float,
    ) -> None:
        verdict = VERDICT_MASKED if masked_count else VERDICT_PASS
        body = {"error": {"message": UPSTREAM_UNREACHABLE_TEXT % reason}}
        latency_ms = int((time.time() - started) * 1000)
        self.send_gateway_json(
            502, body, verdict, input_reasons, masked_count, 0, 0, 0.0,
            rate_limit, rate_remaining, request_id,
        )
        self.write_audit(
            request_id, client_ip, model, verdict, input_reasons, [], masked_count,
            hash_value, outgoing_text[:PREVIEW_CHARS], 0, 0, 0.0, latency_ms, None, False,
        )

    def open_upstream(
        self, payload: Dict[str, Any]
    ) -> Tuple[Optional[int], Any, Optional[bytes]]:
        settings = self.settings
        url = llm_client.completions_url(settings.upstream_base_url)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", "Bearer " + settings.api_key)
        try:
            response = urllib.request.urlopen(request, timeout=settings.timeout)
            return response.getcode(), response, None
        except urllib.error.HTTPError as http_error:
            return http_error.code, None, http_error.read()
        except urllib.error.URLError:
            return None, None, None
        except Exception:
            return None, None, None

    def handle_plain(
        self, request_id: str, model: str, outgoing_payload: Dict[str, Any], outgoing_text: str,
        input_reasons: List[str], masked_count: int, rate_limit: int, rate_remaining: int,
        hash_value: str, client_ip: str, started: float,
    ) -> None:
        status, response, error_body = self.open_upstream(outgoing_payload)
        base_verdict = VERDICT_MASKED if masked_count else VERDICT_PASS

        if status is None:
            self.reply_upstream_unreachable(
                request_id, model, "сетевая ошибка или таймаут", input_reasons, masked_count,
                rate_limit, rate_remaining, hash_value, outgoing_text, client_ip, started,
            )
            return

        if status < 200 or status >= 300:
            raw_body = error_body or b""
            latency_ms = int((time.time() - started) * 1000)
            self.send_raw_upstream(
                status, raw_body, base_verdict, input_reasons, masked_count,
                rate_limit, rate_remaining, request_id,
            )
            self.write_audit(
                request_id, client_ip, model, base_verdict, input_reasons, [], masked_count,
                hash_value, outgoing_text[:PREVIEW_CHARS], 0, 0, 0.0, latency_ms, status, False,
            )
            return

        raw_body = response.read()
        response.close()
        try:
            parsed = json.loads(raw_body.decode("utf-8", "replace"))
        except ValueError:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}

        answer_text = response_choice_text(parsed)
        output_reasons: List[str] = []
        final_verdict = base_verdict
        if self.settings.output_guard_enabled:
            output_result = check_output(answer_text, outgoing_text)
        else:
            output_result = passthrough_output_result()
        if output_result.verdict == GUARD_VERDICT_BLOCKED:
            set_choice_text(parsed, output_result.replacement_text)
            output_reasons = output_result.reasons
            final_verdict = VERDICT_BLOCKED_OUTPUT

        tokens_in, tokens_out, estimated = token_usage(parsed)
        if estimated:
            tokens_in = estimate_tokens(outgoing_text)
            tokens_out = estimate_tokens(answer_text)
        cost_usd = compute_cost(tokens_in, tokens_out)

        latency_ms = int((time.time() - started) * 1000)
        self.send_gateway_json(
            status, parsed, final_verdict, dedup_reasons(input_reasons, output_reasons),
            masked_count, tokens_in, tokens_out, cost_usd, rate_limit, rate_remaining, request_id,
        )
        self.write_audit(
            request_id, client_ip, model, final_verdict, input_reasons, output_reasons,
            masked_count, hash_value, outgoing_text[:PREVIEW_CHARS], tokens_in, tokens_out,
            cost_usd, latency_ms, status, estimated,
        )

    def handle_stream(
        self, request_id: str, model: str, outgoing_payload: Dict[str, Any], outgoing_text: str,
        input_reasons: List[str], masked_count: int, rate_limit: int, rate_remaining: int,
        hash_value: str, client_ip: str, started: float,
    ) -> None:
        status, response, error_body = self.open_upstream(outgoing_payload)
        base_verdict = VERDICT_MASKED if masked_count else VERDICT_PASS

        if status is None:
            self.reply_upstream_unreachable(
                request_id, model, "сетевая ошибка или таймаут", input_reasons, masked_count,
                rate_limit, rate_remaining, hash_value, outgoing_text, client_ip, started,
            )
            return
        if status < 200 or status >= 300:
            raw_body = error_body or b""
            latency_ms = int((time.time() - started) * 1000)
            self.send_raw_upstream(
                status, raw_body, base_verdict, input_reasons, masked_count,
                rate_limit, rate_remaining, request_id,
            )
            self.write_audit(
                request_id, client_ip, model, base_verdict, input_reasons, [], masked_count,
                hash_value, outgoing_text[:PREVIEW_CHARS], 0, 0, 0.0, latency_ms, status, False,
            )
            return

        if self.settings.stream_guard == STREAM_GUARD_INCREMENTAL:
            self.stream_incremental(
                request_id, model, response, outgoing_text, input_reasons, masked_count,
                base_verdict, rate_limit, rate_remaining, hash_value, client_ip, started,
            )
        else:
            self.stream_buffer(
                request_id, model, response, outgoing_text, input_reasons, masked_count,
                base_verdict, rate_limit, rate_remaining, hash_value, client_ip, started,
            )

    def stream_buffer(
        self, request_id: str, model: str, response: Any, outgoing_text: str,
        input_reasons: List[str], masked_count: int, base_verdict: str, rate_limit: int,
        rate_remaining: int, hash_value: str, client_ip: str, started: float,
    ) -> None:
        pieces: List[str] = []
        for delta_text, _finish_reason, _usage in iter_upstream_deltas(response):
            if delta_text:
                pieces.append(delta_text)
        response.close()
        answer_text = "".join(pieces)

        output_reasons: List[str] = []
        final_verdict = base_verdict
        if self.settings.output_guard_enabled:
            output_result = check_output(answer_text, outgoing_text)
        else:
            output_result = passthrough_output_result()
        if output_result.verdict == GUARD_VERDICT_BLOCKED:
            answer_text = output_result.replacement_text
            output_reasons = output_result.reasons
            final_verdict = VERDICT_BLOCKED_OUTPUT

        tokens_in = estimate_tokens(outgoing_text)
        tokens_out = estimate_tokens(answer_text)
        cost_usd = compute_cost(tokens_in, tokens_out)
        reasons = dedup_reasons(input_reasons, output_reasons)

        try:
            self.start_stream(
                final_verdict, reasons, masked_count, tokens_in, tokens_out, cost_usd,
                rate_limit, rate_remaining, request_id,
            )
            created = int(time.time())
            self.send_event(stream_chunk(request_id, created, {"role": "assistant"}, None))
            self.send_event(stream_chunk(request_id, created, {"content": answer_text}, None))
            self.send_event(stream_chunk(request_id, created, {}, "stop"))
            self.write_stream_bytes(STREAM_DONE_MARKER)
            self.end_stream()
        except OSError:
            self.close_connection = True

        latency_ms = int((time.time() - started) * 1000)
        self.write_audit(
            request_id, client_ip, model, final_verdict, input_reasons, output_reasons,
            masked_count, hash_value, outgoing_text[:PREVIEW_CHARS], tokens_in, tokens_out,
            cost_usd, latency_ms, 200, True,
        )

    def stream_incremental(
        self, request_id: str, model: str, response: Any, outgoing_text: str,
        input_reasons: List[str], masked_count: int, base_verdict: str, rate_limit: int,
        rate_remaining: int, hash_value: str, client_ip: str, started: float,
    ) -> None:
        tokens_in_guess = estimate_tokens(outgoing_text)
        pieces: List[str] = []
        sent_chars = 0
        truncated_at_chars: Optional[int] = None
        try:
            self.start_stream(
                base_verdict, input_reasons, masked_count, tokens_in_guess, 0, 0.0,
                rate_limit, rate_remaining, request_id,
            )
            created = int(time.time())
            self.send_event(stream_chunk(request_id, created, {"role": "assistant"}, None))

            blocked_result = None
            for delta_text, finish_reason, _usage in iter_upstream_deltas(response):
                if delta_text:
                    pieces.append(delta_text)
                    if self.settings.output_guard_enabled:
                        check = check_output_partial("".join(pieces), outgoing_text)
                        if check.verdict == GUARD_VERDICT_BLOCKED:
                            blocked_result = check
                            break
                    self.send_event(stream_chunk(request_id, created, {"content": delta_text}, None))
                    sent_chars += len(delta_text)
                if finish_reason:
                    break
            response.close()

            output_reasons: List[str] = []
            final_verdict = base_verdict
            self.send_event(stream_chunk(request_id, created, {}, "stop"))
            if blocked_result is not None:
                output_reasons = blocked_result.reasons
                final_verdict = VERDICT_BLOCKED_OUTPUT
                truncated_at_chars = sent_chars
                self.send_event(output_truncation_event(output_reasons, truncated_at_chars))

            self.write_stream_bytes(STREAM_DONE_MARKER)
            self.end_stream()
        except OSError:
            self.close_connection = True
            output_reasons = []
            final_verdict = base_verdict

        answer_text = "".join(pieces)
        tokens_in = estimate_tokens(outgoing_text)
        tokens_out = estimate_tokens(answer_text)
        cost_usd = compute_cost(tokens_in, tokens_out)
        latency_ms = int((time.time() - started) * 1000)
        self.write_audit(
            request_id, client_ip, model, final_verdict, input_reasons, output_reasons,
            masked_count, hash_value, outgoing_text[:PREVIEW_CHARS], tokens_in, tokens_out,
            cost_usd, latency_ms, 200, True, truncated_at_chars,
        )

    def write_audit(
        self, request_id: str, client_ip: str, model: str, verdict: str,
        input_reasons: List[str], output_reasons: List[str], masked_count: int,
        messages_hash_value: str, prompt_preview: str, tokens_in: int, tokens_out: int,
        cost_usd: float, latency_ms: int, upstream_status: Optional[int], tokens_estimated: bool,
        truncated_at_chars: Optional[int] = None,
    ) -> None:
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "request_id": request_id,
            "client_ip": client_ip,
            "model": model,
            "verdict": verdict,
            "input_reasons": input_reasons,
            "output_reasons": output_reasons,
            "masked_count": masked_count,
            "messages_hash": messages_hash_value,
            "prompt_preview": prompt_preview,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "upstream_status": upstream_status,
            "tokens_estimated": tokens_estimated,
            "truncated_at_chars": truncated_at_chars,
        }
        self.settings.audit.write(record)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LLM Gateway поверх DeepSeek - вход/выход/лимит/учёт")
    parser.add_argument("--host", default=spec13.GATEWAY_HOST)
    parser.add_argument("--port", type=int, default=spec13.GATEWAY_PORT)
    parser.add_argument("--upstream", dest="upstream", default=spec13.UPSTREAM_BASE_URL)
    parser.add_argument(
        "--rate-limit", dest="rate_limit", type=int, default=spec13.DEFAULT_RATE_LIMIT_PER_MINUTE
    )
    parser.add_argument(
        "--stream-guard", dest="stream_guard", choices=list(STREAM_GUARD_MODES), default=STREAM_GUARD_BUFFER
    )
    parser.add_argument("--audit-dir", dest="audit_dir", default=spec13.AUDIT_DIR)
    parser.add_argument("--no-input-guard", dest="input_guard", action="store_false", default=True)
    parser.add_argument("--no-output-guard", dest="output_guard", action="store_false", default=True)
    parser.add_argument("--timeout", type=int, default=REQUEST_TIMEOUT_SECONDS)
    return parser


def build_settings(args: argparse.Namespace) -> GatewaySettings:
    return GatewaySettings(
        upstream_base_url=args.upstream,
        rate_limiter=RateLimiter(args.rate_limit),
        stream_guard=args.stream_guard,
        audit=AuditLog(args.audit_dir),
        input_guard_enabled=args.input_guard,
        output_guard_enabled=args.output_guard,
        api_key=llm_client.read_api_key(spec13.DEFAULT_KEY_ENV),
        timeout=args.timeout,
    )


def describe_startup(args: argparse.Namespace, settings: GatewaySettings) -> List[str]:
    return [
        "Шлюз слушает http://%s:%d%s" % (args.host, args.port, CHAT_PATH),
        "Апстрим: %s" % settings.upstream_base_url,
        "Ключ апстрима: %s" % ("найден" if settings.api_key else "НЕ найден, запросы наверх будут падать 502"),
        "Входной гейт: %s" % ("on" if settings.input_guard_enabled else "off"),
        "Выходной гейт: %s" % ("on" if settings.output_guard_enabled else "off"),
        "Режим стрима: %s" % settings.stream_guard,
        "Лимит частоты: %d/мин" % settings.rate_limiter.limit_per_minute,
        "Журнал аудита: %s" % args.audit_dir,
    ]


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    settings = build_settings(args)
    server = GatewayServer((args.host, args.port), GatewayHandler, settings)
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
