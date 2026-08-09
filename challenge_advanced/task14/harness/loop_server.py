"""Сервер цикла: HTTP на stdlib, порт 8092 (LOOP_CONTRACT.md разделы 2, 8.2).

POST /loop/run - запускает цикл GENERATE -> LINT -> BUILD -> SECURITY -> COMMIT, отдаёт
text/event-stream с событием на каждую смену стадии. GET /loop/history - последние прогоны из
журнала. GET /loop/health - жив ли сервер, адрес шлюза, лимит итераций.

Оба вызова модели идут через шлюз task13 на 8091 (call_llm ниже), заголовок X-Gateway-Source
различает codegen и security_review. Ключ шлюзу не передаётся - он свой подставляет сам.
Песочница и коммит - только через sandbox.py, в рабочее дерево REPO_ROOT сервер не пишет
ничего (раздел 12). Один /loop/run прогон занимает песочницу целиком - конкурентные прогоны
сериализуются через SANDBOX_LOCK, иначе gradle одного прогона затопчет файлы другого.
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import spec14

if spec14.TASK13_HARNESS_DIR not in sys.path:
    sys.path.insert(0, spec14.TASK13_HARNESS_DIR)

import loop_log
import loop_stages
import sandbox as sandbox_ops
from cost import compute_cost, estimate_tokens

JSON_CONTENT_TYPE = "application/json; charset=utf-8"
SSE_CONTENT_TYPE = "text/event-stream; charset=utf-8"

RUN_PATH = "/loop/run"
HISTORY_PATH = "/loop/history"
HEALTH_PATH = "/loop/health"

BAD_BODY_TEXT = "тело запроса не разбирается как JSON: %s"
MISSING_TASK_TEXT = "поле task обязательно и должно быть непустой строкой"
TASK_TOO_LONG_TEXT = "поле task длиннее %d символов" % spec14.MAX_TASK_CHARS
UNKNOWN_PATH_TEXT = "неизвестный путь: %s"
BODY_TOO_LARGE_TEXT = "тело запроса больше %d байт" % spec14.MAX_BODY_BYTES
SOURCE_FILE_EMPTY_TEXT = "поле source_file должно быть непустой строкой"
SOURCE_FILE_OUTSIDE_REPO_TEXT = "source_file обязан быть путём внутри дерева проекта"
SOURCE_FILE_NOT_FOUND_TEXT = "source_file не найден в дереве проекта: %s"
SOURCE_FILE_TOO_LARGE_TEXT = "source_file больше %d байт" % spec14.MAX_SOURCE_FILE_BYTES


def new_run_id() -> str:
    return "loop-" + uuid.uuid4().hex[:16]


def write_log(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def normalized_path(raw_path: str) -> str:
    path = (raw_path or "").split("?")[0].split("#")[0]
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def resolve_source_file(raw_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Проверяет source_file (режим правки, раздел 8.2 расширен): путь обязан лежать внутри
    REPO_ROOT (без ../ побегов наружу), файл обязан существовать и быть не больше лимита.
    Возвращает (нормализованный относительный путь, текст ошибки)."""
    normalized = raw_path.strip().lstrip("/")
    repo_root_real = os.path.realpath(spec14.REPO_ROOT)
    absolute = os.path.realpath(os.path.join(repo_root_real, normalized))
    if os.path.commonpath([absolute, repo_root_real]) != repo_root_real:
        return None, SOURCE_FILE_OUTSIDE_REPO_TEXT
    if not os.path.isfile(absolute):
        return None, SOURCE_FILE_NOT_FOUND_TEXT % normalized
    if os.path.getsize(absolute) > spec14.MAX_SOURCE_FILE_BYTES:
        return None, SOURCE_FILE_TOO_LARGE_TEXT
    return normalized, None


def read_source_file(relative_path: str) -> str:
    """Читает source_file из REPO_ROOT. Только чтение - раздел 12 запрещает писать в рабочее
    дерево, читать оттуда разрешено, это тот же файл, что открыл бы разработчик руками."""
    absolute = os.path.join(spec14.REPO_ROOT, relative_path)
    with open(absolute, encoding="utf-8") as file:
        return file.read()


def _extract_choice_text(parsed: Any) -> str:
    if not isinstance(parsed, dict):
        return ""
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _int_header(headers: Any, name: str) -> int:
    try:
        return int(headers.get(name, "0")) if headers else 0
    except ValueError:
        return 0


