"""Четыре стадии цикла: GENERATE, LINT, BUILD, SECURITY (LOOP_CONTRACT.md раздел 4).

Общая форма результата - StageResult: код стадии, итог, ошибки, длительность, плюс поля,
которые нужны конкретной стадии (файлы, находки, вердикт шлюза, сырой ответ). GENERATE и
SECURITY зовут переданный call_llm с разным source, LINT и BUILD работают только с диском/gradle
и модель не трогают.

SECURITY - три исхода, не два (раздел 5.1): находки есть (severity решает, провал это или нет),
находок нет (чисто), ответ не разобрался (SecurityReviewParseError - это провал стадии, а не
"находок нет", их нельзя путать). Здесь же отдельно проверяется, не заблокировал ли вызов сам
шлюз - это ещё один, независимый от разбора, вид провала.
"""

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import spec14

if spec14.TASK4_HARNESS_DIR not in sys.path:
    sys.path.insert(0, spec14.TASK4_HARNESS_DIR)

import codegen_lib
import sandbox as sandbox_ops
from security_review import SecurityFinding, SecurityReviewParseError, review_code
import security_review

CallLlm = Callable[[str, str, str], Any]

LINT_ERROR_LINE = re.compile(r"^<stdin>:(\d+):(\d+):\s*(.+)$")
COMPILER_ERROR_LINE = re.compile(r"^e: .*$", re.MULTILINE)

GENERATE_SYSTEM_PROMPT = (
    "Ты пишешь код для проекта AI-Chat-Advanced - чат с AI на Kotlin Multiplatform + Compose "
    "Multiplatform, таргеты Android и iOS. Трогаешь только один модуль: feature/loop_generated, "
    "пакет %s.\n\n"
    "Формат ответа:\n"
    "- каждый файл - отдельный блок ```kotlin;\n"
    "- первая строка блока: `// path: <путь>`;\n"
    "- путь всегда начинается с feature/loop_generated/src/androidMain/kotlin/ и продолжается "
    "пакетом %s;\n"
    "- дальше в блоке - полное содержимое файла без сокращений и без пояснений вне блоков кода.\n\n"
    "В androidMain доступны Android SDK целиком и уже подключённые библиотеки проекта: Ktor "
    "HttpClient (ktor-client-core, content-negotiation, kotlinx-serialization-json), "
    "kotlinx.coroutines, Koin (koin-core), androidx.security.crypto (EncryptedSharedPreferences), "
    "androidx.datastore.preferences, обычный android.content.SharedPreferences.\n\n"
    "Конвенции кода: internal по умолчанию, лямбды с именованными параметрами (без it), без "
    "!!, без Any, без magic numbers - именованные константы, без комментариев и KDoc.\n\n"
    "Дальше - задача от пользователя. Реши её кодом."
) % (spec14.SANDBOX_MODULE_PACKAGE, spec14.SANDBOX_MODULE_PACKAGE)

# Режим правки существующего файла - расширение сверх тройки демо-задач раздела 10 контракта
# (см. LOOP_CONTRACT.md раздел 10 и REPORT.md раздел 12: генератор с пустым модулем на входе не
# правит код, а выдумывает его заново, и задача "добавь логирование" ни разу не доходила до
# SECURITY). Здесь на вход идёт содержимое настоящего файла проекта целиком, а задача
# формулируется как его правка - модели есть что редактировать, а не что придумывать.
EDIT_SYSTEM_PROMPT_TEMPLATE = (
    "Ты правишь существующий файл проекта AI-Chat-Advanced - Kotlin Multiplatform + Compose "
    "Multiplatform чат с AI. Вот текущее содержимое файла %s целиком:\n\n"
    "```kotlin\n%s\n```\n\n"
    "Перепиши этот файл с учётом задачи пользователя. Ответ - один блок ```kotlin, первая строка "
    "`// path: %s`, дальше полное содержимое файла целиком, без сокращений и без пояснений вне "
    "блока кода.\n\n"
    "Конвенции кода: internal по умолчанию, лямбды с именованными параметрами (без it), без !!, "
    "без Any, без magic numbers, без комментариев и KDoc."
)


