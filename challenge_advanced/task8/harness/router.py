"""Каскад из двух уровней: дешёвая локальная модель и сильная облачная.

Уровень 1 - pipeline.run_baseline на локальном Qwen с адаптером, стоит ноль.
Уровень 2 - тот же run_baseline на deepseek, включается только по эвристике.
Ответ сильной модели окончательный, третьего уровня нет.

Эвристика E_RISK работает по тексту запроса до любого вызова: дешёвый уровень тогда
не зовётся вовсе и calls_cheap остаётся нулём. Остальные смотрят на ответ дешёвой модели.

E_CONFLICT берёт тот же признак риска, что и E_RISK, но сравнивает его с ответом дешёвой модели и
поднимает наверх только расхождение. Дешёвая ответила EMERGENCY - она уже согласна с признаком,
платить за подтверждение незачем. Ответила спокойнее порога CONFLICT_SEVERITY_CEILING - вот это
спор, его и разбирает сильная модель. Из-за сравнения с ответом правило постовое: дешёвый вызов
делается всегда, зато сильный редко.

Дешёвая не дала маршрута вовсе - тоже спор, и самый сильный: severity такого ответа ниже любого
потолка, кейс уходит наверх. Это осознанно, дешёвый уровень промолчал на тексте с признаком риска.
На наборе из 50 кейсов пустой маршрут и отклонённый вход не встретились ни разу, так что цена
решения нулевая.

Потолок ниже DOCTOR_SOON ставить нельзя, и два основания у этого разной прочности.

Безопасность потолка 2 держится не на замере ответов, а на устройстве правила. Признак риска есть
у всех 13 экстренных кейсов набора, а потолок 2 поднимает наверх любой маркерный кейс, где дешёвая
ответила ниже EMERGENCY. Значит любой экстренный случай, который дешёвая занизила, уходит к
сильной модели по построению, каким бы ни вышел семпл.

Но и этот довод не бесплатный: он наследует безопасность у полноты маркеров на экстренном классе.
13 из 13 - замер на 50 кейсах, а не свойство шаблонов RISK_PATTERNS. Экстренный случай,
сформулированный мимо шаблонов, до сравнения с ответом дешёвой модели просто не дойдёт, и потолок
его не спасёт. Величина, за которой следить дальше, - не потолок, а полнота маркеров на золотых
EMERGENCY: просядет она, просядет и весь довод.

Вред потолка 1 держится на замере, и он слабее. Зазор - экстренные кейсы, где дешёвая ответила
ниже, - на наборе состоит из одного borderline_08 с ответом DOCTOR_SOON: потолок 2 его берёт,
потолок 1 уже нет, и точность падает ниже only_cheap. Зазор проверен на семи семплах дешёвого
уровня (only_cheap, route_conf на четырёх порогах, route_status, route_conflict) и во всех семи
одинаков. Но опора всё равно узкая: сдвинься ответ на этом кейсе на SELF_CARE, и потолок 1 стал
бы безопасным. Закреплять потолок в контракте без добора кейсов, где дешёвая занижает экстренное,
не стоит.

Статус дешёвого ответа run_baseline не считает - там всегда OK, это его контракт честной точки
отсчёта. Поэтому статус выводится здесь через pipeline.resolve_status по порогам task7:
нет маршрута -> FAIL, уверенность ниже 0.40 -> FAIL, от 0.75 без жёстких нарушений -> OK,
иначе UNSURE. Новых порогов не вводится.
"""

import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import router_spec

sys.path.insert(0, router_spec.TASK7_HARNESS_DIR)

import guards
import llm_client
import pipeline
import spec7


@dataclass
class RoutePolicy:
    strategy: str
    heuristics: Tuple[str, ...] = ()
    confidence_threshold: float = router_spec.DEFAULT_CONFIDENCE_THRESHOLD
    conflict_ceiling: int = router_spec.CONFLICT_SEVERITY_CEILING
    force_strong: bool = False

    def enabled(self, code: str) -> bool:
        return code in self.heuristics


