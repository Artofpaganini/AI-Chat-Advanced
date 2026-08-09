"""Второй вызов модели - проверка сгенерированного кода на безопасность.

Строит запрос из промпта security_prompt.py и пронумерованного кода, зовёт модель через
call_llm с source="security_review" (LOOP_CONTRACT.md раздел 9), разбирает ответ строго по
формату оттуда же.

У стадии три исхода (раздел 5.1): находки есть, находок нет, ответ не разобран.
SecurityReviewParseError значит "проверка не смогла ответить" - провал стадии, а не находки.

Раздел 5.2: неразобранный блок - находка неизвестного уровня, а неизвестный уровень при такой
цене ошибки трактуется как высокий. Любой битый блок на попытке - даже один среди четырёх
верных - форсирует повтор ПРОВЕРКИ (не генерации). Если и повтор оставляет битые блоки - стадия
провалена.

Раздел 5.3: попытки СЛИВАЮТСЯ, а не заменяют друг друга. Если первая попытка не была чистой
(были битые блоки) и потому потребовала повтора, а повтор пришёл чистым - результат не
"находки второй попытки", а ОБЪЕДИНЕНИЕ находок первой и второй. Модель недетерминирована,
вторая попытка не обязана быть надмножеством первой: выброшенный CRITICAL первой попытки не
восстановить, если строку и без него сочли успехом.

Ключ склейки - тройка (file, line, title), НЕ (file, line): на одной строке может быть два
разных дефекта (например отсутствие валидации входа и утечка в лог одного и того же вызова),
и склейка только по строке взяла бы уровень от одной находки, а совет - от другой, теряя вторую
молча. Совпали все три поля - один дефект, найденный дважды, берём строгий уровень при
расхождении. Различаются названия - две находки, остаются обе: лишний дубль дёшев (вернёт цикл
на генерацию), потерянная находка уходит в коммит.

Раздел 5.4: находки атрибутируются по попыткам - found_on_attempts на итоговом SecurityFindings,
параллельно самому списку. Найдено с первого раза и найдено только со второго после
напоминания о формате - разные результаты по надёжности, хоть и оба засчитываются.

review_code возвращает Tuple[List[SecurityFinding], List[str]] - второй элемент это сырые
ответы модели по каждой сделанной попытке: один элемент, если первая попытка была чистой, два,
если понадобился и спас повтор. По длине этого списка вызывающий код считает долю прогонов с
повтором (раздел 5.4) - метрика для отчёта отдельной строкой, каждый повтор удваивает стоимость
стадии.

Первый элемент кортежа - не голый list, а SecurityFindings: ведёт себя как обычный
List[SecurityFinding] (итерация, len, индексация), но довешивает malformed_block_counts (по
попытке, длины 1 или 2 - НЕ суммарно), count_per_attempt (сколько находок дала каждая попытка
ДО объединения - длина после объединения это просто len(self)), findings_per_attempt (САМИ
находки каждой попытки до объединения, не только их число - без этого нельзя постфактум
проверить, что именно схлопнулось: числа есть, содержимого нет, и потерю от склейки спишут на
слепоту проверки, которой не было), found_on_attempts (с каких попыток взялась итоговая находка,
параллельно самому списку) и gateway_verdicts.
"""

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from security_prompt import (
    FIELD_FILE,
    FIELD_FIX,
    FIELD_LINE,
    FIELD_SEVERITY,
    FIELD_TITLE,
    FINDING_SEPARATOR,
    NO_FINDINGS_MARKER,
    SECURITY_REVIEW_FORMAT_REMINDER,
    SECURITY_REVIEW_SYSTEM_PROMPT,
    SEVERITY_LEVELS,
    SOURCE_SECURITY_REVIEW,
)

CallLlm = Callable[[str, str, str], Tuple[str, dict]]

_SEVERITY_RANK = {severity: rank for rank, severity in enumerate(SEVERITY_LEVELS)}


@dataclass
class SecurityFinding:
    severity: str
    file: str
    line: int
    title: str
    fix: str


