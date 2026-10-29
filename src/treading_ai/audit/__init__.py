"""Audit package for Treading-AI.

Provides persistent decision journaling, excursion tracking (MFE/MAE),
and evidence-based error classification taxonomy.
"""

from treading_ai.audit.error_classifier import (
    DiagnosticResult,
    ErrorCategory,
    TradeErrorClassifier,
)
from treading_ai.audit.trade_journal import DecisionJournal, JournalEntry

__all__ = [
    "DecisionJournal",
    "JournalEntry",
    "TradeErrorClassifier",
    "ErrorCategory",
    "DiagnosticResult",
]