@dataclass
class StageResult:
    stage: str
    status: str
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    files: Optional[Dict[str, str]] = None
    findings: Optional[List[SecurityFinding]] = None
    gateway: Optional[Dict[str, Any]] = None
    gateway_attempts: List[Dict[str, Any]] = field(default_factory=list)
    commit: Optional[str] = None
    raw_response: str = ""
    raw_responses: List[str] = field(default_factory=list)
    artifact_path: Optional[str] = None
    malformed_block_count: int = 0
    attempt_discrepancy: Optional[Dict[str, Any]] = None


def _elapsed(started):
    return round(time.monotonic() - started, 3)


def _reasons_text(gateway):
    reasons = (gateway or {}).get("reasons") or []
    return "; ".join(reasons) if reasons else "без указанной причины"


def _blocking_verdict(gateway):
    if gateway and gateway.get("verdict") in spec14.GATEWAY_BLOCKING_VERDICTS:
        return gateway
    return None


def _first_blocking_verdict(gateway_list):
    for gateway in gateway_list:
        blocked = _blocking_verdict(gateway)
        if blocked is not None:
            return blocked
    return None


def _finding_key(finding):
    return (finding.file, finding.line)


def _attempt_discrepancy(raw_responses, merged_findings):
    """Раздел 5.3/5.4: итог review_code - объединение попыток, не находки победившей попытки.

    Проверяем это независимо от их слияния: разбираем каждый сырой ответ сами (parse_findings
    у них публичная) и сверяем с тем, что реально дошло в merged_findings. Если что-то нашлось
    хоть в одной попытке, но пропало из итога - это утечка находки между попытками, а не
    отсутствие проблемы. Не блокирует стадию сама по себе - только ложится в журнал (раздел 5.3,
    5.4: решение по гейту не моё, слияние - зона review_code, здесь только измерение).
    """
    if len(raw_responses) < 2:
        return None
    per_attempt = [security_review.parse_findings(text) for text in raw_responses]
    final_keys = {_finding_key(finding) for finding in merged_findings}
    lost = []
    seen = set()
    for attempt_findings in per_attempt:
        for finding in attempt_findings:
            key = _finding_key(finding)
            if key not in final_keys and key not in seen:
                seen.add(key)
                lost.append(finding)
    return {
        "attempts": [len(attempt_findings) for attempt_findings in per_attempt],
        "final": len(merged_findings),
        "lost_between_attempts": [finding_to_dict(finding) for finding in lost],
    }


def _run_generate_with_prompt(system_prompt, task, feedback, call_llm):
    started = time.monotonic()
    user_prompt = task if not feedback else "%s\n\n%s" % (task, feedback)
    text, gateway = call_llm(system_prompt, user_prompt, spec14.SOURCE_CODEGEN)

    gateway_attempts = [gateway] if gateway else []
    blocked = _blocking_verdict(gateway)
    if blocked is not None:
        return StageResult(
            stage=spec14.STAGE_GENERATE, status=spec14.STATUS_BLOCKED,
            errors=["шлюз заблокировал вызов генерации: " + _reasons_text(blocked)],
            duration_seconds=_elapsed(started), gateway=gateway, gateway_attempts=gateway_attempts,
            raw_response=text,
        )

    files = codegen_lib.parse_files(text)
    if not files:
        return StageResult(
            stage=spec14.STAGE_GENERATE, status=spec14.STATUS_FAILED,
            errors=["модель не вернула ни одного файла"],
            duration_seconds=_elapsed(started), gateway=gateway, gateway_attempts=gateway_attempts,
            raw_response=text,
        )
    return StageResult(
        stage=spec14.STAGE_GENERATE, status=spec14.STATUS_DONE, files=files,
        duration_seconds=_elapsed(started), gateway=gateway, gateway_attempts=gateway_attempts,
    )


def run_generate(task, feedback, call_llm):
    """Генерация с чистого листа: модель пишет код по задаче. Провал - ни одного файла в ответе."""
    return _run_generate_with_prompt(GENERATE_SYSTEM_PROMPT, task, feedback, call_llm)


def run_generate_edit(task, feedback, call_llm, source_path, original_content):
    """Генерация-правка: на вход идёт содержимое существующего файла, модель переписывает его
    целиком. Тот же критерий провала, что и у run_generate - разбор и исходы одинаковые."""
    system_prompt = EDIT_SYSTEM_PROMPT_TEMPLATE % (source_path, original_content, source_path)
    return _run_generate_with_prompt(system_prompt, task, feedback, call_llm)


