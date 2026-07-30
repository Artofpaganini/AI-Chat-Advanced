"""Два варианта инференса триажа: монолит одним вызовом и цепочка из трёх этапов.

Монолит - точка отсчёта task7: один вызов, JSON из пяти полей, проверка guards.check_reply.
Цепочка - контракт SPEC раздел 3: разбор фактов, решение по фактам, текст родителю.

Разбор обоих компактных форматов устойчивый: ключи ищутся по всему тексту, поэтому переносы
строк, лишние пробелы, разделитель | и markdown-забор ответ не ломают.

Два разных понятия отказа, их не надо путать:
- violations - что нарушено в формате ответа этапа, отсюда метрика stage_failures;
- ok - дал ли этап пригодный результат, отсюда failed_stage и таблица «где ломается».
Этап 1, назвавший маршрут, пригодный результат всё же дал: факты берутся, а S1_ROUTE_LEAKED
записывается в violations и виден в отчёте отдельной строкой.

Отказоустойчивость по контракту: мусор на этапе 1 -> этап 2 получает пустые факты; мусор на
этапе 2 -> маршрут None, этап 3 не зовётся вовсе и ответ берётся из spec7.FALLBACK_ANSWER;
пустой ответ этапа 3 -> та же заглушка.
"""

import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import stages_spec

sys.path.insert(0, stages_spec.TASK7_HARNESS_DIR)

import guards
import guards_v2
import llm_client
import pipeline
import spec7

NONE_ALIASES = (
    "none",
    "нет",
    "-",
    "--",
    "null",
    "n/a",
    "не указано",
    "не указан",
    "не указана",
    "неизвестно",
    "отсутствует",
)

STAGE1_KEY_PATTERN = re.compile(
    r"(?<![A-Za-z_])(%s)\s*[=:]"
    % "|".join(sorted(stages_spec.STAGE1_ALL_FIELDS, key=len, reverse=True)),
    re.IGNORECASE,
)
STAGE2_KEY_PATTERN = re.compile(
    r"(?<![A-Za-z_])(%s)\s*[=:]" % "|".join(stages_spec.STAGE2_FIELDS), re.IGNORECASE
)
LEAK_PATTERN = re.compile(
    r"(?<![A-Za-z_])(%s)(?![A-Za-z_])" % "|".join(stages_spec.LEAK_TOKENS), re.IGNORECASE
)
INTEGER_PATTERN = re.compile(r"-?\d+")
NUMBER_PATTERN = re.compile(r"-?\d+(?:[.,]\d+)?")
WORD_PATTERN = re.compile(r"[A-Za-z_]+")
VALUE_TAIL_CHARS = " \t\r\n|,.;*`\"'"


@dataclass
class StageResult:
    stage: str
    raw_text: str = ""
    parsed: Dict[str, Any] = field(default_factory=dict)
    ok: bool = False
    violations: List[str] = field(default_factory=list)
    latency_ms: int = 0
    usage: Dict[str, int] = field(default_factory=llm_client.empty_usage)
    cost_usd: float = 0.0
    model: str = ""


@dataclass
class MultiStageDecision:
    case_id: str
    mode: str
    route: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""
    answer_text: str = ""
    stages: List[StageResult] = field(default_factory=list)
    total_latency_ms: int = 0
    total_cost_usd: float = 0.0
    calls: int = 0
    failed_stage: Optional[str] = None
    error: Optional[str] = None


def empty_facts(with_context: bool = False) -> Dict[str, Any]:
    facts: Dict[str, Any] = {
        stages_spec.F_AGE: None,
        stages_spec.F_SYMPTOMS: [],
        stages_spec.F_METRICS: stages_spec.NONE_VALUE,
        stages_spec.F_DURATION: stages_spec.NONE_VALUE,
        stages_spec.F_PARENT_STATE: stages_spec.NONE_VALUE,
        stages_spec.F_QUESTION_TYPE: stages_spec.QT_OTHER,
    }
    if with_context:
        facts[stages_spec.F_CONTEXT_AGE] = None
    return facts


def known_age(facts: Dict[str, Any]) -> Optional[int]:
    age = facts.get(stages_spec.F_AGE)
    if isinstance(age, int):
        return age
    context_age = facts.get(stages_spec.F_CONTEXT_AGE)
    if isinstance(context_age, int):
        return context_age
    return None