def _float_header(headers: Any, name: str) -> float:
    try:
        return float(headers.get(name, "0")) if headers else 0.0
    except ValueError:
        return 0.0


def _gateway_info(headers: Any, status: Optional[int], fallback_reason: str = "") -> Dict[str, Any]:
    verdict = headers.get(spec14.GATEWAY_VERDICT_HEADER) if headers else None
    reasons_raw = headers.get(spec14.GATEWAY_REASONS_HEADER, "") if headers else ""
    reasons = [reason for reason in reasons_raw.split(",") if reason]
    if not reasons and fallback_reason:
        reasons = [fallback_reason]
    return {
        "verdict": verdict or spec14.GATEWAY_VERDICT_UNREACHABLE,
        "reasons": reasons,
        "request_id": headers.get(spec14.GATEWAY_REQUEST_ID_HEADER, "") if headers else "",
        "tokens_in": _int_header(headers, spec14.GATEWAY_TOKENS_IN_HEADER),
        "tokens_out": _int_header(headers, spec14.GATEWAY_TOKENS_OUT_HEADER),
        "cost_usd": _float_header(headers, spec14.GATEWAY_COST_HEADER),
        "http_status": status,
    }


def build_gateway_client(gateway_url: str, timeout: int, run_id: str):
    """Строит call_llm(system, user, source) -> (text, gateway_info) поверх шлюза на gateway_url.

    Один call_llm - один прогон: run_id уходит в X-Gateway-Run-Id на каждый вызов, чтобы аудит
    шлюза можно было сопоставить с конкретной записью в журнале цикла (пока шлюз это поле не
    пишет в свой аудит - это его сторона, не эта функция)."""
    endpoint = gateway_url.rstrip("/") + spec14.GATEWAY_CHAT_PATH

    def call_llm(system: str, user: str, source: str) -> Tuple[str, Dict[str, Any]]:
        payload = {
            "model": spec14.DEFAULT_MODEL,
            "temperature": spec14.CALL_TEMPERATURE,
            "max_tokens": spec14.CALL_MAX_TOKENS,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(endpoint, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header(spec14.GATEWAY_SOURCE_HEADER, source)
        request.add_header(spec14.GATEWAY_RUN_ID_HEADER, run_id)
        try:
            response = urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as http_error:
            error_body = http_error.read()
            try:
                message = json.loads(error_body.decode("utf-8", "replace")).get("error", {}).get("message", "")
            except ValueError:
                message = ""
            gateway = _gateway_info(http_error.headers, http_error.code, message or ("HTTP %s" % http_error.code))
            return "", gateway
        except urllib.error.URLError as url_error:
            return "", {
                "verdict": spec14.GATEWAY_VERDICT_UNREACHABLE, "reasons": [str(url_error.reason)],
                "request_id": "", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "http_status": None,
            }
        except OSError as os_error:
            return "", {
                "verdict": spec14.GATEWAY_VERDICT_UNREACHABLE, "reasons": [str(os_error)],
                "request_id": "", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "http_status": None,
            }

        status = response.getcode()
        gateway = _gateway_info(response.headers, status)
        raw_body = response.read()
        response.close()
        try:
            parsed = json.loads(raw_body.decode("utf-8", "replace"))
        except ValueError:
            parsed = {}
        return _extract_choice_text(parsed), gateway

    return call_llm


def _event(stage: str, iteration: int, status: str) -> Dict[str, Any]:
    return {"stage": stage, "iteration": iteration, "status": status}


def _event_from_result(result: "loop_stages.StageResult", iteration: int) -> Dict[str, Any]:
    event = {"stage": result.stage, "iteration": iteration, "status": result.status}
    if result.stage == spec14.STAGE_GENERATE and result.status == spec14.STATUS_DONE and result.files:
        event["files"] = sorted(os.path.basename(path) for path in result.files)
    if result.stage == spec14.STAGE_SECURITY and result.findings is not None:
        event["findings"] = [loop_stages.finding_to_dict(finding) for finding in result.findings]
    elif result.errors:
        event["errors"] = result.errors
    if result.gateway is not None:
        verdict = result.gateway.get("verdict")
        if verdict:
            event["gateway_verdict"] = verdict
        reasons = result.gateway.get("reasons")
        if reasons:
            event["gateway_reasons"] = reasons
    if result.stage == spec14.STAGE_COMMIT and result.commit:
        event["commit"] = result.commit
    if result.artifact_path:
        event["artifact"] = result.artifact_path
    if result.stage == spec14.STAGE_SECURITY and result.malformed_block_count:
        event["malformed_blocks"] = result.malformed_block_count
    return event


def _stage_log_entry(result: "loop_stages.StageResult", iteration: int) -> Dict[str, Any]:
    return {
        "stage": result.stage, "iteration": iteration, "status": result.status,
        "duration_seconds": result.duration_seconds,
    }


def _record_gateway_calls(gateway_calls: List[Dict[str, Any]], source: str, result: "loop_stages.StageResult") -> None:
    attempts = result.gateway_attempts or ([result.gateway] if result.gateway else [])
    for gateway in attempts:
        if not gateway:
            continue
        gateway_calls.append({
            "source": source,
            "verdict": gateway.get("verdict"),
            "reasons": gateway.get("reasons", []),
            "tokens_in": gateway.get("tokens_in", 0),
            "tokens_out": gateway.get("tokens_out", 0),
            "cost_usd": gateway.get("cost_usd", 0.0),
        })


def _files_for_security_review(final_files: Dict[str, str]) -> Dict[str, str]:
    """Всё, что реально уходит в коммит песочницы - не только .kt (найдено разбором прогона 1:
    проверка видела только сгенерированный файл, build.gradle.kts модуля и добавленная строка в
    settings.gradle.kts ей не показывались, а именно build.gradle.kts несёт факт "модуль только
    androidMain, без commonMain/iosMain" - штука, которую в .kt не увидеть). Манифест сюда не
    попадает - этот харнесс его не создаёт и не трогает вовсе."""
    files = dict(final_files)
    files[spec14.SANDBOX_MODULE_RELATIVE_PATH + "/build.gradle.kts"] = sandbox_ops.MODULE_BUILD_FILE
    files["settings.gradle.kts (добавленная строка)"] = 'include("%s")\n' % spec14.SANDBOX_MODULE_GRADLE_PATH
    return files


def _save_final_code_artifact(log_dir: str, run_id: str, final_files: Dict[str, str]) -> Optional[str]:
    """Песочница переписывается каждым следующим прогоном (раздел 12 - один каталог на всех),
    поэтому единственный долгоживущий след неудачного прогона - файл в raw/. Успешный прогон
    восстановим и через git-коммит песочницы, но дублировать сюда не вредно - один прогон и
    здесь, и там, никакого рассинхрона."""
    if not final_files:
        return None
    target_dir = os.path.join(log_dir, "artifacts", "%s-final-code" % run_id)
    os.makedirs(target_dir, exist_ok=True)
    for path, body in final_files.items():
        with open(os.path.join(target_dir, os.path.basename(path)), "w", encoding="utf-8") as file:
            file.write(body)
    return os.path.relpath(target_dir, spec14.TASK_DIR)


def _save_security_artifact(log_dir: str, run_id: str, iteration: int, raw_responses: List[str]) -> Optional[str]:
    if not raw_responses:
        return None
    artifacts_dir = os.path.join(log_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    filename = "%s-i%d-security-response.txt" % (run_id, iteration)
    path = os.path.join(artifacts_dir, filename)
    with open(path, "w", encoding="utf-8") as file:
        for index, text in enumerate(raw_responses, start=1):
            file.write("----- попытка %d/%d -----\n" % (index, len(raw_responses)))
            file.write(text)
            file.write("\n\n")
    return os.path.relpath(path, spec14.TASK_DIR)


def execute_run(task: str, max_iterations: int, call_llm, sandbox_root: str, run_id: str,
                 log_dir: str, journal_out: Dict[str, Any]):
    """Генератор: по одному событию на смену стадии, ровно как раздел 8.2. journal_out
    заполняется как побочный эффект - к моменту исчерпания генератора в нём лежит полная
    запись для loop_log.LoopLog."""
    stages_log: List[Dict[str, Any]] = []
    all_findings: List[Any] = []
    gateway_calls: List[Dict[str, Any]] = []
    lint_errors_log: List[Dict[str, Any]] = []
    build_errors_log: List[Dict[str, Any]] = []
    gateway_blocks = 0
    security_review_first_try = 0
    security_review_rescued = 0
    security_review_failed = 0
    security_malformed_blocks: List[Dict[str, Any]] = []
    security_attempt_discrepancies: List[Dict[str, Any]] = []
    feedback = ""
    commit_hash: Optional[str] = None
    stopped_at: Optional[str] = None
    final_files: Dict[str, str] = {}
    iteration = 0

    for iteration in range(1, max_iterations + 1):
        yield _event(spec14.STAGE_GENERATE, iteration, spec14.STATUS_RUNNING)
        generate_result = loop_stages.run_generate(task, feedback, call_llm)
        stages_log.append(_stage_log_entry(generate_result, iteration))
        _record_gateway_calls(gateway_calls, spec14.SOURCE_CODEGEN, generate_result)
        yield _event_from_result(generate_result, iteration)

        if generate_result.status == spec14.STATUS_BLOCKED:
            gateway_blocks += 1
            feedback = loop_stages.build_feedback(generate_result)
            stopped_at = spec14.STAGE_GENERATE
            continue
        if generate_result.status != spec14.STATUS_DONE:
            feedback = loop_stages.build_feedback(generate_result)
            stopped_at = spec14.STAGE_GENERATE
            continue

        final_files = generate_result.files or {}
        stopped_at = None

        yield _event(spec14.STAGE_LINT, iteration, spec14.STATUS_RUNNING)
        lint_result = loop_stages.run_lint(final_files)
        stages_log.append(_stage_log_entry(lint_result, iteration))
        yield _event_from_result(lint_result, iteration)
        if lint_result.status != spec14.STATUS_DONE:
            for message in lint_result.errors:
                lint_errors_log.append({"iteration": iteration, "message": message})
            feedback = loop_stages.build_feedback(lint_result)
            stopped_at = spec14.STAGE_LINT
            continue

        yield _event(spec14.STAGE_BUILD, iteration, spec14.STATUS_RUNNING)
        sandbox_ops.ensure(sandbox_root)
        sandbox_ops.reset(sandbox_root)
        sandbox_ops.install(sandbox_root, final_files)
        build_result = loop_stages.run_build(sandbox_root)
        stages_log.append(_stage_log_entry(build_result, iteration))
        yield _event_from_result(build_result, iteration)
        if build_result.status != spec14.STATUS_DONE:
            for message in build_result.errors:
                build_errors_log.append({"iteration": iteration, "message": message})
            feedback = loop_stages.build_feedback(build_result)
            stopped_at = spec14.STAGE_BUILD
            continue

        yield _event(spec14.STAGE_SECURITY, iteration, spec14.STATUS_RUNNING)
        security_result = loop_stages.run_security(_files_for_security_review(final_files), call_llm)
        _record_gateway_calls(gateway_calls, spec14.SOURCE_SECURITY_REVIEW, security_result)

        if security_result.raw_responses:
            artifact = _save_security_artifact(log_dir, run_id, iteration, security_result.raw_responses)
            security_result.artifact_path = artifact
            attempts_used = len(security_result.raw_responses)
            if security_result.status == spec14.STATUS_PARSE_ERROR:
                security_review_failed += 1
            elif attempts_used == 1:
                security_review_first_try += 1
            elif attempts_used == 2:
                security_review_rescued += 1
            security_malformed_blocks.append({"iteration": iteration, "count": security_result.malformed_block_count})
            if security_result.attempt_discrepancy:
                entry = dict(security_result.attempt_discrepancy)
                entry["iteration"] = iteration
                security_attempt_discrepancies.append(entry)

        stages_log.append(_stage_log_entry(security_result, iteration))
        if security_result.findings:
            all_findings.extend(security_result.findings)
        yield _event_from_result(security_result, iteration)

        if security_result.status in spec14.STAGE_HARD_STOP_STATUSES:
            # раздел 5.2, пункт 2: проверка не смогла прочитать свой ответ - это не ошибка
            # сгенерированного кода, GENERATE не зовём и итерацию не тратим, прогон стоп целиком
            stopped_at = spec14.STAGE_SECURITY
            break
        if security_result.status == spec14.STATUS_BLOCKED:
            gateway_blocks += 1
            feedback = loop_stages.build_feedback(security_result)
            stopped_at = spec14.STAGE_SECURITY
            continue
        if security_result.status != spec14.STATUS_DONE:
            feedback = loop_stages.build_feedback(security_result)
            stopped_at = spec14.STAGE_SECURITY
            continue

        yield _event(spec14.STAGE_COMMIT, iteration, spec14.STATUS_RUNNING)
        message = "loop %s iteration %d: %s" % (run_id, iteration, task[:80])
        commit_hash = sandbox_ops.commit(sandbox_root, message)
        commit_status = spec14.STATUS_DONE if commit_hash else spec14.STATUS_FAILED
        commit_result = loop_stages.StageResult(stage=spec14.STAGE_COMMIT, status=commit_status, commit=commit_hash)
        stages_log.append(_stage_log_entry(commit_result, iteration))
        yield _event_from_result(commit_result, iteration)
        stopped_at = None if commit_hash else spec14.STAGE_COMMIT
        break

    final_code_artifact = _save_final_code_artifact(log_dir, run_id, final_files)
    if not commit_hash:
        sandbox_ops.reset(sandbox_root)

    final_status = spec14.STATUS_DONE if commit_hash else spec14.STATUS_FAILED
    malformed_blocks_total = sum(entry["count"] for entry in security_malformed_blocks)
    lost_findings_total = sum(len(entry["lost_between_attempts"]) for entry in security_attempt_discrepancies)
    result_event: Dict[str, Any] = {
        "stage": spec14.STAGE_RESULT, "status": final_status, "iterations_used": iteration,
        "security_findings": len(all_findings), "gateway_blocks": gateway_blocks,
        "security_review_first_try": security_review_first_try,
        "security_review_rescued": security_review_rescued,
        "security_review_failed": security_review_failed,
        "security_malformed_blocks_total": malformed_blocks_total,
        "security_lost_findings_total": lost_findings_total,
        # run_id - тот же идентификатор, что ушёл шлюзу в X-Gateway-Run-Id на каждом вызове
        # (раздел 9): по нему прогон цикла сопоставляется с записями в журнале аудита шлюза.
        "run_id": run_id,
    }
    if stopped_at:
        result_event["stopped_at"] = stopped_at
    if final_files:
        # приложению - код целиком, в поток, не в журнал; журнал (ниже) видит только имена
        result_event["final_code"] = {os.path.basename(path): body for path, body in final_files.items()}
    yield result_event

    journal_out.update(loop_log.build_record(
        run_id=run_id, task=task, iterations_used=iteration, stopped_at=stopped_at,
        stages=stages_log, security_findings=[loop_stages.finding_to_dict(finding) for finding in all_findings],
        gateway_calls=gateway_calls, lint_errors=lint_errors_log, build_errors=build_errors_log,
        commit=commit_hash, final_files=sorted(final_files), final_code_artifact=final_code_artifact,
        security_review_first_try=security_review_first_try,
        security_review_rescued=security_review_rescued,
        security_review_failed=security_review_failed,
        security_malformed_blocks=security_malformed_blocks,
        security_attempt_discrepancies=security_attempt_discrepancies,
    ))


def execute_edit_run(task: str, source_file: str, call_llm, run_id: str,
                      log_dir: str, journal_out: Dict[str, Any]):
    """Режим правки существующего файла (POST /loop/run, поле source_file - расширение сверх
    раздела 8.2 контракта). Один проход GENERATE -> SECURITY, без LINT/BUILD/COMMIT.

    Почему без них: LINT/BUILD/COMMIT в этом харнессе рассчитаны на песочницу feature/loop_generated
    и её условный build.gradle.kts (sandbox.py) - у него нет реальных api/impl-связей с остальным
    проектом. Поднимать вместо этого настоящий модуль feature/ai со всеми его зависимостями - кратно
    дороже, а вопрос замера (перенесёт ли генератор строку маскировки заголовка при правке блока
    логирования, и заметит ли пропажу проверка безопасности) отвечается уже на паре GENERATE и
    SECURITY. Коммита в этом режиме нет никогда - раздел 12 и так запрещает писать в рабочее дерево
    REPO_ROOT, а песочницу трогать незачем, если сборка не нужна.
    """
    iteration = 1
    stages_log: List[Dict[str, Any]] = []
    gateway_calls: List[Dict[str, Any]] = []
    gateway_blocks = 0
    security_review_first_try = 0
    security_review_rescued = 0
    security_review_failed = 0
    security_malformed_blocks: List[Dict[str, Any]] = []
    security_attempt_discrepancies: List[Dict[str, Any]] = []
    all_findings: List[Any] = []
    final_files: Dict[str, str] = {}
    stopped_at: Optional[str] = None

    original_content = read_source_file(source_file)

    yield _event(spec14.STAGE_GENERATE, iteration, spec14.STATUS_RUNNING)
    generate_result = loop_stages.run_generate_edit(task, "", call_llm, source_file, original_content)
    stages_log.append(_stage_log_entry(generate_result, iteration))
    _record_gateway_calls(gateway_calls, spec14.SOURCE_CODEGEN, generate_result)
    yield _event_from_result(generate_result, iteration)

    if generate_result.status == spec14.STATUS_BLOCKED:
        gateway_blocks += 1
        stopped_at = spec14.STAGE_GENERATE
    elif generate_result.status != spec14.STATUS_DONE:
        stopped_at = spec14.STAGE_GENERATE
    else:
        # первый (и единственный ожидаемый) файл ответа - независимо от того, какой путь модель
        # написала в `// path:`, результат правки хранится и проверяется под исходным source_file
        _edited_path, edited_content = sorted(generate_result.files.items())[0]
        final_files = {source_file: edited_content}

        yield _event(spec14.STAGE_SECURITY, iteration, spec14.STATUS_RUNNING)
        security_result = loop_stages.run_security(final_files, call_llm)
        _record_gateway_calls(gateway_calls, spec14.SOURCE_SECURITY_REVIEW, security_result)

        if security_result.raw_responses:
            artifact = _save_security_artifact(log_dir, run_id, iteration, security_result.raw_responses)
            security_result.artifact_path = artifact
            attempts_used = len(security_result.raw_responses)
            if security_result.status == spec14.STATUS_PARSE_ERROR:
                security_review_failed += 1
            elif attempts_used == 1:
                security_review_first_try += 1
            elif attempts_used == 2:
                security_review_rescued += 1
            security_malformed_blocks.append({"iteration": iteration, "count": security_result.malformed_block_count})
            if security_result.attempt_discrepancy:
                entry = dict(security_result.attempt_discrepancy)
                entry["iteration"] = iteration
                security_attempt_discrepancies.append(entry)

        stages_log.append(_stage_log_entry(security_result, iteration))
        if security_result.findings:
            all_findings.extend(security_result.findings)
        yield _event_from_result(security_result, iteration)

        if security_result.status in spec14.STAGE_HARD_STOP_STATUSES:
            stopped_at = spec14.STAGE_SECURITY
        elif security_result.status == spec14.STATUS_BLOCKED:
            gateway_blocks += 1
            stopped_at = spec14.STAGE_SECURITY
        elif security_result.status != spec14.STATUS_DONE:
            # находки CRITICAL/HIGH - коммита в этом режиме всё равно нет, стадия просто отмечена
            # как место, на котором прогон встал, раздел 5 (возврат на генерацию) сюда не относится
            stopped_at = spec14.STAGE_SECURITY

    final_code_artifact = _save_final_code_artifact(log_dir, run_id, final_files)
    malformed_blocks_total = sum(entry["count"] for entry in security_malformed_blocks)
    lost_findings_total = sum(len(entry["lost_between_attempts"]) for entry in security_attempt_discrepancies)
    final_status = spec14.STATUS_DONE if stopped_at is None else spec14.STATUS_FAILED
    result_event: Dict[str, Any] = {
        "stage": spec14.STAGE_RESULT, "status": final_status, "iterations_used": iteration,
        "security_findings": len(all_findings), "gateway_blocks": gateway_blocks,
        "security_review_first_try": security_review_first_try,
        "security_review_rescued": security_review_rescued,
        "security_review_failed": security_review_failed,
        "security_malformed_blocks_total": malformed_blocks_total,
        "security_lost_findings_total": lost_findings_total,
        "run_id": run_id,
    }
    if stopped_at:
        result_event["stopped_at"] = stopped_at
    if final_files:
        result_event["final_code"] = {os.path.basename(path): body for path, body in final_files.items()}
    yield result_event

    journal_out.update(loop_log.build_record(
        run_id=run_id, task=task, iterations_used=iteration, stopped_at=stopped_at,
        stages=stages_log, security_findings=[loop_stages.finding_to_dict(finding) for finding in all_findings],
        gateway_calls=gateway_calls, lint_errors=[], build_errors=[],
        commit=None, final_files=sorted(final_files), final_code_artifact=final_code_artifact,
        security_review_first_try=security_review_first_try,
        security_review_rescued=security_review_rescued,
        security_review_failed=security_review_failed,
        security_malformed_blocks=security_malformed_blocks,
        security_attempt_discrepancies=security_attempt_discrepancies,
    ))
    journal_out["mode"] = "source_edit"
    journal_out["source_file"] = source_file


class LoopSettings:
    def __init__(self, gateway_url: str, max_iterations: int, sandbox_root: str, log_dir: str, timeout: int) -> None:
        self.gateway_url = gateway_url
        self.max_iterations = max_iterations
        self.sandbox_root = sandbox_root
        self.log = loop_log.LoopLog(log_dir)
        self.log_dir = log_dir
        self.timeout = timeout
        self.sandbox_lock = threading.Lock()


class LoopServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: Tuple[str, int], handler_class, settings: LoopSettings) -> None:
        self.settings = settings
        super().__init__(address, handler_class)


class LoopHandler(BaseHTTPRequestHandler):
    server_version = "LoopServer/1.0"
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
    def settings(self) -> LoopSettings:
        return self.server.settings

    def send_plain_json(self, status: int, payload: Dict[str, Any]) -> None:
        self.response_started = True
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", JSON_CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def start_stream(self) -> None:
        self.response_started = True
        self.send_response(200)
        self.send_header("Content-Type", SSE_CONTENT_TYPE)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        self.wfile.flush()

    def write_stream_bytes(self, data: bytes) -> None:
        self.wfile.write(b"%x\r\n" % len(data))
        self.wfile.write(data)
        self.wfile.write(b"\r\n")
        self.wfile.flush()

    def send_event(self, event: Dict[str, Any]) -> None:
        payload = "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
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
        if length > spec14.MAX_BODY_BYTES:
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
        if path == HISTORY_PATH:
            self.handle_history(urllib.parse.parse_qs(parsed.query))
            return
        self.send_plain_json(404, {"error": {"message": UNKNOWN_PATH_TEXT % path}})

    def handle_health(self) -> None:
        settings = self.settings
        self.send_plain_json(200, {
            "status": "ok",
            "gateway": settings.gateway_url,
            "max_iterations": settings.max_iterations,
            "sandbox": settings.sandbox_root,
            "sandbox_ready": os.path.isdir(os.path.join(settings.sandbox_root, ".git")),
            "log_dir": settings.log_dir,
            "ktlint": spec14.KTLINT_PATH,
            "ktlint_present": os.path.isfile(spec14.KTLINT_PATH),
        })

    def handle_history(self, query: Dict[str, List[str]]) -> None:
        raw_limit = (query.get("limit") or [str(spec14.DEFAULT_HISTORY_LIMIT)])[0]
        try:
            limit = int(raw_limit)
        except ValueError:
            limit = spec14.DEFAULT_HISTORY_LIMIT
        limit = max(1, min(limit, spec14.MAX_HISTORY_LIMIT))
        items = self.settings.log.tail(limit)
        self.send_plain_json(200, {"items": items, "count": len(items)})

    def do_POST(self) -> None:
        self.response_started = False
        path = normalized_path(self.path)
        body, read_error = self.read_body()
        if read_error is not None:
            self.close_connection = True
            self.send_plain_json(400, {"error": {"message": read_error}})
            return
        if path != RUN_PATH:
            self.send_plain_json(404, {"error": {"message": UNKNOWN_PATH_TEXT % path}})
            return
        try:
            self.handle_run(body)
        except Exception as unexpected_error:
            self.close_connection = True
            if self.response_started:
                return
            try:
                self.send_plain_json(500, {"error": {"message": str(unexpected_error)}})
            except Exception:
                return

    def handle_run(self, body: Optional[bytes]) -> None:
        try:
            payload = json.loads((body or b"").decode("utf-8", "replace") or "{}")
        except ValueError as parse_error:
            self.send_plain_json(400, {"error": {"message": BAD_BODY_TEXT % parse_error}})
            return
        if not isinstance(payload, dict):
            self.send_plain_json(400, {"error": {"message": BAD_BODY_TEXT % "тело не объект JSON"}})
            return

        task = payload.get("task")
        if not isinstance(task, str) or not task.strip():
            self.send_plain_json(400, {"error": {"message": MISSING_TASK_TEXT}})
            return
        if len(task) > spec14.MAX_TASK_CHARS:
            self.send_plain_json(400, {"error": {"message": TASK_TOO_LONG_TEXT}})
            return

        source_file = None
        raw_source_file = payload.get("source_file")
        if raw_source_file is not None:
            if not isinstance(raw_source_file, str) or not raw_source_file.strip():
                self.send_plain_json(400, {"error": {"message": SOURCE_FILE_EMPTY_TEXT}})
                return
            source_file, source_file_error = resolve_source_file(raw_source_file)
            if source_file_error is not None:
                self.send_plain_json(400, {"error": {"message": source_file_error}})
                return

        settings = self.settings
        requested = payload.get("max_iterations")
        max_iterations = settings.max_iterations
        if isinstance(requested, int) and requested > 0:
            max_iterations = min(requested, settings.max_iterations)

        run_id = new_run_id()
        call_llm = build_gateway_client(settings.gateway_url, settings.timeout, run_id)
        journal: Dict[str, Any] = {}
        self.start_stream()
        with settings.sandbox_lock:
            try:
                if source_file is not None:
                    event_source = execute_edit_run(
                        task.strip(), source_file, call_llm, run_id, settings.log_dir, journal,
                    )
                else:
                    event_source = execute_run(
                        task.strip(), max_iterations, call_llm, settings.sandbox_root,
                        run_id, settings.log_dir, journal,
                    )
                for event in event_source:
                    self.send_event(event)
            except OSError:
                self.close_connection = True
                return
        if journal:
            settings.log.write(journal)
        try:
            self.write_stream_bytes(b"data: [DONE]\n\n")
            self.end_stream()
        except OSError:
            self.close_connection = True


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Сервер цикла с проверкой безопасности (task14)")
    parser.add_argument("--host", default=spec14.LOOP_HOST)
    parser.add_argument("--port", type=int, default=spec14.LOOP_PORT)
    parser.add_argument("--gateway", default=spec14.GATEWAY_URL)
    parser.add_argument("--max-iterations", dest="max_iterations", type=int, default=spec14.DEFAULT_MAX_ITERATIONS)
    parser.add_argument("--sandbox", default=spec14.SANDBOX_DIR)
    parser.add_argument("--log-dir", dest="log_dir", default=spec14.LOOP_LOG_DIR)
    parser.add_argument("--timeout", type=int, default=spec14.GATEWAY_TIMEOUT_SECONDS)
    parser.add_argument("--task", default=spec14.EXAMPLE_TASKS[0], help="задача для --dry-run")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    return parser


def describe_plan(args: argparse.Namespace) -> List[str]:
    calls_per_iteration = 2
    worst_case_calls = calls_per_iteration * args.max_iterations
    tokens_in = estimate_tokens(loop_stages.GENERATE_SYSTEM_PROMPT + args.task) * args.max_iterations
    tokens_out = 900 * args.max_iterations
    tokens_in += 700 * args.max_iterations
    tokens_out += 400 * args.max_iterations
    worst_case_cost = compute_cost(tokens_in, tokens_out)
    return [
        "План прогона POST %s (без единого запроса к сети):" % RUN_PATH,
        "  задача: %s" % args.task,
        "  сервер цикла: http://%s:%d" % (args.host, args.port),
        "  шлюз: %s" % args.gateway,
        "  лимит итераций: %d" % args.max_iterations,
        "  песочница: %s" % args.sandbox,
        "  журнал: %s" % args.log_dir,
        "  ktlint: %s (есть: %s)" % (spec14.KTLINT_PATH, os.path.isfile(spec14.KTLINT_PATH)),
        "  худший случай вызовов модели: %d GENERATE + %d SECURITY = %d" % (
            args.max_iterations, args.max_iterations, worst_case_calls,
        ),
        "  грубая оценка стоимости худшего случая: $%.6f (тарифы task13/spec13, оценка по длине)" % worst_case_cost,
        "  запросов отправлено: 0",
    ]


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.dry_run:
        for line in describe_plan(args):
            write_log(line)
        return 0

    settings = LoopSettings(
        gateway_url=args.gateway, max_iterations=args.max_iterations,
        sandbox_root=args.sandbox, log_dir=args.log_dir, timeout=args.timeout,
    )
    server = LoopServer((args.host, args.port), LoopHandler, settings)
    write_log("Сервер цикла слушает http://%s:%d%s" % (args.host, args.port, RUN_PATH))
    write_log("Шлюз: %s" % settings.gateway_url)
    write_log("Лимит итераций: %d" % settings.max_iterations)
    write_log("Песочница: %s" % settings.sandbox_root)
    write_log("Журнал: %s" % settings.log_dir)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        write_log("Остановка по Ctrl+C")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
