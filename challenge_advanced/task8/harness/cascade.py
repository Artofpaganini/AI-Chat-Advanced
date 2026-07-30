"""Каскад task8 для живого сервера: те же правила эскалации, но уровни считает пайплайн триажа.

router.route_one водит уровни через pipeline.run_baseline - один вызов, четыре маршрута, никаких
проверок версии 2. Серверу этого мало: язык, кризисный гейт, поддержка родителя и данные ребёнка
живут в pipeline_v2, и терять их из-за роутинга нельзя. Поэтому здесь повторён только порядок
уровней, а сами правила эскалации импортированы из router без единой правки - policy_for,
should_escalate_pre, should_escalate_post. Коды и пороги берутся из router_spec.

Как уровень считается, каскад не знает: вызывающая сторона передаёт run_level, который по имени
уровня возвращает готовое решение. Всё, что касается промпта, профиля ребёнка и критика, остаётся
в сервере, здесь - только выбор уровня.

Два случая наверх не уходят по построению.

Первый - решение, принятое без единого вызова. Пустой ввод, чужой язык и кризисный гейт pipeline_v2
разбирает до сети, calls там ноль. Дешёвый уровень в этих случаях ничего не отвечал, спорить не с
чем, и ответ вообще не приписывается уровню: answered_by = none.

Второй - кризис, найденный уже в ответе модели. Маршрут там выставлен детерминированно, и отправить
такой случай наверх значит дать сильной модели право его отменить. Платить за возможность понизить
экстренный маршрут - плохой размен.

Порядок уровней и запасной вариант «сильная не дала маршрут - берём ответ дешёвой» повторяют
router.route_one. Статус, в отличие от route_one, не пересчитывается: у пайплайна свой статус, он
учитывает кризис, вердикт критика и подъём по правилу безопасности, и затирать его нельзя.

Отдельная тонкость - что считать нарушением формата для E_GUARD. В замере task8 дешёвый уровень
считал run_baseline: один вызов, критика нет вовсе, и в violations лежали только претензии к самому
триажному ответу. Здесь уровень считает пайплайн, и в тот же список попадают претензии к ответу
критика. Разница не косметическая: локальный критик на 1.7B ни разу не выдал разборчивый вердикт, и
E_GUARD на неотфильтрованном списке срабатывал на каждом кейсе с признаком риска - то есть
превращался в E_RISK, правило, от которого task8 как раз ушёл. Поэтому перед проверкой коды критика
из списка убираются, и правило видит ровно тот вход, на котором его мерили.
"""

import dataclasses
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import router
import router_spec

sys.path.insert(0, router_spec.TASK7_HARNESS_DIR)

import pipeline
import spec7

CRITIC_VIOLATION_CODES = frozenset(spec7.CRITIC_CODES)

ROUTING_OFF = "off"
ROUTING_SMART = "smart"
ROUTING_MODES = (ROUTING_OFF, ROUTING_SMART)

ROUTING_STRATEGIES = {ROUTING_SMART: router_spec.STRATEGY_ROUTE_SMART}

ROUTING_TITLES = {
    ROUTING_OFF: "каскада нет, каждый запрос идёт в основную модель",
    ROUTING_SMART: "каскад: сначала дешёвый уровень, наверх по расхождению, формату и уверенности",
}

LEVEL_NONE = "none"

STRONG_NO_ROUTE_NOTE = "сильная модель не дала маршрут, итог взят от дешёвой"

RunLevel = Callable[[str], pipeline.Decision]


@dataclass
class CascadeOutcome:
    decision: pipeline.Decision
    answered_by: str
    escalated: bool = False
    escalation_reasons: List[str] = field(default_factory=list)
    calls_cheap: int = 0
    calls_strong: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    note: Optional[str] = None


def policy_for(routing: str, confidence_threshold: float, conflict_ceiling: int) -> router.RoutePolicy:
    strategy = ROUTING_STRATEGIES[routing]
    return router.policy_for(strategy, confidence_threshold, conflict_ceiling)


def answered_without_model(decision: pipeline.Decision) -> bool:
    return decision.calls == 0


def crisis_locked(decision: pipeline.Decision) -> bool:
    return bool(getattr(decision, "crisis", False))


def without_critic_violations(decision: pipeline.Decision) -> pipeline.Decision:
    kept = [code for code in decision.violations if code not in CRITIC_VIOLATION_CODES]
    if len(kept) == len(decision.violations):
        return decision
    return dataclasses.replace(decision, violations=kept)


def elapsed_ms(started: float) -> int:
    return int((time.time() - started) * 1000)


def single_level_outcome(
    decision: pipeline.Decision, level: str, started: float, reasons: Optional[List[str]] = None
) -> CascadeOutcome:
    is_strong = level == router_spec.LEVEL_STRONG
    answered_by = LEVEL_NONE if answered_without_model(decision) else level
    return CascadeOutcome(
        decision=decision,
        answered_by=answered_by,
        escalated=is_strong,
        escalation_reasons=list(reasons or []),
        calls_cheap=0 if is_strong else decision.calls,
        calls_strong=decision.calls if is_strong else 0,
        cost_usd=round(decision.cost_usd, 8),
        latency_ms=elapsed_ms(started),
    )


def run_cascade(case_text: str, policy: router.RoutePolicy, run_level: RunLevel) -> CascadeOutcome:
    started = time.time()
    pre_reasons = router.should_escalate_pre(case_text, policy)
    if policy.force_strong or pre_reasons:
        strong = run_level(router_spec.LEVEL_STRONG)
        return single_level_outcome(strong, router_spec.LEVEL_STRONG, started, pre_reasons)

    cheap = run_level(router_spec.LEVEL_CHEAP)
    if answered_without_model(cheap) or crisis_locked(cheap):
        return single_level_outcome(cheap, router_spec.LEVEL_CHEAP, started)

    post_reasons = router.should_escalate_post(
        case_text, without_critic_violations(cheap), policy
    )
    if not post_reasons:
        return single_level_outcome(cheap, router_spec.LEVEL_CHEAP, started)

    strong = run_level(router_spec.LEVEL_STRONG)
    final = strong
    note: Optional[str] = None
    if strong.route is None and cheap.route is not None:
        final = cheap
        note = STRONG_NO_ROUTE_NOTE
    return CascadeOutcome(
        decision=final,
        answered_by=router_spec.LEVEL_CHEAP if note else router_spec.LEVEL_STRONG,
        escalated=True,
        escalation_reasons=post_reasons,
        calls_cheap=cheap.calls,
        calls_strong=strong.calls,
        cost_usd=round(cheap.cost_usd + strong.cost_usd, 8),
        latency_ms=elapsed_ms(started),
        note=note,
    )
