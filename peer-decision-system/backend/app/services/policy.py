"""Pure policy evaluation: GoF Strategy without HTTP or database dependencies."""
from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class PolicyContext:
    high_impact: bool
    affected_team: bool
    yes_ratio: float
    affected_support: float | None
    participants: int
    expert_reviews: int
    description_length: int


class RuleStrategy(Protocol):
    def fails(self, context: PolicyContext, threshold: float) -> bool: ...


class HighSupport:
    def fails(self, context: PolicyContext, threshold: float) -> bool:
        return context.high_impact and context.yes_ratio < threshold


class MinoritySupport:
    def fails(self, context: PolicyContext, threshold: float) -> bool:
        return context.affected_team and (
            context.affected_support is None or context.affected_support < threshold
        )


class Quorum:
    def fails(self, context: PolicyContext, threshold: float) -> bool:
        return context.participants < threshold


class ExpertReviewRequired:
    def fails(self, context: PolicyContext, threshold: float) -> bool:
        return context.high_impact and context.expert_reviews < threshold


class DescriptionLength:
    def fails(self, context: PolicyContext, threshold: float) -> bool:
        return context.description_length < threshold


class PolicyEngine:
    def __init__(self, strategies: Mapping[str, RuleStrategy]):
        self._strategies = dict(strategies)

    def evaluate(self, kind: str, threshold: float, severity: str,
                 context: PolicyContext) -> str:
        strategy = self._strategies.get(kind)
        # Unknown persisted rules must never silently approve a decision.
        if strategy is None:
            return 'BLOCKED'
        return severity if strategy.fails(context, threshold) else 'COMPLIANT'


policy_engine = PolicyEngine({
    'HIGH_SUPPORT': HighSupport(),
    'MINORITY_SUPPORT': MinoritySupport(),
    'QUORUM': Quorum(),
    'EXPERT_REVIEW': ExpertReviewRequired(),
    'DESCRIPTION_LENGTH': DescriptionLength(),
})
