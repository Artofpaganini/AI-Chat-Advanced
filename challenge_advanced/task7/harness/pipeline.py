"""Механизмы 2-4: Redundancy, Self-check и Scoring поверх готовой модели.

run_baseline - честная точка отсчёта: ровно один вызов, никакого контроля. Предусловие входа
он проверяет и записывает в violations, но всё равно идёт в модель и принимает ответ -
именно так ведёт себя неконтролируемый инференс.
run_pipeline - полный цикл из SPEC разделы 3-6. Предусловие входа стоит первым: нарушение
даёт FAIL за ноль вызовов и ноль денег.

Триггер критика имеет три режима. agreement - контракт SPEC раздел 5, критик зовётся при разбросе
голосов либо подъёме маршрута. risk - плюс к этому критик зовётся, если detect_risk_markers нашёл
в тексте сообщения признак риска. always - критик зовётся на каждом кейсе. Режимы risk и always -
эксперимент поверх контракта, дефолт остаётся agreement.

Критик может работать на другой модели, чем основной проход: run_pipeline принимает две
конфигурации клиента. Если конфигурация критика не передана, он работает на той же модели -
это прежнее поведение. Деньги при этом считаются раздельно: основные вызовы по цене основной
модели, вызов критика по цене его модели, в Decision лежат обе суммы.

Порядок статусов при конфликте условий: нет валидных голосов -> FAIL, risk_missed -> UNSURE,
safety-подъём -> UNSURE, confidence_final ниже нижнего порога -> FAIL, дальше OK либо UNSURE.
Safety-подъём стоит выше нижнего порога сознательно: спрятать поднятый до экстренного маршрут
за общей заглушкой опаснее, чем показать его с пометкой о неуверенности.
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

import guards
import llm_client
import spec7

RISK_PATTERNS = tuple(
    (label, re.compile(pattern)) for label, pattern in spec7.RISK_TRIGGER_PATTERNS
)


@dataclass
class Decision:
    case_id: str
    mode: str
    route: Optional[str]
    red_flags: List[str] = field(default_factory=list)
    age_months: Optional[int] = None
    reason: str = ""
    confidence_final: float = 0.0
    status: str = spec7.STATUS_FAIL
    votes: List[str] = field(default_factory=list)
    agreement: float = 0.0
    self_check_ran: bool = False
    self_check_verdict: Optional[str] = None
    risk_missed: bool = False
    escalated_by_safety: bool = False
    violations: List[str] = field(default_factory=list)
    retried: bool = False
    calls: int = 0
    latency_ms: int = 0
    usage_total: Dict[str, int] = field(default_factory=llm_client.empty_usage)
    cost_usd: float = 0.0
    error: Optional[str] = None
    raw_samples: List[str] = field(default_factory=list)
    input_rejected: bool = False
    inference_location: str = spec7.LOCATION_CLOUD
    model: str = ""
    price_source: str = spec7.PRICE_SOURCE_UNKNOWN
    self_check_forced: bool = False
    self_check_trigger: str = spec7.SELF_CHECK_TRIGGER_AGREEMENT
    risk_markers: List[str] = field(default_factory=list)
    critic_model: str = ""
    critic_inference_location: str = ""
    critic_price_source: str = ""
    critic_usage_total: Dict[str, int] = field(default_factory=llm_client.empty_usage)
    critic_cost_usd: float = 0.0


@dataclass
class SampleOutcome:
    parsed: Optional[Dict[str, Any]]
    violations: List[str]
    valid: bool
    repaired: bool
    raw_texts: List[str]
    calls: int
    usage: Dict[str, int]
    error: Optional[str]


def normalize_for_risk(text: str) -> str:
    value = text if isinstance(text, str) else ""
    return value.lower().replace(spec7.RISK_TEXT_LETTER_YO, spec7.RISK_TEXT_LETTER_YE)


def detect_risk_markers(text: str) -> List[str]:
    normalized = normalize_for_risk(text)
    markers: List[str] = []
    for label, pattern in RISK_PATTERNS:
        if label in markers:
            continue
        if pattern.search(normalized) is not None:
            markers.append(label)
    return markers


def should_self_check(
    trigger: str, vote_agreement: float, escalated_by_safety: bool, risk_markers: List[str]
) -> bool:
    by_agreement = vote_agreement < 1.0 or escalated_by_safety
    if trigger == spec7.SELF_CHECK_TRIGGER_ALWAYS:
        return True
    if trigger == spec7.SELF_CHECK_TRIGGER_RISK:
        return bool(risk_markers) or by_agreement
    return by_agreement


def triage_messages(case_text: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": spec7.TRIAGE_SYSTEM_PROMPT},
        {"role": "user", "content": case_text},
    ]


def repair_messages(case_text: str, previous_reply: str, violations: List[str]) -> List[Dict[str, str]]:
    hard_codes = [code for code in violations if not code.startswith(spec7.SOFT_PREFIX)]
    hint = spec7.REPAIR_HINT.format(violations=", ".join(hard_codes) or "формат ответа")
    return [
        {"role": "system", "content": spec7.TRIAGE_SYSTEM_PROMPT},
        {"role": "user", "content": case_text},
        {"role": "assistant", "content": previous_reply},
        {"role": "user", "content": hint},
    ]


def critic_messages(case_text: str, route: str, red_flags: List[str], reason: str) -> List[Dict[str, str]]:
    flags_text = ", ".join(red_flags) if red_flags else spec7.EMPTY_FLAGS_PLACEHOLDER
    user_text = spec7.CRITIC_USER_TEMPLATE.format(
        case_text=case_text,
        route=route,
        red_flags=flags_text,
        reason=reason or spec7.EMPTY_FLAGS_PLACEHOLDER,
    )
    return [
        {"role": "system", "content": spec7.CRITIC_SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]


def clip_raw(text: str) -> str:
    if len(text) <= spec7.RAW_SAMPLE_CHARS:
        return text
    return text[: spec7.RAW_SAMPLE_CHARS]


def route_of(parsed: Dict[str, Any]) -> str:
    return str(parsed.get("route"))


def confidence_of(parsed: Dict[str, Any]) -> float:
    value = parsed.get("confidence")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value)


def flags_of(parsed: Dict[str, Any]) -> List[str]:
    value = parsed.get("red_flags")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def age_of(parsed: Dict[str, Any]) -> Optional[int]:
    value = parsed.get("age_months")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def reason_of(parsed: Dict[str, Any]) -> str:
    value = parsed.get("reason")
    if not isinstance(value, str):
        return ""
    return value


def billed_cost(usage: Dict[str, int], client_cfg: llm_client.ClientConfig) -> float:
    if client_cfg.is_local:
        return 0.0
    return llm_client.usage_cost(usage, client_cfg.model)


def price_source_of(client_cfg: llm_client.ClientConfig) -> str:
    if client_cfg.is_local:
        return spec7.PRICE_SOURCE_LOCAL
    return llm_client.price_source(client_cfg.model)


def critic_config(
    client_cfg: llm_client.ClientConfig, critic_cfg: Optional[llm_client.ClientConfig]
) -> llm_client.ClientConfig:
    if critic_cfg is None:
        return client_cfg
    return critic_cfg


def run_baseline(case_text: str, client_cfg: llm_client.ClientConfig, case_id: str = "") -> Decision:
    started = time.time()
    input_guard = guards.check_input(case_text)
    result = llm_client.call_with_config(
        triage_messages(case_text), spec7.TEMPERATURE_BASELINE, client_cfg
    )
    guard = guards.check_reply(result.content)
    parsed = guard.parsed or {}
    route = route_of(parsed) if guard.parsed is not None else None
    if route is not None and route not in spec7.ROUTES:
        route = None
    usage_total = llm_client.merge_usage(llm_client.empty_usage(), result.usage)
    return Decision(
        case_id=case_id,
        mode=spec7.MODE_BASELINE,
        route=route,
        red_flags=flags_of(parsed),
        age_months=age_of(parsed),
        reason=reason_of(parsed),
        confidence_final=round(confidence_of(parsed), 4),
        status=spec7.STATUS_OK,
        votes=[route] if route else [],
        agreement=1.0 if route else 0.0,
        self_check_ran=False,
        self_check_verdict=None,
        risk_missed=False,
        escalated_by_safety=False,
        violations=list(input_guard.violations) + list(guard.violations),
        retried=False,
        calls=1,
        latency_ms=int((time.time() - started) * 1000),
        usage_total=usage_total,
        cost_usd=billed_cost(usage_total, client_cfg),
        error=result.error,
        raw_samples=[clip_raw(result.content)],
        input_rejected=False,
        inference_location=client_cfg.location,
        model=client_cfg.model,
        price_source=price_source_of(client_cfg),
        self_check_trigger=spec7.SELF_CHECK_TRIGGER_NONE,
        risk_markers=detect_risk_markers(case_text),
    )


def rejected_by_input(
    case_id: str,
    mode: str,
    violations: List[str],
    client_cfg: llm_client.ClientConfig,
    trigger: str = spec7.SELF_CHECK_TRIGGER_AGREEMENT,
    critic_cfg: Optional[llm_client.ClientConfig] = None,
) -> Decision:
    judge = critic_config(client_cfg, critic_cfg)
    return Decision(
        case_id=case_id,
        mode=mode,
        route=None,
        status=spec7.STATUS_FAIL,
        violations=list(violations),
        calls=0,
        latency_ms=0,
        usage_total=llm_client.empty_usage(),
        cost_usd=0.0,
        input_rejected=True,
        inference_location=client_cfg.location,
        model=client_cfg.model,
        price_source=price_source_of(client_cfg),
        self_check_trigger=trigger,
        critic_model=judge.model,
        critic_inference_location=judge.location,
        critic_price_source=price_source_of(judge),
    )


def collect_sample(case_text: str, client_cfg: llm_client.ClientConfig) -> SampleOutcome:
    usage = llm_client.empty_usage()
    result = llm_client.call_with_config(
        triage_messages(case_text), spec7.TEMPERATURE_REDUNDANCY, client_cfg
    )
    usage = llm_client.merge_usage(usage, result.usage)
    raw_texts = [clip_raw(result.content)]
    if result.error is not None:
        return SampleOutcome(None, [], False, False, raw_texts, 1, usage, result.error)

    guard = guards.check_reply(result.content)
    if guard.ok:
        return SampleOutcome(guard.parsed, list(guard.violations), True, False, raw_texts, 1, usage, None)

    repair = llm_client.call_with_config(
        repair_messages(case_text, result.content, guard.violations),
        spec7.TEMPERATURE_REDUNDANCY,
        client_cfg,
    )
    usage = llm_client.merge_usage(usage, repair.usage)
    raw_texts.append(clip_raw(repair.content))
    if repair.error is not None:
        return SampleOutcome(None, list(guard.violations), False, True, raw_texts, 2, usage, repair.error)

    repair_guard = guards.check_reply(repair.content)
    violations = list(guard.violations) + list(repair_guard.violations)
    if repair_guard.ok:
        return SampleOutcome(repair_guard.parsed, violations, True, True, raw_texts, 2, usage, None)
    return SampleOutcome(None, violations, False, True, raw_texts, 2, usage, None)


def majority_route(votes: List[str]) -> str:
    counts: Dict[str, int] = {}
    for vote in votes:
        counts[vote] = counts.get(vote, 0) + 1
    top_count = max(counts.values())
    tied = [route for route, count in counts.items() if count == top_count]
    return min(tied, key=lambda route: spec7.SEVERITY.get(route, 0))


def vote_route(votes: List[str]) -> str:
    return max(votes, key=lambda vote: spec7.SEVERITY.get(vote, 0))


def agreement_share(votes: List[str], route: str) -> float:
    if not votes:
        return 0.0
    return round(sum(1 for vote in votes if vote == route) / len(votes), 4)


def self_check_agreement(verdict: Optional[str], vote_agreement: float) -> float:
    if verdict == spec7.VERDICT_AGREE:
        return 1.0
    if verdict == spec7.VERDICT_DISAGREE:
        return 0.0
    return vote_agreement


def score_confidence(vote_agreement: float, check_agreement: float, self_reported: float) -> float:
    total = (
        spec7.W_VOTE * vote_agreement
        + spec7.W_SELF_CHECK * check_agreement
        + spec7.W_SELF_REPORT * self_reported
    )
    return round(total, 4)


def resolve_status(
    has_votes: bool,
    risk_missed: bool,
    escalated_by_safety: bool,
    confidence_final: float,
    blocking_violations: bool,
) -> str:
    if not has_votes:
        return spec7.STATUS_FAIL
    if risk_missed:
        return spec7.STATUS_UNSURE
    if escalated_by_safety:
        return spec7.STATUS_UNSURE
    if confidence_final < spec7.UNSURE_THRESHOLD:
        return spec7.STATUS_FAIL
    if confidence_final >= spec7.OK_THRESHOLD and not blocking_violations:
        return spec7.STATUS_OK
    return spec7.STATUS_UNSURE


def merge_flags(samples: List[Dict[str, Any]], route: str) -> List[str]:
    collected: List[str] = []
    for parsed in samples:
        if route_of(parsed) != route:
            continue
        for flag in flags_of(parsed):
            if flag not in collected:
                collected.append(flag)
    return collected[: spec7.MAX_RED_FLAGS]


def pick_representative(samples: List[Dict[str, Any]], route: str) -> Optional[Dict[str, Any]]:
    matching = [parsed for parsed in samples if route_of(parsed) == route]
    if not matching:
        return None
    return max(matching, key=confidence_of)


def run_self_check(
    case_text: str,
    route: str,
    red_flags: List[str],
    reason: str,
    critic_cfg: llm_client.ClientConfig,
) -> Tuple[Optional[str], bool, List[str], int, Dict[str, int], str, Optional[str]]:
    result = llm_client.call_with_config(
        critic_messages(case_text, route, red_flags, reason),
        spec7.TEMPERATURE_SELF_CHECK,
        critic_cfg,
    )
    usage = llm_client.merge_usage(llm_client.empty_usage(), result.usage)
    guard = guards.check_critic_reply(result.content)
    if result.error is not None or not guard.ok or guard.parsed is None:
        return None, False, list(guard.violations), 1, usage, clip_raw(result.content), result.error
    verdict = str(guard.parsed.get("verdict"))
    risk_missed = bool(guard.parsed.get("risk_missed"))
    return verdict, risk_missed, list(guard.violations), 1, usage, clip_raw(result.content), None


def run_pipeline(
    case_text: str,
    client_cfg: llm_client.ClientConfig,
    case_id: str = "",
    self_check_trigger: str = spec7.SELF_CHECK_TRIGGER_AGREEMENT,
    critic_cfg: Optional[llm_client.ClientConfig] = None,
) -> Decision:
    started = time.time()
    judge = critic_config(client_cfg, critic_cfg)
    forced = self_check_trigger == spec7.SELF_CHECK_TRIGGER_ALWAYS
    risk_markers = detect_risk_markers(case_text)
    input_guard = guards.check_input(case_text)
    if not input_guard.ok:
        decision = rejected_by_input(
            case_id,
            spec7.MODE_PIPELINE,
            input_guard.violations,
            client_cfg,
            self_check_trigger,
            judge,
        )
        decision.self_check_forced = forced
        decision.risk_markers = risk_markers
        return decision

    outcomes = [collect_sample(case_text, client_cfg) for _ in range(spec7.REDUNDANCY_SAMPLES)]

    calls = sum(outcome.calls for outcome in outcomes)
    usage_total = llm_client.empty_usage()
    violations: List[str] = []
    raw_samples: List[str] = []
    errors: List[str] = []
    for outcome in outcomes:
        usage_total = llm_client.merge_usage(usage_total, outcome.usage)
        violations.extend(outcome.violations)
        raw_samples.extend(outcome.raw_texts)
        if outcome.error is not None:
            errors.append(outcome.error)

    retried = any(outcome.repaired for outcome in outcomes)
    blocking_violations = any(
        not outcome.valid and guards.has_hard_violation(outcome.violations) for outcome in outcomes
    )

    valid_samples = [outcome.parsed for outcome in outcomes if outcome.valid and outcome.parsed]
    votes = [route_of(parsed) for parsed in valid_samples]

    if not votes:
        return Decision(
            case_id=case_id,
            mode=spec7.MODE_PIPELINE,
            route=None,
            status=spec7.STATUS_FAIL,
            violations=violations,
            retried=retried,
            calls=calls,
            latency_ms=int((time.time() - started) * 1000),
            usage_total=usage_total,
            cost_usd=billed_cost(usage_total, client_cfg),
            error="; ".join(errors) if errors else None,
            raw_samples=raw_samples,
            inference_location=client_cfg.location,
            model=client_cfg.model,
            price_source=price_source_of(client_cfg),
            self_check_forced=forced,
            self_check_trigger=self_check_trigger,
            risk_markers=risk_markers,
            critic_model=judge.model,
            critic_inference_location=judge.location,
            critic_price_source=price_source_of(judge),
        )

    route_final = vote_route(votes)
    vote_agreement = agreement_share(votes, route_final)
    escalated_by_safety = spec7.SEVERITY[route_final] > spec7.SEVERITY[majority_route(votes)]

    red_flags = merge_flags(valid_samples, route_final)
    representative = pick_representative(valid_samples, route_final) or valid_samples[0]
    reason = reason_of(representative)
    age_months = age_of(representative)
    self_reported = sum(confidence_of(parsed) for parsed in valid_samples) / len(valid_samples)

    self_check_ran = should_self_check(
        self_check_trigger, vote_agreement, escalated_by_safety, risk_markers
    )
    main_cost = billed_cost(usage_total, client_cfg)
    critic_usage_total = llm_client.empty_usage()
    verdict: Optional[str] = None
    risk_missed = False
    if self_check_ran:
        (
            verdict,
            risk_missed,
            critic_violations,
            critic_calls,
            critic_usage,
            critic_raw,
            critic_error,
        ) = run_self_check(case_text, route_final, red_flags, reason, judge)
        calls += critic_calls
        critic_usage_total = llm_client.merge_usage(critic_usage_total, critic_usage)
        usage_total = llm_client.merge_usage(usage_total, critic_usage)
        violations.extend(critic_violations)
        raw_samples.append(critic_raw)
        if critic_error is not None:
            errors.append(critic_error)
        if guards.has_hard_violation(critic_violations):
            blocking_violations = True
    critic_cost = billed_cost(critic_usage_total, judge)

    if risk_missed:
        route_final = spec7.ROUTE_EMERGENCY
        if not red_flags:
            red_flags = ["критик увидел упущенный опасный признак"]

    check_agreement = self_check_agreement(verdict, vote_agreement)
    confidence_final = score_confidence(vote_agreement, check_agreement, self_reported)
    status = resolve_status(
        True, risk_missed, escalated_by_safety, confidence_final, blocking_violations
    )

    return Decision(
        case_id=case_id,
        mode=spec7.MODE_PIPELINE,
        route=route_final,
        red_flags=red_flags,
        age_months=age_months,
        reason=reason,
        confidence_final=confidence_final,
        status=status,
        votes=votes,
        agreement=vote_agreement,
        self_check_ran=self_check_ran,
        self_check_verdict=verdict,
        risk_missed=risk_missed,
        escalated_by_safety=escalated_by_safety,
        violations=violations,
        retried=retried,
        calls=calls,
        latency_ms=int((time.time() - started) * 1000),
        usage_total=usage_total,
        cost_usd=round(main_cost + critic_cost, 8),
        error="; ".join(errors) if errors else None,
        raw_samples=raw_samples,
        inference_location=client_cfg.location,
        model=client_cfg.model,
        price_source=price_source_of(client_cfg),
        self_check_forced=forced,
        self_check_trigger=self_check_trigger,
        risk_markers=risk_markers,
        critic_model=judge.model,
        critic_inference_location=judge.location,
        critic_price_source=price_source_of(judge),
        critic_usage_total=critic_usage_total,
        critic_cost_usd=critic_cost,
    )


def failed_decision(case_id: str, mode: str, error_text: str) -> Decision:
    return Decision(
        case_id=case_id,
        mode=mode,
        route=None,
        status=spec7.STATUS_FAIL if mode == spec7.MODE_PIPELINE else spec7.STATUS_OK,
        error=error_text,
    )