@dataclass
class RouteOutcome:
    case_id: str
    strategy: str
    final_route: Optional[str] = None
    final_status: str = spec7.STATUS_FAIL
    final_confidence: float = 0.0
    escalated: bool = False
    escalation_reasons: List[str] = field(default_factory=list)
    cheap_decision: Optional[pipeline.Decision] = None
    strong_decision: Optional[pipeline.Decision] = None
    calls_cheap: int = 0
    calls_strong: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None


def policy_for(
    strategy: str,
    confidence_threshold: float = router_spec.DEFAULT_CONFIDENCE_THRESHOLD,
    conflict_ceiling: int = router_spec.CONFLICT_SEVERITY_CEILING,
) -> RoutePolicy:
    return RoutePolicy(
        strategy=strategy,
        heuristics=router_spec.STRATEGY_HEURISTICS.get(strategy, ()),
        confidence_threshold=confidence_threshold,
        conflict_ceiling=conflict_ceiling,
        force_strong=strategy == router_spec.STRATEGY_ONLY_STRONG,
    )


def cheap_config(
    model: str = router_spec.CHEAP_MODEL,
    base_url: str = router_spec.CHEAP_BASE_URL,
    adapters: str = router_spec.CHEAP_ADAPTERS,
    timeout: int = spec7.REQUEST_TIMEOUT_SECONDS,
) -> llm_client.ClientConfig:
    payload = dict(spec7.NO_THINKING_PAYLOAD)
    if adapters:
        payload[spec7.ADAPTERS_PAYLOAD_KEY] = adapters
    return llm_client.ClientConfig(
        model=model, base_url=base_url, api_key="", timeout=timeout, extra_payload=payload
    )


def strong_config(
    model: str = router_spec.STRONG_MODEL,
    base_url: str = router_spec.STRONG_BASE_URL,
    key_env: str = router_spec.STRONG_KEY_ENV,
    timeout: int = spec7.REQUEST_TIMEOUT_SECONDS,
) -> llm_client.ClientConfig:
    location = llm_client.inference_location(base_url)
    api_key = "" if location == spec7.LOCATION_LOCAL else llm_client.read_api_key(key_env)
    return llm_client.ClientConfig(
        model=model, base_url=base_url, api_key=api_key, timeout=timeout, extra_payload=None
    )


def answer_text_of(decision: pipeline.Decision) -> str:
    for sample in decision.raw_samples:
        if sample:
            return sample
    return decision.reason


def derive_status(decision: pipeline.Decision) -> str:
    blocking = guards.has_hard_violation(list(decision.violations))
    return pipeline.resolve_status(
        decision.route is not None, False, False, decision.confidence_final, blocking
    )


def should_escalate_pre(case_text: str, policy: RoutePolicy) -> List[str]:
    if not policy.enabled(router_spec.E_RISK):
        return []
    if pipeline.detect_risk_markers(case_text):
        return [router_spec.E_RISK]
    return []


def route_severity(route: Optional[str]) -> int:
    if route not in spec7.SEVERITY:
        return router_spec.NO_ROUTE_SEVERITY
    return spec7.SEVERITY[route]


def is_risk_conflict(case_text: str, cheap_decision: pipeline.Decision, ceiling: int) -> bool:
    if not pipeline.detect_risk_markers(case_text):
        return False
    return route_severity(cheap_decision.route) <= ceiling


def should_escalate_post(
    case_text: str, cheap_decision: pipeline.Decision, policy: RoutePolicy
) -> List[str]:
    reasons: List[str] = []
    if policy.enabled(router_spec.E_CONFLICT):
        if is_risk_conflict(case_text, cheap_decision, policy.conflict_ceiling):
            reasons.append(router_spec.E_CONFLICT)
    if policy.enabled(router_spec.E_CONF):
        if cheap_decision.confidence_final < policy.confidence_threshold:
            reasons.append(router_spec.E_CONF)
    if policy.enabled(router_spec.E_STATUS):
        if derive_status(cheap_decision) in (spec7.STATUS_UNSURE, spec7.STATUS_FAIL):
            reasons.append(router_spec.E_STATUS)
    if policy.enabled(router_spec.E_GUARD):
        if guards.has_hard_violation(list(cheap_decision.violations)):
            reasons.append(router_spec.E_GUARD)
    if policy.enabled(router_spec.E_LEN):
        length = len(answer_text_of(cheap_decision))
        if length < router_spec.MIN_ANSWER_CHARS or length > router_spec.MAX_ANSWER_CHARS:
            reasons.append(router_spec.E_LEN)
    return reasons


