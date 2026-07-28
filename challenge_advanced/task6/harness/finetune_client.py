# -*- coding: utf-8 -*-
"""
Клиент файнтюна ассистента ALVA через OpenAI-совместимый API.

Три шага: upload (загрузка train.jsonl и eval.jsonl), create (создание job), poll (ожидание статуса).
Реальный запуск файнтюна требует прямого ключа OpenAI, ключи OpenRouter и DeepSeek для этого не
подходят: OpenRouter только роутит инференс, у DeepSeek публичного fine-tuning API нет.

Защита от случайной отправки: dry-run включён по умолчанию, сеть трогается ТОЛЬКО с флагом --confirm.
Ключ читается лишь из переменной окружения (по умолчанию OPENAI_API_KEY) и нигде не печатается.
Все запросы и ответы пишутся в raw/finetune_client_log.jsonl.

Запуск: python3 harness/finetune_client.py --dry-run
        python3 harness/finetune_client.py --step upload --confirm
        python3 harness/finetune_client.py --step all --confirm
        python3 harness/finetune_client.py --step poll --job-id ftjob-xxx --confirm
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

try:
    from spec import ARTIFACTS_DIR, RAW_DIR
except ImportError as import_error:
    sys.stderr.write(
        "Не найден модуль harness/spec.py (он держит пути проекта). "
        "Соберите харнесс полностью и повторите. Причина: %s\n" % import_error
    )
    sys.exit(2)

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"
DEFAULT_SUFFIX = "alva-parent-coach"
DEFAULT_POLL_INTERVAL_SECONDS = 30
TRAIN_FILE_NAME = "train.jsonl"
EVAL_FILE_NAME = "eval.jsonl"
LOG_FILE_NAME = "finetune_client_log.jsonl"
FILE_PURPOSE = "fine-tune"
FILE_CONTENT_TYPE = "application/jsonl"
REQUEST_TIMEOUT_SECONDS = 90
RETRY_DELAYS_SECONDS = (2, 5, 15, 40)
RETRYABLE_STATUS = 429
SERVER_ERROR_FLOOR = 500
MAX_POLL_SECONDS = 4 * 60 * 60
EVENTS_LIMIT = 20
BODY_PREVIEW_LIMIT = 500
TERMINAL_STATUSES = ("succeeded", "failed", "cancelled")
MASKED_AUTHORIZATION = "Authorization: Bearer ***"
EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2
LOG_PATH = os.path.join(RAW_DIR, LOG_FILE_NAME)


class PreflightError(Exception):
    pass


class ApiError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Файнтюн ассистента ALVA. Без --confirm ничего не отправляется.",
    )
    parser.add_argument("--step", choices=("all", "upload", "create", "poll"), default="all")
    parser.add_argument("--train", dest="train_path", default=None)
    parser.add_argument("--eval", dest="eval_path", default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--suffix", default=DEFAULT_SUFFIX)
    parser.add_argument("--base-url", dest="base_url", default=DEFAULT_BASE_URL)
    parser.add_argument("--key-env", dest="key_env", default=DEFAULT_KEY_ENV)
    parser.add_argument("--job-id", dest="job_id", default=None)
    parser.add_argument(
        "--poll-interval",
        dest="poll_interval",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
    )
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--training-file-id", dest="training_file_id", default=None)
    parser.add_argument("--validation-file-id", dest="validation_file_id", default=None)
    return parser


def resolve_path(raw_value: Optional[str], default_name: str) -> str:
    if raw_value:
        return os.path.abspath(raw_value)
    return os.path.join(ARTIFACTS_DIR, default_name)


def append_log(step: str, method: str, url: str, status: Optional[int], body_preview: str) -> None:
    entry = {
        "ts": time.time(),
        "step": step,
        "method": method,
        "url": url,
        "status": status,
        "body_preview": body_preview[:BODY_PREVIEW_LIMIT],
    }
    log_dir = os.path.dirname(LOG_PATH)
    if log_dir and not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def inspect_file(path: str) -> Dict[str, Any]:
    info = {"path": path, "exists": False, "size": 0, "lines": 0, "problem": None}
    if not os.path.isfile(path):
        info["problem"] = "файл не найден (его собирает build_dataset.py)"
        return info
    info["exists"] = True
    info["size"] = os.path.getsize(path)
    if info["size"] == 0:
        info["problem"] = "файл пустой"
        return info
    lines = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except ValueError as parse_error:
                info["problem"] = "строка %d не парсится как JSON: %s" % (line_number, parse_error)
                return info
            if not isinstance(record, dict) or "messages" not in record:
                info["problem"] = "в строке %d нет ключа messages" % line_number
                return info
            lines += 1
    info["lines"] = lines
    if lines == 0:
        info["problem"] = "нет ни одной непустой строки"
    return info


def preflight(paths: List[str]) -> List[Dict[str, Any]]:
    reports = []
    for path in paths:
        report = inspect_file(path)
        reports.append(report)
        if report["problem"] is not None:
            raise PreflightError("%s: %s" % (path, report["problem"]))
    return reports


def build_multipart(file_path: str) -> Tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    file_name = os.path.basename(file_path)
    with open(file_path, "rb") as handle:
        file_bytes = handle.read()
    chunks = []
    chunks.append(("--" + boundary + "\r\n").encode("utf-8"))
    chunks.append(b'Content-Disposition: form-data; name="purpose"\r\n\r\n')
    chunks.append((FILE_PURPOSE + "\r\n").encode("utf-8"))
    chunks.append(("--" + boundary + "\r\n").encode("utf-8"))
    chunks.append(
        ('Content-Disposition: form-data; name="file"; filename="%s"\r\n' % file_name).encode("utf-8")
    )
    chunks.append(("Content-Type: %s\r\n\r\n" % FILE_CONTENT_TYPE).encode("utf-8"))
    chunks.append(file_bytes)
    chunks.append(b"\r\n")
    chunks.append(("--" + boundary + "--\r\n").encode("utf-8"))
    return b"".join(chunks), "multipart/form-data; boundary=" + boundary


def is_retryable_status(status: int) -> bool:
    return status == RETRYABLE_STATUS or status >= SERVER_ERROR_FLOOR


def send_once(
    method: str,
    url: str,
    body: Optional[bytes],
    content_type: Optional[str],
    api_key: str,
) -> Tuple[int, str]:
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Authorization", "Bearer " + api_key)
    if content_type is not None:
        request.add_header("Content-Type", content_type)
    response = urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        raw_body = response.read().decode("utf-8", "replace")
        return response.getcode(), raw_body
    finally:
        response.close()


def request_with_retries(
    step: str,
    method: str,
    url: str,
    body: Optional[bytes],
    content_type: Optional[str],
    api_key: str,
) -> Dict[str, Any]:
    attempt = 0
    while True:
        try:
            status, raw_body = send_once(method, url, body, content_type, api_key)
            append_log(step, method, url, status, raw_body)
            try:
                return json.loads(raw_body)
            except ValueError as parse_error:
                raise ApiError("ответ %s %s не парсится как JSON: %s" % (method, url, parse_error))
        except urllib.error.HTTPError as http_error:
            try:
                error_body = http_error.read().decode("utf-8", "replace")
            except Exception:
                error_body = ""
            append_log(step, method, url, http_error.code, error_body)
            message = "HTTP %d на %s %s: %s" % (http_error.code, method, url, error_body[:300])
            if not is_retryable_status(http_error.code) or attempt >= len(RETRY_DELAYS_SECONDS):
                raise ApiError(message)
        except urllib.error.URLError as url_error:
            append_log(step, method, url, None, "сетевая ошибка: %s" % url_error.reason)
            message = "сетевая ошибка на %s %s: %s" % (method, url, url_error.reason)
            if attempt >= len(RETRY_DELAYS_SECONDS):
                raise ApiError(message)
        delay = RETRY_DELAYS_SECONDS[attempt]
        sys.stdout.write("  повтор через %d с: %s\n" % (delay, message))
        sys.stdout.flush()
        time.sleep(delay)
        attempt += 1


def resolve_api_key(key_env: str) -> str:
    api_key = os.environ.get(key_env, "").strip()
    if not api_key:
        sys.stderr.write(
            "Не задана переменная окружения %s. Экспортируйте ключ OpenAI и повторите: "
            "export %s=<ваш ключ>\n" % (key_env, key_env)
        )
        sys.exit(EXIT_CONFIG_ERROR)
    return api_key


def build_job_body(
    training_file_id: str,
    validation_file_id: str,
    model: str,
    suffix: str,
) -> Dict[str, Any]:
    return {
        "training_file": training_file_id,
        "validation_file": validation_file_id,
        "model": model,
        "suffix": suffix,
        "hyperparameters": {"n_epochs": "auto"},
    }


def do_upload(base_url: str, api_key: str, file_path: str) -> str:
    body, content_type = build_multipart(file_path)
    url = base_url + "/files"
    sys.stdout.write("upload: %s (%d байт) -> POST %s\n" % (os.path.basename(file_path), len(body), url))
    parsed = request_with_retries("upload", "POST", url, body, content_type, api_key)
    file_id = parsed.get("id")
    if not file_id:
        raise ApiError("в ответе на загрузку %s нет id" % file_path)
    sys.stdout.write("  готово, file id: %s\n" % file_id)
    return file_id


def do_create(
    base_url: str,
    api_key: str,
    training_file_id: str,
    validation_file_id: str,
    model: str,
    suffix: str,
) -> str:
    url = base_url + "/fine_tuning/jobs"
    payload = build_job_body(training_file_id, validation_file_id, model, suffix)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.write("create: POST %s\n" % url)
    parsed = request_with_retries("create", "POST", url, body, "application/json", api_key)
    job_id = parsed.get("id")
    if not job_id:
        raise ApiError("в ответе на создание job нет id")
    sys.stdout.write("  готово, job id: %s, статус: %s\n" % (job_id, parsed.get("status")))
    return job_id


def do_poll(base_url: str, api_key: str, job_id: str, poll_interval: int) -> int:
    job_url = base_url + "/fine_tuning/jobs/" + job_id
    events_url = job_url + "/events?limit=%d" % EVENTS_LIMIT
    started = time.time()
    seen_events = set()
    sys.stdout.write("poll: %s каждые %d с, максимум %d ч\n" % (job_url, poll_interval, MAX_POLL_SECONDS // 3600))
    while True:
        job = request_with_retries("poll", "GET", job_url, None, None, api_key)
        status = job.get("status", "unknown")
        elapsed = int(time.time() - started)
        sys.stdout.write("  [%d с] статус: %s\n" % (elapsed, status))
        events = request_with_retries("poll_events", "GET", events_url, None, None, api_key)
        for event in reversed(events.get("data") or []):
            event_id = event.get("id")
            if event_id in seen_events:
                continue
            seen_events.add(event_id)
            sys.stdout.write("    событие: %s\n" % event.get("message", ""))
        if status in TERMINAL_STATUSES:
            sys.stdout.write("Финальный статус: %s\n" % status)
            if status == "succeeded":
                sys.stdout.write("Модель: %s\n" % job.get("fine_tuned_model"))
                return EXIT_OK
            return EXIT_DATA_ERROR
        if time.time() - started > MAX_POLL_SECONDS:
            sys.stdout.write(
                "Ожидание превысило %d ч, выхожу. Job %s остался в статусе %s, "
                "проверьте его позже: --step poll --job-id %s --confirm\n"
                % (MAX_POLL_SECONDS // 3600, job_id, status, job_id)
            )
            return EXIT_DATA_ERROR
        time.sleep(poll_interval)


def print_file_plan(title: str, report: Dict[str, Any]) -> None:
    if report["problem"] is not None:
        sys.stdout.write("  %s: %s -> ПРОПУСК, %s\n" % (title, report["path"], report["problem"]))
        return
    sys.stdout.write(
        "  %s: %s, %d байт, %d строк\n"
        % (title, report["path"], report["size"], report["lines"])
    )


def print_dry_run(args: argparse.Namespace, base_url: str, train_path: str, eval_path: str) -> None:
    train_report = inspect_file(train_path)
    eval_report = inspect_file(eval_path)
    sys.stdout.write("DRY-RUN: сеть не используется, ключ не требуется. Для отправки нужен --confirm.\n")
    sys.stdout.write("Шаг:              %s\n" % args.step)
    sys.stdout.write("Base URL:         %s\n" % base_url)
    sys.stdout.write("Ключ из env:      %s (значение не печатается)\n" % args.key_env)
    sys.stdout.write("Заголовки:        %s\n" % MASKED_AUTHORIZATION)
    sys.stdout.write("Лог вызовов:      %s\n" % LOG_PATH)
    sys.stdout.write("\n1) upload -> POST %s/files (multipart/form-data, purpose=%s)\n" % (base_url, FILE_PURPOSE))
    print_file_plan("training_file", train_report)
    print_file_plan("validation_file", eval_report)
    sys.stdout.write(
        "\n2) create -> POST %s/fine_tuning/jobs, тело:\n%s\n"
        % (
            base_url,
            json.dumps(
                build_job_body(
                    args.training_file_id or "<id из шага upload для train.jsonl>",
                    args.validation_file_id or "<id из шага upload для eval.jsonl>",
                    args.model,
                    args.suffix,
                ),
                ensure_ascii=False,
                indent=2,
            ),
        )
    )
    sys.stdout.write(
        "\n3) poll -> GET %s/fine_tuning/jobs/%s раз в %d с плюс GET .../events?limit=%d\n"
        % (base_url, args.job_id or "<job_id из шага create>", args.poll_interval, EVENTS_LIMIT)
    )
    sys.stdout.write("   Терминальные статусы: %s. Максимум ожидания: %d ч.\n" % (", ".join(TERMINAL_STATUSES), MAX_POLL_SECONDS // 3600))
    if train_report["problem"] is not None or eval_report["problem"] is not None:
        sys.stdout.write(
            "\nВНИМАНИЕ: датасет ещё не готов, реальный запуск сейчас упал бы на предполётной проверке.\n"
        )
    sys.stdout.write("\nНичего не отправлено.\n")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    base_url = args.base_url.rstrip("/")
    train_path = resolve_path(args.train_path, TRAIN_FILE_NAME)
    eval_path = resolve_path(args.eval_path, EVAL_FILE_NAME)
    if args.poll_interval <= 0:
        sys.stderr.write("Значение --poll-interval должно быть больше нуля.\n")
        return EXIT_CONFIG_ERROR

    if args.dry_run or not args.confirm:
        if args.dry_run and args.confirm:
            sys.stdout.write("Флаги --dry-run и --confirm вместе: выигрывает --dry-run, отправки не будет.\n")
        print_dry_run(args, base_url, train_path, eval_path)
        return EXIT_OK

    api_key = resolve_api_key(args.key_env)
    training_file_id = args.training_file_id
    validation_file_id = args.validation_file_id

    try:
        if args.step in ("all", "upload"):
            preflight([train_path, eval_path])
            training_file_id = do_upload(base_url, api_key, train_path)
            validation_file_id = do_upload(base_url, api_key, eval_path)
            if args.step == "upload":
                sys.stdout.write(
                    "\nДальше: --step create --training-file-id %s --validation-file-id %s --confirm\n"
                    % (training_file_id, validation_file_id)
                )
                return EXIT_OK

        job_id = args.job_id
        if args.step in ("all", "create"):
            if not training_file_id or not validation_file_id:
                sys.stderr.write(
                    "Для шага create нужны id загруженных файлов: "
                    "--training-file-id и --validation-file-id, либо запускайте --step all.\n"
                )
                return EXIT_CONFIG_ERROR
            job_id = do_create(
                base_url, api_key, training_file_id, validation_file_id, args.model, args.suffix
            )
            if args.step == "create":
                sys.stdout.write("\nДальше: --step poll --job-id %s --confirm\n" % job_id)
                return EXIT_OK

        if args.step in ("all", "poll"):
            if not job_id:
                sys.stderr.write("Для шага poll нужен --job-id.\n")
                return EXIT_CONFIG_ERROR
            return do_poll(base_url, api_key, job_id, args.poll_interval)
    except PreflightError as preflight_error:
        sys.stderr.write("Предполётная проверка не прошла, ничего не отправлено: %s\n" % preflight_error)
        return EXIT_DATA_ERROR
    except ApiError as api_error:
        sys.stderr.write("Ошибка API: %s\n" % api_error)
        return EXIT_DATA_ERROR
    except OSError as os_error:
        sys.stderr.write("Ошибка файловой системы: %s\n" % os_error)
        return EXIT_DATA_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
