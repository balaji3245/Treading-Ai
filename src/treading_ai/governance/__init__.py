"""Governance package for Treading-AI.

Provides model registry, versioning, rollback, pre-registered challenger gates,
and adaptive error-driven learning workflows.
"""

from treading_ai.governance.adaptive_learner import (
    AdaptiveLearner,
    CorrectiveHypothesis,
    ErrorClusterAnalysis,
    LearningStepResult,
)
from treading_ai.governance.challenger_gate import (
    ChallengerGate,
    GateDecision,
    PromotionCriteria,
)
from treading_ai.governance.model_registry import ModelMetadata, ModelRegistry

__all__ = [
    "ModelRegistry",
    "ModelMetadata",
    "ChallengerGate",
    "GateDecision",
    "PromotionCriteria",
    "AdaptiveLearner",
    "ErrorClusterAnalysis",
    "CorrectiveHypothesis",
    "LearningStepResult",
]
