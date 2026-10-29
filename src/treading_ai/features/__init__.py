"""Feature engineering package for Treading-AI.

Provides leakage-free, multi-timeframe, and session-aware quantitative feature
extraction engines for algorithmic trading intelligence.
"""

from treading_ai.features.technical import TechnicalFeatureExtractor
from treading_ai.features.time_features import TimeFeatureExtractor
from treading_ai.features.multi_timeframe import MultiTimeframeAligner
from treading_ai.features.market_structure import MarketStructureEngine
from treading_ai.features.pipeline import FeaturePipeline

__all__ = [
    "TechnicalFeatureExtractor",
    "TimeFeatureExtractor",
    "MultiTimeframeAligner",
    "MarketStructureEngine",
    "FeaturePipeline",
]