def call_level(
    case_text: str, case_id: str, client_cfg: llm_client.ClientConfig
) -> pipeline.Decision:
    return pipeline.run_baseline(case_text, client_cfg, case_id)


def outcome_of_single(
    case_id: str,
    policy: RoutePolicy,
    decision: pipeline.Decision,
    level: str,
    started: float,
) -> RouteOutcome:
    is_strong = level == router_spec.LEVEL_STRONG
    return RouteOutcome(
        case_id=case_id,
        strategy=policy.strategy,
        final_route=decision.route,
        final_status=derive_status(decision),
        final_confidence=decision.confidence_final,
        escalated=is_strong,
        escalation_reasons=[],
        cheap_decision=None if is_strong else decision,
        strong_decision=decision if is_strong else None,
        calls_cheap=0 if is_strong else decision.calls,
        calls_strong=decision.calls if is_strong else 0,
        latency_ms=int((time.time() - started) * 1000),
        cost_usd=round(decision.cost_usd, 8),
        error=decision.error,
    )


def merge_errors(parts: List[Optional[str]]) -> Optional[str]:
    texts = [part for part in parts if part]
    if not texts:
        return None
    return "; ".join(texts)


def route_one(
    case_text: str,
    case_id: str,
    policy: RoutePolicy,
    cheap_cfg: llm_client.ClientConfig,
    strong_cfg: llm_client.ClientConfig,
) -> RouteOutcome:
    started = time.time()
    try:
        if policy.force_strong:
            strong = call_level(case_text, case_id, strong_cfg)
            return outcome_of_single(
                case_id, policy, strong, router_spec.LEVEL_STRONG, started
            )

        pre_reasons = should_escalate_pre(case_text, policy)
        if pre_reasons:
            strong = call_level(case_text, case_id, strong_cfg)
            outcome = outcome_of_single(
                case_id, policy, strong, router_spec.LEVEL_STRONG, started
            )
            outcome.escalation_reasons = pre_reasons
            return outcome

        cheap = call_level(case_text, case_id, cheap_cfg)
        post_reasons = should_escalate_post(case_text, cheap, policy)
        if not post_reasons:
            return outcome_of_single(
                case_id, policy, cheap, router_spec.LEVEL_CHEAP, started
            )

        strong = call_level(case_text, case_id, strong_cfg)
        fallback_note: Optional[str] = None
        final = strong
        if strong.route is None and cheap.route is not None:
            fallback_note = "сильная модель не дала маршрут, итог взят от дешёвой"
            final = cheap
        return RouteOutcome(
            case_id=case_id,
            strategy=policy.strategy,
            final_route=final.route,
            final_status=derive_status(final),
            final_confidence=final.confidence_final,
            escalated=True,
            escalation_reasons=post_reasons,
            cheap_decision=cheap,
            strong_decision=strong,
            calls_cheap=cheap.calls,
            calls_strong=strong.calls,
            latency_ms=int((time.time() - started) * 1000),
            cost_usd=round(cheap.cost_usd + strong.cost_usd, 8),
            error=merge_errors([cheap.error, strong.error, fallback_note]),
        )
    except Exception as unexpected_error:
        return RouteOutcome(
            case_id=case_id,
            strategy=policy.strategy,
            final_route=None,
            final_status=spec7.STATUS_FAIL,
            latency_ms=int((time.time() - started) * 1000),
            error="сбой роутинга кейса: %s" % unexpected_error,
        )
