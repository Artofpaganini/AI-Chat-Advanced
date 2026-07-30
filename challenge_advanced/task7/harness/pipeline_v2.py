"""Пайплайн версии 2: те же механизмы, шесть маршрутов и детерминированный кризисный гейт.

pipeline.py заморожен - на нём стоят замеры task7 и task8. Здесь повторяется его порядок работы
(избыточность, критик, скоринг), но с промптом и перечислением маршрутов из spec_v2.

Главное отличие - кризис родителя. Он ловится регулярками ДО обращения к модели и перекрывает
любой маршрут: если в тексте есть мысли о вреде себе или ребёнку, решение принимается на месте,
без сети, без голосования и без денег. Модель тут не нужна и не должна иметь возможности
передумать. Второй проход детектора идёт по тексту, который вернула модель: если признак
разглядела она, а регулярки нет - случай всё равно становится кризисным.

Порядок выбора маршрута отличается от v1 в одном месте: у SELF_CARE, PARENT_SUPPORT и DATA_INSIGHT
одинаковая тяжесть, поэтому при равенстве побеждает тот, за кого больше голосов, а не тот,
кто попался первым.
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
import guards_v2
import llm_client
import pipeline
import spec7
import spec_v2

CRISIS_PATTERNS = tuple(
    (label, re.compile(pattern)) for label, pattern in spec_v2.CRISIS_TRIGGER_PATTERNS
)

SUPPORT_THEME_PATTERNS = tuple(
    (label, re.compile(pattern)) for label, pattern in spec_v2.SUPPORT_THEME_PATTERNS
)

PROLONGED_PATTERNS = tuple(
    re.compile(pattern) for pattern in spec_v2.SUPPORT_PROLONGED_PATTERNS
)

CYRILLIC_PATTERN = re.compile(spec_v2.CYRILLIC_PATTERN)

EXPLAIN_CRISIS = "сработал кризисный гейт, модель не опрашивалась"
EXPLAIN_CRISIS_FROM_REPLY = "кризисный признак найден в ответе модели"


@dataclass
class DecisionV2(pipeline.Decision):
    language_rejected: bool = False
    crisis: bool = False
    crisis_markers: List[str] = field(default_factory=list)
    crisis_source: str = ""
    emergency_subtype: str = ""
    support_themes: List[str] = field(default_factory=list)
    support_prolonged: bool = False
    child_profile_present: bool = False
    child_profile_fields: List[str] = field(default_factory=list)
    data_source: str = spec_v2.DATA_SOURCE_NONE
    spec_version: str = spec_v2.SPEC_VERSION_V2


def has_cyrillic(text: str) -> bool:
    value = text if isinstance(text, str) else ""
    return CYRILLIC_PATTERN.search(value) is not None


def rejected_by_language(
    case_id: str,
    client_cfg: llm_client.ClientConfig,
    critic_cfg: Optional[llm_client.ClientConfig],
    trigger: str,
) -> DecisionV2:
    judge = pipeline.critic_config(client_cfg, critic_cfg)
    return DecisionV2(
        case_id=case_id,
        mode=spec7.MODE_PIPELINE,
        route=None,
        status=spec7.STATUS_FAIL,
        violations=[spec_v2.C_IN_NOT_RUSSIAN],
        calls=0,
        latency_ms=0,
        usage_total=llm_client.empty_usage(),
        cost_usd=0.0,
        input_rejected=False,
        inference_location=client_cfg.location,
        model=client_cfg.model,
        price_source=pipeline.price_source_of(client_cfg),
        self_check_trigger=trigger,
        critic_model=judge.model,
        critic_inference_location=judge.location,
        critic_price_source=pipeline.price_source_of(judge),
        adapter=client_cfg.adapter,
        critic_adapter=judge.adapter,
        language_rejected=True,
    )


def detect_crisis(text: str) -> List[str]:
    normalized = pipeline.normalize_for_risk(text)
    markers: List[str] = []
    for label, pattern in CRISIS_PATTERNS:
        if label in markers:
            continue
        if pattern.search(normalized) is not None:
            markers.append(label)
    return markers


def detect_support_themes(text: str) -> List[str]:
    normalized = pipeline.normalize_for_risk(text)
    themes: List[str] = []
    for label, pattern in SUPPORT_THEME_PATTERNS:
        if label in themes:
            continue
        if pattern.search(normalized) is not None:
            themes.append(label)
    return [theme for theme in spec_v2.SUPPORT_THEMES if theme in themes]


def detect_prolonged(text: str) -> bool:
    normalized = pipeline.normalize_for_risk(text)
    for pattern in PROLONGED_PATTERNS:
        if pattern.search(normalized) is not None:
            return True
    return False


def reply_crisis_text(red_flags: List[str], reason: str) -> str:
    return " ".join(list(red_flags) + [reason or ""])


def triage_messages(case_text: str, profile_block: str) -> List[Dict[str, str]]:
    system_text = spec_v2.TRIAGE_SYSTEM_PROMPT
    if profile_block:
        system_text = system_text + "\n\n" + profile_block
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": case_text},
    ]


def repair_messages(
    case_text: str, previous_reply: str, violations: List[str], profile_block: str
) -> List[Dict[str, str]]:
    hard_codes = [code for code in violations if not code.startswith(spec7.SOFT_PREFIX)]
    hint = spec_v2.REPAIR_HINT.format(violations=", ".join(hard_codes) or "формат ответа")
    messages = triage_messages(case_text, profile_block)
    messages.append({"role": "assistant", "content": previous_reply})
    messages.append({"role": "user", "content": hint})
    return messages


def critic_messages(
    case_text: str, route: str, red_flags: List[str], reason: str
) -> List[Dict[str, str]]:
    flags_text = ", ".join(red_flags) if red_flags else spec7.EMPTY_FLAGS_PLACEHOLDER
    user_text = spec7.CRITIC_USER_TEMPLATE.format(
        case_text=case_text,
        route=route,
        red_flags=flags_text,
        reason=reason or spec7.EMPTY_FLAGS_PLACEHOLDER,
    )
    return [
        {"role": "system", "content": spec_v2.CRITIC_SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]


def collect_sample(
    case_text: str, client_cfg: llm_client.ClientConfig, profile_block: str
) -> pipeline.SampleOutcome:
    usage = llm_client.empty_usage()
    result = llm_client.call_with_config(
        triage_messages(case_text, profile_block), spec7.TEMPERATURE_REDUNDANCY, client_cfg
    )
    usage = llm_client.merge_usage(usage, result.usage)
    raw_texts = [pipeline.clip_raw(result.content)]
    if result.error is not None:
        return pipeline.SampleOutcome(None, [], False, False, raw_texts, 1, usage, result.error)

    guard = guards_v2.check_reply(result.content)
    if guard.ok:
        return pipeline.SampleOutcome(
            guard.parsed, list(guard.violations), True, False, raw_texts, 1, usage, None
        )

    repair = llm_client.call_with_config(
        repair_messages(case_text, result.content, guard.violations, profile_block),
        spec7.TEMPERATURE_REDUNDANCY,
        client_cfg,
    )
    usage = llm_client.merge_usage(usage, repair.usage)
    raw_texts.append(pipeline.clip_raw(repair.content))
    if repair.error is not None:
        return pipeline.SampleOutcome(
            None, list(guard.violations), False, True, raw_texts, 2, usage, repair.error
        )

    repair_guard = guards_v2.check_reply(repair.content)
    violations = list(guard.violations) + list(repair_guard.violations)
    if repair_guard.ok:
        return pipeline.SampleOutcome(
            repair_guard.parsed, violations, True, True, raw_texts, 2, usage, None
        )
    return pipeline.SampleOutcome(None, violations, False, True, raw_texts, 2, usage, None)


def severity_of(route: str) -> int:
    return spec_v2.SEVERITY.get(route, 0)


def majority_route(votes: List[str]) -> str:
    return pipeline.majority_route(votes, spec_v2.SEVERITY)


def vote_route(votes: List[str]) -> str:
    return pipeline.vote_route(votes, spec_v2.SEVERITY)


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
        return None, False, list(guard.violations), 1, usage, pipeline.clip_raw(result.content), result.error
    verdict = str(guard.parsed.get("verdict"))
    risk_missed = bool(guard.parsed.get("risk_missed"))
    return verdict, risk_missed, list(guard.violations), 1, usage, pipeline.clip_raw(result.content), None


def crisis_decision(
    case_id: str,
    markers: List[str],
    client_cfg: llm_client.ClientConfig,
    critic_cfg: Optional[llm_client.ClientConfig],
    trigger: str,
    started: float,
    profile_present: bool,
    profile_fields: List[str],
) -> DecisionV2:
    judge = pipeline.critic_config(client_cfg, critic_cfg)
    return DecisionV2(
        case_id=case_id,
        mode=spec7.MODE_PIPELINE,
        route=spec7.ROUTE_EMERGENCY,
        red_flags=[spec_v2.CRISIS_RED_FLAG],
        age_months=None,
        reason=spec_v2.CRISIS_REASON,
        confidence_final=spec_v2.CRISIS_CONFIDENCE,
        status=spec7.STATUS_OK,
        votes=[spec7.ROUTE_EMERGENCY],
        agreement=1.0,
        self_check_ran=False,
        self_check_verdict=None,
        risk_missed=False,
        escalated_by_safety=True,
        violations=[],
        retried=False,
        calls=0,
        latency_ms=int((time.time() - started) * 1000),
        usage_total=llm_client.empty_usage(),
        cost_usd=0.0,
        error=None,
        raw_samples=[],
        inference_location=client_cfg.location,
        model=client_cfg.model,
        price_source=pipeline.price_source_of(client_cfg),
        self_check_trigger=trigger,
        risk_markers=[],
        critic_model=judge.model,
        critic_inference_location=judge.location,
        critic_price_source=pipeline.price_source_of(judge),
        adapter=client_cfg.adapter,
        critic_adapter=judge.adapter,
        crisis=True,
        crisis_markers=markers,
        crisis_source=EXPLAIN_CRISIS,
        emergency_subtype=spec_v2.CRISIS_SUBTYPE,
        child_profile_present=profile_present,
        child_profile_fields=profile_fields,
    )


def run_pipeline(
    case_text: str,
    client_cfg: llm_client.ClientConfig,
    case_id: str = "",
    self_check_trigger: str = spec7.SELF_CHECK_TRIGGER_AGREEMENT,
    critic_cfg: Optional[llm_client.ClientConfig] = None,
    profile_block: str = "",
    profile_present: bool = False,
    profile_fields: Optional[List[str]] = None,
    data_source: str = spec_v2.DATA_SOURCE_NONE,
) -> DecisionV2:
    started = time.time()
    fields = list(profile_fields or [])
    judge = pipeline.critic_config(client_cfg, critic_cfg)
    forced = self_check_trigger == spec7.SELF_CHECK_TRIGGER_ALWAYS
    risk_markers = pipeline.detect_risk_markers(case_text)
    support_themes = detect_support_themes(case_text)
    support_prolonged = detect_prolonged(case_text)
    input_guard = guards.check_input(case_text)
    if not input_guard.ok:
        rejected = pipeline.rejected_by_input(
            case_id,
            spec7.MODE_PIPELINE,
            input_guard.violations,
            client_cfg,
            self_check_trigger,
            judge,
        )
        decision = DecisionV2(**vars(rejected))
        decision.self_check_forced = forced
        decision.risk_markers = risk_markers
        decision.child_profile_present = profile_present
        decision.child_profile_fields = fields
        return decision

    if not has_cyrillic(case_text):
        return rejected_by_language(case_id, client_cfg, critic_cfg, self_check_trigger)

    crisis_markers = detect_crisis(case_text)
    if crisis_markers:
        return crisis_decision(
            case_id,
            crisis_markers,
            client_cfg,
            critic_cfg,
            self_check_trigger,
            started,
            profile_present,
            fields,
        )

    outcomes = [
        collect_sample(case_text, client_cfg, profile_block)
        for _ in range(spec7.REDUNDANCY_SAMPLES)
    ]

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
    votes = [pipeline.route_of(parsed) for parsed in valid_samples]

    if not votes:
        return DecisionV2(
            case_id=case_id,
            mode=spec7.MODE_PIPELINE,
            route=None,
            status=spec7.STATUS_FAIL,
            violations=violations,
            retried=retried,
            calls=calls,
            latency_ms=int((time.time() - started) * 1000),
            usage_total=usage_total,
            cost_usd=pipeline.billed_cost(usage_total, client_cfg),
            error="; ".join(errors) if errors else None,
            raw_samples=raw_samples,
            inference_location=client_cfg.location,
            model=client_cfg.model,
            price_source=pipeline.price_source_of(client_cfg),
            self_check_forced=forced,
            self_check_trigger=self_check_trigger,
            risk_markers=risk_markers,
            critic_model=judge.model,
            critic_inference_location=judge.location,
            critic_price_source=pipeline.price_source_of(judge),
            adapter=client_cfg.adapter,
            critic_adapter=judge.adapter,
            child_profile_present=profile_present,
            child_profile_fields=fields,
            data_source=data_source,
        )

    route_final = vote_route(votes)
    vote_agreement = pipeline.agreement_share(votes, route_final)
    escalated_by_safety = severity_of(route_final) > severity_of(majority_route(votes))

    red_flags = pipeline.merge_flags(valid_samples, route_final)
    representative = pipeline.pick_representative(valid_samples, route_final) or valid_samples[0]
    reason = pipeline.reason_of(representative)
    age_months = pipeline.age_of(representative)
    self_reported = sum(pipeline.confidence_of(parsed) for parsed in valid_samples) / len(
        valid_samples
    )

    self_check_ran = pipeline.should_self_check(
        self_check_trigger, vote_agreement, escalated_by_safety, risk_markers
    )
    main_cost = pipeline.billed_cost(usage_total, client_cfg)
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
    critic_cost = pipeline.billed_cost(critic_usage_total, judge)

    if risk_missed:
        route_final = spec7.ROUTE_EMERGENCY
        if not red_flags:
            red_flags = ["критик увидел упущенный опасный признак"]

    crisis_from_reply = detect_crisis(reply_crisis_text(red_flags, reason))
    crisis = bool(crisis_from_reply)
    crisis_source = EXPLAIN_CRISIS_FROM_REPLY if crisis else ""
    if crisis:
        route_final = spec7.ROUTE_EMERGENCY
        if spec_v2.CRISIS_RED_FLAG not in red_flags:
            red_flags = ([spec_v2.CRISIS_RED_FLAG] + red_flags)[: spec7.MAX_RED_FLAGS]

    check_agreement = pipeline.self_check_agreement(verdict, vote_agreement)
    confidence_final = pipeline.score_confidence(vote_agreement, check_agreement, self_reported)
    status = pipeline.resolve_status(
        True, risk_missed, escalated_by_safety, confidence_final, blocking_violations
    )
    if crisis:
        status = spec7.STATUS_OK
        confidence_final = spec_v2.CRISIS_CONFIDENCE

    return DecisionV2(
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
        price_source=pipeline.price_source_of(client_cfg),
        self_check_forced=forced,
        self_check_trigger=self_check_trigger,
        risk_markers=risk_markers,
        critic_model=judge.model,
        critic_inference_location=judge.location,
        critic_price_source=pipeline.price_source_of(judge),
        critic_usage_total=critic_usage_total,
        critic_cost_usd=critic_cost,
        adapter=client_cfg.adapter,
        critic_adapter=judge.adapter,
        crisis=crisis,
        crisis_markers=crisis_from_reply,
        crisis_source=crisis_source,
        emergency_subtype=spec_v2.CRISIS_SUBTYPE if crisis else "",
        support_themes=support_themes,
        support_prolonged=support_prolonged,
        child_profile_present=profile_present,
        child_profile_fields=fields,
        data_source=data_source,
    )