class SecurityFindings(list):
    """List[SecurityFinding] с метаданными разбора, по одной записи на попытку в списках.

    Ведёт себя как обычный list - итерация, len, индексация и сравнение по содержимому не
    отличаются от plain list, весь код, ожидающий List[SecurityFinding], работает без правок.

    malformed_block_counts - битые блоки, по попытке (не суммарно): [3, 0] - разовая осечка,
    [3, 3] - промпт нестабилен по формату. count_per_attempt - сколько находок распознала
    каждая попытка ДО объединения (раздел 5.3); после объединения находок может быть меньше
    (дубликаты схлопнулись) - итоговое число это len(self). findings_per_attempt - САМИ находки
    каждой попытки до объединения (список списков SecurityFinding, длина - число попыток) -
    без них проверить постфактум, что именно схлопнулось, нечем: числа есть, содержимого нет.
    found_on_attempts - параллельно self, кортеж номеров попыток (1-based), на которых
    встретилась именно эта находка после объединения (раздел 5.4). gateway_verdicts - вердикт
    шлюза по каждой попытке.
    """

    def __init__(
        self,
        findings: List[SecurityFinding],
        malformed_block_counts: Optional[List[int]] = None,
        count_per_attempt: Optional[List[int]] = None,
        findings_per_attempt: Optional[List[List[SecurityFinding]]] = None,
        found_on_attempts: Optional[List[Tuple[int, ...]]] = None,
        gateway_verdicts: Optional[List[dict]] = None,
    ) -> None:
        super().__init__(findings)
        self.malformed_block_counts = list(malformed_block_counts) if malformed_block_counts else []
        self.count_per_attempt = list(count_per_attempt) if count_per_attempt else []
        self.findings_per_attempt = list(findings_per_attempt) if findings_per_attempt else []
        self.found_on_attempts = list(found_on_attempts) if found_on_attempts else []
        self.gateway_verdicts = list(gateway_verdicts) if gateway_verdicts else []


class SecurityReviewParseError(Exception):
    """Стадия провалена: после двух попыток в ответе остались неразобранные блоки.

    Неразобранный блок - находка неизвестного уровня (раздел 5.2), она не отбрасывается тихо и
    не приравнивается к "находок нет": коммита при этом исходе нет, даже если часть блоков
    распознана и часть findings нашлась.

    raw_responses, gateway_verdicts, malformed_block_counts - всегда длины 2, ПО ПОПЫТКАМ, не
    суммарно. partial_findings - находки, которые всё же разобрались на каждой попытке (список
    списков, по одному на попытку, может быть пустым) - НЕ объединены между собой (раздел 5.3
    про объединение говорит об успешном исходе; здесь стадия провалена, и выдавать за неё один
    "итоговый" список означало бы подать недостоверный результат как достоверный).
    """

    def __init__(
        self,
        raw_responses: List[str],
        gateway_verdicts: List[dict],
        malformed_block_counts: List[int],
        partial_findings: List[List[SecurityFinding]],
    ) -> None:
        self.raw_responses = raw_responses
        self.gateway_verdicts = gateway_verdicts
        self.malformed_block_counts = malformed_block_counts
        self.partial_findings = partial_findings
        super().__init__(
            "security review left unparsed blocks after %d attempt(s), malformed per attempt: %s"
            % (len(raw_responses), malformed_block_counts)
        )


_FIELD_PATTERN = re.compile(
    r"^%s:[ \t]*(?P<severity>\S+)[ \t]*\n"
    r"%s:[ \t]*(?P<file>[^\n]+?)[ \t]*\n"
    r"%s:[ \t]*(?P<line>\d+)[ \t]*\n"
    r"%s:[ \t]*(?P<title>[^\n]+?)[ \t]*\n"
    r"%s:[ \t]*(?P<fix>[^\n]+?)[ \t]*$"
    % (FIELD_SEVERITY, FIELD_FILE, FIELD_LINE, FIELD_TITLE, FIELD_FIX),
    re.MULTILINE,
)

_SEPARATOR_PATTERN = re.compile(r"(?m)^[ \t]*%s[ \t]*$\n?" % re.escape(FINDING_SEPARATOR))


def parse_findings(raw_response: str) -> SecurityFindings:
    """Построчный разбор ОДНОЙ попытки по блокам. Битый блок пропускается, а не роняет ответ.

    malformed_block_counts - всегда список длины 1 здесь (одна попытка = один разбор). Пустой
    ответ и нераспознанный текст без единого блока - тоже malformed_block_counts == [1], не
    отдельный случай. review_code решает по этому числу, нужен ли повтор - не эта функция.
    """
    text = raw_response.strip()
    if text == NO_FINDINGS_MARKER:
        return SecurityFindings([], malformed_block_counts=[0])
    if not text:
        return SecurityFindings([], malformed_block_counts=[1])

    findings: List[SecurityFinding] = []
    malformed_block_count = 0
    for block in (piece.strip() for piece in _SEPARATOR_PATTERN.split(text)):
        finding = _parse_block(block)
        if finding is None:
            malformed_block_count += 1
        else:
            findings.append(finding)
    return SecurityFindings(findings, malformed_block_counts=[malformed_block_count])


def _parse_block(block: str) -> Optional[SecurityFinding]:
    if not block:
        return None
    match = _FIELD_PATTERN.fullmatch(block)
    if match is None:
        return None
    severity = match.group("severity").strip().upper()
    if severity not in SEVERITY_LEVELS:
        return None
    file_name = match.group("file").strip()
    title = match.group("title").strip()
    fix = match.group("fix").strip()
    if not file_name or not title or not fix:
        return None
    try:
        line_number = int(match.group("line"))
    except ValueError:
        return None
    if line_number <= 0:
        return None
    return SecurityFinding(severity=severity, file=file_name, line=line_number, title=title, fix=fix)