def clip_history(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    recent = [
        message
        for message in messages
        if str(message.get("role")) in stages_spec.HISTORY_ROLES
        and str(message.get("content") or "").strip()
    ][-stages_spec.HISTORY_MAX_MESSAGES :]
    total = 0
    kept: List[Dict[str, str]] = []
    for message in reversed(recent):
        length = len(str(message.get("content") or ""))
        if kept and total + length > stages_spec.HISTORY_MAX_CHARS:
            break
        total += length
        kept.append(message)
    kept.reverse()
    return kept


def format_conversation(messages: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for message in messages:
        role = stages_spec.HISTORY_ROLE_TITLES.get(
            str(message.get("role")), stages_spec.HISTORY_ROLE_USER
        )
        text = " ".join(str(message.get("content") or "").split())
        lines.append(stages_spec.HISTORY_LINE % (role, text))
    return "\n".join(lines)


def is_none_value(value: str) -> bool:
    return value.strip().strip(VALUE_TAIL_CHARS).lower() in NONE_ALIASES


def clean_value(value: str) -> str:
    return value.strip().strip(VALUE_TAIL_CHARS).strip()


def clip_value(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]


def collect_pairs(text: str, pattern: re.Pattern) -> Dict[str, str]:
    matches = list(pattern.finditer(text))
    pairs: Dict[str, str] = {}
    for position, match in enumerate(matches):
        start = match.end()
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        key = match.group(1).upper()
        pairs[key] = text[start:end]
    return pairs


def parse_age(value: Optional[str]) -> Tuple[Optional[int], bool]:
    if value is None or is_none_value(value):
        return None, False
    match = INTEGER_PATTERN.search(value)
    if match is None:
        return None, False
    age = int(match.group(0))
    if age < stages_spec.MIN_AGE_MONTHS or age > stages_spec.MAX_AGE_MONTHS:
        return None, True
    return age, False


def parse_symptoms(value: Optional[str]) -> List[str]:
    if value is None or is_none_value(value):
        return []
    parts = [clean_value(part) for part in value.split(stages_spec.SYMPTOM_SEPARATOR)]
    symptoms = [
        clip_value(part, stages_spec.MAX_SYMPTOM_CHARS)
        for part in parts
        if part and not is_none_value(part)
    ]
    return symptoms[: stages_spec.MAX_SYMPTOMS]


def parse_free_field(value: Optional[str], limit: int) -> str:
    if value is None or is_none_value(value):
        return stages_spec.NONE_VALUE
    cleaned = " ".join(clean_value(value).split())
    if not cleaned:
        return stages_spec.NONE_VALUE
    return clip_value(cleaned, limit)


def parse_question_type(value: Optional[str]) -> Tuple[str, bool]:
    if value is None:
        return stages_spec.QT_OTHER, True
    match = WORD_PATTERN.search(value)
    if match is None:
        return stages_spec.QT_OTHER, True
    candidate = match.group(0).upper()
    if candidate not in stages_spec.QUESTION_TYPES:
        return stages_spec.QT_OTHER, True
    return candidate, False


def route_leaked(raw_text: str) -> bool:
    return LEAK_PATTERN.search(raw_text or "") is not None


def parse_stage1(raw: str, with_context: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    violations: List[str] = []
    text, _fenced = guards.strip_code_fence(raw or "")
    if route_leaked(raw or ""):
        violations.append(stages_spec.S1_ROUTE_LEAKED)
    pairs = collect_pairs(text, STAGE1_KEY_PATTERN)
    facts = empty_facts(with_context)
    if not pairs:
        violations.append(stages_spec.S1_PARSE)
        return facts, violations
    required = (
        stages_spec.STAGE1_CONVERSATION_FIELDS if with_context else stages_spec.STAGE1_FIELDS
    )
    broken = [name for name in required if name not in pairs]
    age, age_out_of_range = parse_age(pairs.get(stages_spec.F_AGE))
    question_type, question_type_broken = parse_question_type(
        pairs.get(stages_spec.F_QUESTION_TYPE)
    )
    facts[stages_spec.F_AGE] = age
    facts[stages_spec.F_SYMPTOMS] = parse_symptoms(pairs.get(stages_spec.F_SYMPTOMS))
    facts[stages_spec.F_METRICS] = parse_free_field(
        pairs.get(stages_spec.F_METRICS), stages_spec.MAX_METRICS_CHARS
    )
    facts[stages_spec.F_DURATION] = parse_free_field(
        pairs.get(stages_spec.F_DURATION), stages_spec.MAX_DURATION_CHARS
    )
    facts[stages_spec.F_PARENT_STATE] = parse_free_field(
        pairs.get(stages_spec.F_PARENT_STATE), stages_spec.MAX_PARENT_STATE_CHARS
    )
    facts[stages_spec.F_QUESTION_TYPE] = question_type
    context_out_of_range = False
    if with_context or stages_spec.F_CONTEXT_AGE in pairs:
        context_age, context_out_of_range = parse_age(pairs.get(stages_spec.F_CONTEXT_AGE))
        facts[stages_spec.F_CONTEXT_AGE] = context_age
    if broken or age_out_of_range or question_type_broken or context_out_of_range:
        violations.append(stages_spec.S1_PARSE)
    return facts, violations


def parse_confidence(value: Optional[str]) -> Tuple[float, bool]:
    if value is None:
        return 0.0, True
    match = NUMBER_PATTERN.search(value)
    if match is None:
        return 0.0, True
    number = float(match.group(0).replace(",", "."))
    if number < stages_spec.MIN_CONFIDENCE or number > stages_spec.MAX_CONFIDENCE:
        return min(max(number, stages_spec.MIN_CONFIDENCE), stages_spec.MAX_CONFIDENCE), True
    return number, False


def parse_route_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    match = LEAK_PATTERN.search(value)
    if match is None:
        return None
    return match.group(1).upper()


def parse_stage2(raw: str) -> Tuple[Dict[str, Any], List[str]]:
    violations: List[str] = []
    text, _fenced = guards.strip_code_fence(raw or "")
    pairs = collect_pairs(text, STAGE2_KEY_PATTERN)
    route = parse_route_value(pairs.get(stages_spec.D_ROUTE))
    if route is None:
        route = parse_route_value(text)
        if route is not None:
            violations.append(stages_spec.S2_PARSE)
    confidence, confidence_broken = parse_confidence(pairs.get(stages_spec.D_CONFIDENCE))
    why = parse_free_field(pairs.get(stages_spec.D_WHY), stages_spec.MAX_WHY_CHARS)
    if why == stages_spec.NONE_VALUE:
        why = ""
    parsed = {
        stages_spec.D_ROUTE: route,
        stages_spec.D_CONFIDENCE: round(confidence, 4),
        stages_spec.D_WHY: why,
    }
    if route is None or confidence_broken or stages_spec.D_WHY not in pairs:
        if stages_spec.S2_PARSE not in violations:
            violations.append(stages_spec.S2_PARSE)
    return parsed, violations


def format_facts(facts: Dict[str, Any]) -> str:
    age = facts.get(stages_spec.F_AGE)
    symptoms = facts.get(stages_spec.F_SYMPTOMS) or []
    lines = [
        "%s%s%s"
        % (
            stages_spec.F_AGE,
            stages_spec.PAIR_SEPARATOR,
            stages_spec.NONE_VALUE if age is None else age,
        ),
        "%s%s%s"
        % (
            stages_spec.F_SYMPTOMS,
            stages_spec.PAIR_SEPARATOR,
            stages_spec.SYMPTOM_SEPARATOR.join(symptoms) if symptoms else stages_spec.NONE_VALUE,
        ),
    ]
    for name in (stages_spec.F_METRICS, stages_spec.F_DURATION, stages_spec.F_PARENT_STATE):
        value = facts.get(name) or stages_spec.NONE_VALUE
        lines.append("%s%s%s" % (name, stages_spec.PAIR_SEPARATOR, value))
    lines.append(
        "%s%s%s"
        % (
            stages_spec.F_QUESTION_TYPE,
            stages_spec.PAIR_SEPARATOR,
            facts.get(stages_spec.F_QUESTION_TYPE) or stages_spec.QT_OTHER,
        )
    )
    if stages_spec.F_CONTEXT_AGE in facts:
        context_age = facts.get(stages_spec.F_CONTEXT_AGE)
        lines.append(
            "%s%s%s"
            % (
                stages_spec.F_CONTEXT_AGE,
                stages_spec.PAIR_SEPARATOR,
                stages_spec.NONE_VALUE if context_age is None else context_age,
            )
        )
    return "\n".join(lines)


def context_block(facts: Dict[str, Any]) -> str:
    return stages_spec.HISTORY_CONTEXT_BLOCK.format(facts=format_facts(facts))


def stage_messages(system_prompt: str, user_text: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]


def stage_max_tokens(stage: str, client_cfg: llm_client.ClientConfig) -> int:
    if client_cfg.is_local:
        return client_cfg.max_tokens
    return stages_spec.STAGE_MAX_TOKENS[stage]


def call_stage(
    stage: str,
    messages: List[Dict[str, str]],
    client_cfg: llm_client.ClientConfig,
) -> Tuple[llm_client.CallResult, StageResult]:
    result = llm_client.call_with_config(
        messages, spec7.TEMPERATURE_BASELINE, client_cfg, stage_max_tokens(stage, client_cfg)
    )
    usage = llm_client.merge_usage(llm_client.empty_usage(), result.usage)
    return result, StageResult(
        stage=stage,
        raw_text=pipeline.clip_raw(result.content or ""),
        parsed={},
        ok=False,
        violations=[],
        latency_ms=result.latency_ms,
        usage=usage,
        cost_usd=pipeline.billed_cost(usage, client_cfg),
        model=client_cfg.model,
    )


def totals_of(stages: List[StageResult], started: float) -> Tuple[int, float, int]:
    total_cost = round(sum(stage.cost_usd for stage in stages), 8)
    return int((time.time() - started) * 1000), total_cost, len(stages)


def merge_errors(parts: List[Optional[str]]) -> Optional[str]:
    texts = [part for part in parts if part]
    if not texts:
        return None
    return "; ".join(texts)


def run_monolithic(
    case_text: str, client_cfg: llm_client.ClientConfig, case_id: str = ""
) -> MultiStageDecision:
    started = time.time()
    try:
        result, stage = call_stage(
            stages_spec.STAGE_MONOLITHIC,
            stage_messages(stages_spec.MONOLITHIC_SYSTEM_PROMPT, case_text),
            client_cfg,
        )
        guard = guards_v2.check_reply(result.content)
        parsed = guard.parsed or {}
        route = pipeline.route_of(parsed) if guard.parsed is not None else None
        if route not in stages_spec.ROUTES:
            route = None
        stage.parsed = dict(parsed)
        stage.violations = list(guard.violations)
        stage.ok = route is not None and result.error is None
        reason = pipeline.reason_of(parsed)
        latency_ms, cost, calls = totals_of([stage], started)
        return MultiStageDecision(
            case_id=case_id,
            mode=stages_spec.MODE_MONOLITHIC,
            route=route,
            confidence=round(pipeline.confidence_of(parsed), 4),
            reason=reason,
            answer_text=reason if route is not None else stages_spec.FALLBACK_ANSWER,
            stages=[stage],
            total_latency_ms=latency_ms,
            total_cost_usd=cost,
            calls=calls,
            failed_stage=None if stage.ok else stages_spec.STAGE_MONOLITHIC,
            error=result.error,
        )
    except Exception as unexpected_error:
        return failed_decision(
            case_id,
            stages_spec.MODE_MONOLITHIC,
            stages_spec.STAGE_MONOLITHIC,
            "сбой монолита: %s" % unexpected_error,
            started,
        )


def failed_decision(
    case_id: str, mode: str, stage: str, error_text: str, started: float
) -> MultiStageDecision:
    return MultiStageDecision(
        case_id=case_id,
        mode=mode,
        route=None,
        answer_text=stages_spec.FALLBACK_ANSWER,
        stages=[],
        total_latency_ms=int((time.time() - started) * 1000),
        total_cost_usd=0.0,
        calls=0,
        failed_stage=stage,
        error=error_text,
    )


def stage1_messages(
    case_text: str, history: Optional[List[Dict[str, str]]]
) -> Tuple[List[Dict[str, str]], bool]:
    kept = clip_history(history or [])
    if not kept:
        return (
            stage_messages(
                stages_spec.STAGE1_SYSTEM_PROMPT,
                stages_spec.STAGE1_USER_TEMPLATE.format(case_text=case_text),
            ),
            False,
        )
    return (
        stage_messages(
            stages_spec.STAGE1_CONVERSATION_SYSTEM_PROMPT,
            stages_spec.STAGE1_CONVERSATION_USER_TEMPLATE.format(
                conversation=format_conversation(kept), case_text=case_text
            ),
        ),
        True,
    )


def run_stage1(
    case_text: str,
    client_cfg: llm_client.ClientConfig,
    history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[StageResult, Dict[str, Any], Optional[str]]:
    messages, with_context = stage1_messages(case_text, history)
    result, stage = call_stage(stages_spec.STAGE_PARSE, messages, client_cfg)
    facts, violations = parse_stage1(result.content or "", with_context)
    stage.parsed = facts
    stage.violations = violations
    stage.ok = result.error is None and stages_spec.S1_PARSE not in violations
    return stage, facts, result.error


def run_stage2(
    facts: Dict[str, Any], client_cfg: llm_client.ClientConfig
) -> Tuple[StageResult, Dict[str, Any], Optional[str]]:
    result, stage = call_stage(
        stages_spec.STAGE_DECIDE,
        stage_messages(
            stages_spec.STAGE2_SYSTEM_PROMPT,
            stages_spec.STAGE2_USER_TEMPLATE.format(facts=format_facts(facts)),
        ),
        client_cfg,
    )
    decision, violations = parse_stage2(result.content or "")
    stage.parsed = decision
    stage.violations = violations
    stage.ok = result.error is None and decision[stages_spec.D_ROUTE] is not None
    return stage, decision, result.error


def run_stage3(
    route: str, why: str, facts: Dict[str, Any], client_cfg: llm_client.ClientConfig
) -> Tuple[StageResult, str, Optional[str]]:
    result, stage = call_stage(
        stages_spec.STAGE_ANSWER,
        stage_messages(
            stages_spec.STAGE3_SYSTEM_PROMPT,
            stages_spec.STAGE3_USER_TEMPLATE.format(
                route=route, why=why or stages_spec.NONE_VALUE, facts=format_facts(facts)
            ),
        ),
        client_cfg,
    )
    text = (result.content or "").strip()
    if len(text) < stages_spec.MIN_ANSWER_CHARS:
        stage.violations = [stages_spec.S3_EMPTY]
        stage.ok = False
        answer = stages_spec.FALLBACK_ANSWER
    else:
        stage.ok = result.error is None
        answer = clip_value(text, stages_spec.MAX_ANSWER_CHARS)
    stage.parsed = {"answer_chars": len(text)}
    return stage, answer, result.error


def run_multistage(
    case_text: str,
    cfg1: llm_client.ClientConfig,
    cfg2: Optional[llm_client.ClientConfig] = None,
    cfg3: Optional[llm_client.ClientConfig] = None,
    case_id: str = "",
    history: Optional[List[Dict[str, str]]] = None,
) -> MultiStageDecision:
    started = time.time()
    decide_cfg = cfg2 or cfg1
    answer_cfg = cfg3 or cfg1
    try:
        stage1, facts, error1 = run_stage1(case_text, cfg1, history)
        stages = [stage1]
        failed_stage: Optional[str] = None
        notes: List[Optional[str]] = [error1]
        facts_for_decision = facts
        if not stage1.ok:
            failed_stage = stages_spec.STAGE_PARSE
            facts_for_decision = empty_facts(stages_spec.F_CONTEXT_AGE in facts)
            notes.append("этап 1 не дал фактов, решение принимается на пустых фактах")

        stage2, decision, error2 = run_stage2(facts_for_decision, decide_cfg)
        stages.append(stage2)
        notes.append(error2)
        route = decision[stages_spec.D_ROUTE]
        why = decision[stages_spec.D_WHY]
        confidence = decision[stages_spec.D_CONFIDENCE]
        if not stage2.ok:
            if failed_stage is None:
                failed_stage = stages_spec.STAGE_DECIDE
            notes.append("этап 2 не дал маршрута, ответ заменён заглушкой")
            latency_ms, cost, calls = totals_of(stages, started)
            return MultiStageDecision(
                case_id=case_id,
                mode=stages_spec.MODE_MULTISTAGE,
                route=None,
                confidence=confidence,
                reason=why,
                answer_text=stages_spec.FALLBACK_ANSWER,
                stages=stages,
                total_latency_ms=latency_ms,
                total_cost_usd=cost,
                calls=calls,
                failed_stage=failed_stage,
                error=merge_errors(notes),
            )

        stage3, answer_text, error3 = run_stage3(route, why, facts_for_decision, answer_cfg)
        stages.append(stage3)
        notes.append(error3)
        if not stage3.ok and failed_stage is None:
            failed_stage = stages_spec.STAGE_ANSWER
        latency_ms, cost, calls = totals_of(stages, started)
        return MultiStageDecision(
            case_id=case_id,
            mode=stages_spec.MODE_MULTISTAGE,
            route=route,
            confidence=confidence,
            reason=why,
            answer_text=answer_text,
            stages=stages,
            total_latency_ms=latency_ms,
            total_cost_usd=cost,
            calls=calls,
            failed_stage=failed_stage,
            error=merge_errors(notes),
        )
    except Exception as unexpected_error:
        return failed_decision(
            case_id,
            stages_spec.MODE_MULTISTAGE,
            stages_spec.STAGE_PARSE,
            "сбой цепочки: %s" % unexpected_error,
            started,
        )