def run_lint(files):
    """Линт: ktlint из системы через --stdin, по одному файлу. Провал - хоть одна ошибка стиля."""
    started = time.monotonic()
    errors = []
    kotlin_files = sorted(path for path in files if path.endswith((".kt", ".kts")))
    for path in kotlin_files:
        virtual_path = os.path.join(spec14.REPO_ROOT, path)
        try:
            result = subprocess.run(
                [spec14.KTLINT_PATH, "--stdin", "--stdin-path=%s" % virtual_path, "--log-level=none"],
                input=files[path], capture_output=True, text=True, timeout=spec14.KTLINT_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            errors.append("%s: ktlint не запустился: %s" % (path, error))
            continue
        if result.returncode == 0:
            continue
        for line in (result.stdout + result.stderr).splitlines():
            match = LINT_ERROR_LINE.match(line)
            if match:
                line_no, _column_no, message = match.groups()
                errors.append("%s Ln %s: %s" % (path, line_no, message))
    status = spec14.STATUS_DONE if not errors else spec14.STATUS_FAILED
    return StageResult(stage=spec14.STAGE_LINT, status=status, errors=errors, duration_seconds=_elapsed(started))


def run_build(sandbox_root):
    """Сборка: gradle в песочнице. Файлы туда кладёт вызывающая сторона до вызова этой функции."""
    started = time.monotonic()
    task = sandbox_ops.detect_build_task(sandbox_root)
    result = sandbox_ops.gradle(sandbox_root, ["%s:%s" % (spec14.SANDBOX_MODULE_GRADLE_PATH, task), "--offline"])
    output = result.stdout + result.stderr
    prefix = sandbox_root.rstrip("/") + "/"
    errors = [line.replace(prefix, "") for line in COMPILER_ERROR_LINE.findall(output)]
    status = spec14.STATUS_DONE if result.returncode == 0 else spec14.STATUS_FAILED
    return StageResult(stage=spec14.STAGE_BUILD, status=status, errors=errors, duration_seconds=_elapsed(started))


def _call_review_code(files, call_llm):
    """review_code отдаёт (SecurityFindings, raw_responses); SecurityFindings - list с довеском
    malformed_block_count (раздел 5.2: разбор поблочный, битый блок не роняет остальные находки,
    но и не исчезает молча - его число едет отдельно)."""
    findings, raw_responses = review_code(files, call_llm)
    malformed_block_count = getattr(findings, "malformed_block_count", 0)
    return list(findings), list(raw_responses), malformed_block_count


def run_security(files, call_llm):
    """Проверка безопасности: второй вызов модели, свой промпт (security_prompt.py).

    gateway_attempts копит вердикт шлюза КАЖДОГО вызова (их может быть два - review_code сам
    повторяет запрос при полностью нераспознанном ответе), а не только последнего - иначе первая
    попытка, которую шлюз заблокировал, потеряется из журнала, если вторая прошла.

    Три вида провала стадии (раздел 5.1, 5.2), не путать между собой:
    - STATUS_BLOCKED - шлюз не пустил вызов;
    - STATUS_PARSE_ERROR - ни один блок ответа не разобрался ни с одной попытки;
    - STATUS_PARTIAL_PARSE_ERROR - что-то разобралось, но не всё; в непрочитанном блоке мог
      быть Critical или High, коммит без него нечестен.
    Последние два не возвращают цикл на GENERATE (раздел 5.2, пункт 2) - это не ошибка
    сгенерированного кода, и жечь на неё бюджет итераций незачем. Их останавливает вызывающая
    сторона (loop_server.execute_run), не эта функция - run_security только сообщает статус.
    """
    started = time.monotonic()
    attempts: List[Optional[Dict[str, Any]]] = []

    def recording_call_llm(system, user, source):
        text, gateway = call_llm(system, user, source)
        attempts.append(gateway)
        return text, gateway

    try:
        findings, raw_responses, malformed_block_count = _call_review_code(files, recording_call_llm)
    except SecurityReviewParseError as error:
        gateway_attempts = list(error.gateway_verdicts)
        blocked = _first_blocking_verdict(gateway_attempts)
        last_gateway = gateway_attempts[-1] if gateway_attempts else None
        discrepancy = _attempt_discrepancy(list(error.raw_responses), [])
        if blocked is not None:
            return StageResult(
                stage=spec14.STAGE_SECURITY, status=spec14.STATUS_BLOCKED,
                errors=["шлюз заблокировал вызов проверки безопасности: " + _reasons_text(blocked)],
                duration_seconds=_elapsed(started), gateway=blocked, gateway_attempts=gateway_attempts,
                raw_responses=list(error.raw_responses), attempt_discrepancy=discrepancy,
            )
        return StageResult(
            stage=spec14.STAGE_SECURITY, status=spec14.STATUS_PARSE_ERROR,
            errors=["ответ проверки безопасности не разобрался ни с первой, ни со второй попытки"],
            duration_seconds=_elapsed(started), gateway=last_gateway, gateway_attempts=gateway_attempts,
            raw_responses=list(error.raw_responses), attempt_discrepancy=discrepancy,
        )

    gateway_attempts = attempts
    gateway = gateway_attempts[-1] if gateway_attempts else None
    discrepancy = _attempt_discrepancy(raw_responses, findings)
    blocked = _first_blocking_verdict(gateway_attempts)
    if blocked is not None:
        return StageResult(
            stage=spec14.STAGE_SECURITY, status=spec14.STATUS_BLOCKED,
            errors=["шлюз заблокировал вызов проверки безопасности: " + _reasons_text(blocked)],
            duration_seconds=_elapsed(started), gateway=gateway, gateway_attempts=gateway_attempts,
            raw_responses=raw_responses, attempt_discrepancy=discrepancy,
        )

    if malformed_block_count > 0:
        return StageResult(
            stage=spec14.STAGE_SECURITY, status=spec14.STATUS_PARTIAL_PARSE_ERROR,
            errors=[
                "часть ответа проверки безопасности не разобралась: битых блоков %d - в "
                "любом из них мог быть Critical или High, коммит без них давать нельзя"
                % malformed_block_count
            ],
            duration_seconds=_elapsed(started), gateway=gateway, gateway_attempts=gateway_attempts,
            findings=findings, raw_responses=raw_responses, malformed_block_count=malformed_block_count,
            attempt_discrepancy=discrepancy,
        )

    blocking_findings = [finding for finding in findings if finding.severity in spec14.BLOCKING_SEVERITIES]
    status = spec14.STATUS_FAILED if blocking_findings else spec14.STATUS_DONE
    return StageResult(
        stage=spec14.STAGE_SECURITY, status=status, findings=findings,
        duration_seconds=_elapsed(started), gateway=gateway, gateway_attempts=gateway_attempts,
        raw_responses=raw_responses, malformed_block_count=malformed_block_count,
        attempt_discrepancy=discrepancy,
    )


def finding_to_dict(finding):
    return {
        "severity": finding.severity,
        "file": finding.file,
        "line": finding.line,
        "title": finding.title,
        "fix": finding.fix,
    }


def build_feedback(result):
    """Текст фидбека для следующего GENERATE - разный на каждую стадию и на каждый исход."""
    if result.stage == spec14.STAGE_GENERATE:
        if result.status == spec14.STATUS_BLOCKED:
            return (
                "Шлюз заблокировал прошлый вызов генерации: %s. Перепиши задачу без этого "
                "содержимого и ответь снова." % _reasons_text(result.gateway)
            )
        return (
            "Прошлый ответ не удалось разобрать ни на один файл кода. Строго держись формата: "
            "блок ```kotlin, первая строка `// path: <путь>`, дальше полный код файла без "
            "сокращений."
        )
    if result.stage == spec14.STAGE_LINT:
        return "Код не прошёл ktlint. Построчные ошибки стиля:\n" + "\n".join(result.errors)
    if result.stage == spec14.STAGE_BUILD:
        return "Код не собрался gradle. Ошибки компилятора:\n" + "\n".join(result.errors)
    if result.stage == spec14.STAGE_SECURITY:
        if result.status == spec14.STATUS_BLOCKED:
            return (
                "Шлюз заблокировал вызов проверки безопасности: %s. Перепиши задачу без этого "
                "содержимого и ответь снова." % _reasons_text(result.gateway)
            )
        if result.status in spec14.STAGE_HARD_STOP_STATUSES:
            return (
                "Проверка безопасности не смогла до конца разобрать собственный ответ - это "
                "техническая ошибка самой проверки, а не твоего кода. Пришли тот же код ещё раз "
                "без изменений по смыслу."
            )
        blocking_findings = [finding for finding in (result.findings or []) if finding.severity in spec14.BLOCKING_SEVERITIES]
        return security_review.build_feedback(blocking_findings)
    return "Предыдущая попытка не прошла проверку."