def _normalized_title(title: str) -> str:
    """Регистр и пробелы не должны разваливать сравнение названий - смысл важнее форматирования."""
    return " ".join(title.casefold().split())


def _merge_findings_by_attempt(
    findings_by_attempt: List[List[SecurityFinding]],
) -> Tuple[List[SecurityFinding], List[Tuple[int, ...]]]:
    """Объединение находок нескольких попыток в одну (раздел 5.3), с атрибуцией (раздел 5.4).

    Дубликаты схлопываются по тройке (file, line, нормализованное title), НЕ по (file, line): на
    одной строке может быть два разных дефекта (например отсутствие валидации входа и утечка в
    лог одного и того же вызова) - склейка только по строке взяла бы уровень от одной находки, а
    совет от другой, теряя вторую молча. При совпадении всех трёх полей - это один дефект,
    найденный дважды, берётся более строгий severity. При разных названиях на одной строке -
    это две находки, обе остаются: лишний дубль дешевле пропуска (раздел 5.3).

    Возвращает объединённый список в порядке первого появления и параллельный список кортежей
    - номера попыток (1-based), на которых встретилась итоговая находка.
    """
    Key = Tuple[str, int, str]
    order: List[Key] = []
    kept: Dict[Key, SecurityFinding] = {}
    attempts_seen: Dict[Key, List[int]] = {}

    for attempt_number, findings in enumerate(findings_by_attempt, start=1):
        for finding in findings:
            key = (finding.file, finding.line, _normalized_title(finding.title))
            if key not in kept:
                order.append(key)
                kept[key] = finding
                attempts_seen[key] = [attempt_number]
                continue
            attempts_seen[key].append(attempt_number)
            if _SEVERITY_RANK[finding.severity] < _SEVERITY_RANK[kept[key].severity]:
                kept[key] = finding

    merged = [kept[key] for key in order]
    found_on = [tuple(sorted(set(attempts_seen[key]))) for key in order]
    return merged, found_on


def _numbered_file_block(file_name: str, content: str) -> str:
    lines = content.splitlines()
    numbered = "\n".join("%d: %s" % (index, line) for index, line in enumerate(lines, start=1))
    return "Файл: %s\n%s" % (file_name, numbered)


def build_user_message(files: Dict[str, str]) -> str:
    return "\n\n".join(_numbered_file_block(name, files[name]) for name in sorted(files))


ReviewResult = Tuple[List[SecurityFinding], List[str]]


def _finalize(
    findings_by_attempt: List[List[SecurityFinding]],
    malformed_block_counts: List[int],
    gateway_verdicts: List[dict],
) -> SecurityFindings:
    merged, found_on = _merge_findings_by_attempt(findings_by_attempt)
    return SecurityFindings(
        merged,
        malformed_block_counts=malformed_block_counts,
        count_per_attempt=[len(findings) for findings in findings_by_attempt],
        findings_per_attempt=findings_by_attempt,
        found_on_attempts=found_on,
        gateway_verdicts=gateway_verdicts,
    )


def review_code(files: Dict[str, str], call_llm: CallLlm) -> ReviewResult:
    if not files:
        return SecurityFindings([]), []

    user_message = build_user_message(files)
    raw_response_1, gateway_verdict_1 = call_llm(
        SECURITY_REVIEW_SYSTEM_PROMPT, user_message, SOURCE_SECURITY_REVIEW
    )
    parsed_1 = parse_findings(raw_response_1)
    malformed_1 = parsed_1.malformed_block_counts[0]

    if malformed_1 == 0:
        result = _finalize([list(parsed_1)], [malformed_1], [gateway_verdict_1])
        return result, [raw_response_1]

    retry_message = SECURITY_REVIEW_FORMAT_REMINDER + "\n\n" + user_message
    raw_response_2, gateway_verdict_2 = call_llm(
        SECURITY_REVIEW_SYSTEM_PROMPT, retry_message, SOURCE_SECURITY_REVIEW
    )
    parsed_2 = parse_findings(raw_response_2)
    malformed_2 = parsed_2.malformed_block_counts[0]

    if malformed_2 == 0:
        result = _finalize(
            [list(parsed_1), list(parsed_2)],
            [malformed_1, malformed_2],
            [gateway_verdict_1, gateway_verdict_2],
        )
        return result, [raw_response_1, raw_response_2]

    raise SecurityReviewParseError(
        raw_responses=[raw_response_1, raw_response_2],
        gateway_verdicts=[gateway_verdict_1, gateway_verdict_2],
        malformed_block_counts=[malformed_1, malformed_2],
        partial_findings=[list(parsed_1), list(parsed_2)],
    )


def build_feedback(findings: List[SecurityFinding]) -> str:
    if not findings:
        return ""
    lines = ["Проверка безопасности нашла проблемы, их нужно исправить перед коммитом:"]
    for finding in findings:
        lines.append(
            "[%s] %s:%d - %s. Исправление: %s"
            % (finding.severity, finding.file, finding.line, finding.title, finding.fix)
        )
    return "\n".join(lines)
