"""Persistent Decision and Trade Journal for XAUUSD Algorithmic Analysis.

This module provides persistent, queryable, versioned relational storage
for all market analysis decisions (BUY, SELL, NONE), entry assumptions,
invalidation levels, subsequent market excursions (MFE/MAE), realized PnL,
and post-trade error classifications.

Storage Engine: SQLite database with indexing and Parquet export.
"""

from dataclasses import asdict, dataclass, field
import datetime
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from treading_ai.audit.error_classifier import DiagnosticResult, TradeErrorClassifier
from treading_ai.config import REPORTS_DIR

logger = logging.getLogger(__name__)

DEFAULT_JOURNAL_DB_PATH = REPORTS_DIR / "decision_journal.db"


@dataclass
class JournalEntry:
    """Represents a complete decision and trade journal record."""
    decision_id: str
    timestamp: str  # ISO-8601 UTC string
    data_version: str
    feature_version: str
    model_version: str
    strategy_id: str
    decision: str  # 'BUY', 'SELL', 'NONE'
    predicted_direction: int  # 1, -1, 0
    confidence: float
    calibrated_prob: Optional[float]
    expected_horizon_bars: int
    entry_reference_price: float
    stop_loss_price: Optional[float]
    target_price: Optional[float]
    invalidation_price: Optional[float]
    market_regime: str
    session: str
    structure_state: str
    reasoning_summary: str
    feature_evidence_json: str  # JSON-encoded dictionary of supporting features
    # Outcome fields (populated when outcome matures)
    outcome_observed: bool = False
    outcome_timestamp: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # 'TARGET', 'STOP', 'TIME', 'INACTIVATION'
    bars_held: Optional[int] = None
    gross_pnl: Optional[float] = None
    estimated_friction: Optional[float] = None
    net_pnl: Optional[float] = None
    mfe: Optional[float] = None
    mae: Optional[float] = None
    is_failure: Optional[bool] = None
    primary_error_category: Optional[str] = None
    error_categories_json: Optional[str] = None
    post_outcome_diagnosis: Optional[str] = None
    corrective_hypothesis: Optional[str] = None


class DecisionJournal:
    """Persistent SQLite-backed Decision & Trade Journal."""

    def __init__(self, db_path: Union[str, Path] = DEFAULT_JOURNAL_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.error_classifier = TradeErrorClassifier()
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with WAL mode enabled for high-concurrency safety."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_database(self) -> None:
        """Create the schema and indexes if they do not exist."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_journal (
                    decision_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    data_version TEXT NOT NULL,
                    feature_version TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    predicted_direction INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    calibrated_prob REAL,
                    expected_horizon_bars INTEGER NOT NULL,
                    entry_reference_price REAL NOT NULL,
                    stop_loss_price REAL,
                    target_price REAL,
                    invalidation_price REAL,
                    market_regime TEXT NOT NULL,
                    session TEXT NOT NULL,
                    structure_state TEXT NOT NULL,
                    reasoning_summary TEXT NOT NULL,
                    feature_evidence_json TEXT NOT NULL,
                    outcome_observed INTEGER NOT NULL DEFAULT 0,
                    outcome_timestamp TEXT,
                    exit_price REAL,
                    exit_reason TEXT,
                    bars_held INTEGER,
                    gross_pnl REAL,
                    estimated_friction REAL,
                    net_pnl REAL,
                    mfe REAL,
                    mae REAL,
                    is_failure INTEGER,
                    primary_error_category TEXT,
                    error_categories_json TEXT,
                    post_outcome_diagnosis TEXT,
                    corrective_hypothesis TEXT
                );
                """
            )
            # Create indexes for performant historical queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dj_timestamp ON decision_journal(timestamp);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dj_model ON decision_journal(model_version);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dj_strategy ON decision_journal(strategy_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dj_decision ON decision_journal(decision);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dj_outcome ON decision_journal(outcome_observed);")

    def record_decision(
        self,
        decision_id: str,
        timestamp: Union[str, pd.Timestamp, datetime.datetime],
        data_version: str,
        feature_version: str,
        model_version: str,
        strategy_id: str,
        decision: str,  # 'BUY', 'SELL', 'NONE'
        predicted_direction: int,  # 1, -1, 0
        confidence: float,
        expected_horizon_bars: int,
        entry_reference_price: float,
        market_regime: str,
        session: str,
        structure_state: str,
        reasoning_summary: str,
        calibrated_prob: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        target_price: Optional[float] = None,
        invalidation_price: Optional[float] = None,
        feature_evidence: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record a newly formulated market decision with full contextual reasoning.

        Returns:
            The decision_id recorded.
        """
        ts_str = pd.to_datetime(timestamp).isoformat()

        def _json_serialize_helper(obj):
            if isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
                return float(obj)
            elif isinstance(obj, (np.bool_, bool)):
                return bool(obj)
            elif isinstance(obj, (pd.Timestamp, datetime.datetime)):
                return obj.isoformat()
            return str(obj)

        evidence_json = json.dumps(feature_evidence or {}, default=_json_serialize_helper)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO decision_journal (
                    decision_id, timestamp, data_version, feature_version, model_version,
                    strategy_id, decision, predicted_direction, confidence, calibrated_prob,
                    expected_horizon_bars, entry_reference_price, stop_loss_price,
                    target_price, invalidation_price, market_regime, session,
                    structure_state, reasoning_summary, feature_evidence_json, outcome_observed
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0
                );
                """,
                (
                    decision_id,
                    ts_str,
                    data_version,
                    feature_version,
                    model_version,
                    strategy_id,
                    decision,
                    predicted_direction,
                    float(confidence),
                    float(calibrated_prob) if calibrated_prob is not None else None,
                    int(expected_horizon_bars),
                    float(entry_reference_price),
                    float(stop_loss_price) if stop_loss_price is not None else None,
                    float(target_price) if target_price is not None else None,
                    float(invalidation_price) if invalidation_price is not None else None,
                    str(market_regime),
                    str(session),
                    str(structure_state),
                    str(reasoning_summary),
                    evidence_json,
                ),
            )
        return decision_id

    def record_outcome(
        self,
        decision_id: str,
        outcome_timestamp: Union[str, pd.Timestamp, datetime.datetime],
        exit_price: float,
        exit_reason: str,
        bars_held: int,
        gross_pnl: float,
        estimated_friction: float,
        net_pnl: float,
        mfe: float,
        mae: float,
        entry_atr: float,
        target_distance: Optional[float] = None,
        stop_distance: Optional[float] = None,
        max_candle_range: Optional[float] = None,
        is_rollover: bool = False,
    ) -> DiagnosticResult:
        """
        Record the observable market outcome for an earlier decision,
        running automatic error classification and hypothesis formulation.

        Returns:
            DiagnosticResult with assigned categories and hypothesis.
        """
        # Fetch existing decision context
        entry = self.get_decision(decision_id)
        if entry is None:
            raise KeyError(f"Decision ID '{decision_id}' not found in journal!")

        target_dist = target_distance
        if target_dist is None and entry.target_price is not None:
            target_dist = abs(entry.target_price - entry.entry_reference_price)

        stop_dist = stop_distance
        if stop_dist is None and entry.stop_loss_price is not None:
            stop_dist = abs(entry.stop_loss_price - entry.entry_reference_price)

        # Run automated diagnosis
        diag = self.error_classifier.classify_outcome(
            decision_id=decision_id,
            predicted_direction=entry.predicted_direction,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            total_friction=estimated_friction,
            mfe=mfe,
            mae=mae,
            entry_atr=entry_atr,
            confidence=entry.confidence,
            market_regime=entry.market_regime,
            exit_reason=exit_reason,
            target_distance=target_dist,
            stop_distance=stop_dist,
            max_candle_range=max_candle_range,
            is_rollover=is_rollover,
        )

        outcome_ts_str = pd.to_datetime(outcome_timestamp).isoformat()
        categories_json = json.dumps(diag.categories)

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE decision_journal SET
                    outcome_observed = 1,
                    outcome_timestamp = ?,
                    exit_price = ?,
                    exit_reason = ?,
                    bars_held = ?,
                    gross_pnl = ?,
                    estimated_friction = ?,
                    net_pnl = ?,
                    mfe = ?,
                    mae = ?,
                    is_failure = ?,
                    primary_error_category = ?,
                    error_categories_json = ?,
                    post_outcome_diagnosis = ?,
                    corrective_hypothesis = ?
                WHERE decision_id = ?;
                """,
                (
                    outcome_ts_str,
                    float(exit_price),
                    str(exit_reason),
                    int(bars_held),
                    float(gross_pnl),
                    float(estimated_friction),
                    float(net_pnl),
                    float(mfe),
                    float(mae),
                    1 if diag.is_failure else 0,
                    diag.primary_reason,
                    categories_json,
                    diag.explanation,
                    diag.corrective_hypothesis,
                    decision_id,
                ),
            )
        return diag

    def get_decision(self, decision_id: str) -> Optional[JournalEntry]:
        """Retrieve a single journal entry by its unique ID."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM decision_journal WHERE decision_id = ?;", (decision_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return JournalEntry(
                decision_id=row["decision_id"],
                timestamp=row["timestamp"],
                data_version=row["data_version"],
                feature_version=row["feature_version"],
                model_version=row["model_version"],
                strategy_id=row["strategy_id"],
                decision=row["decision"],
                predicted_direction=row["predicted_direction"],
                confidence=row["confidence"],
                calibrated_prob=row["calibrated_prob"],
                expected_horizon_bars=row["expected_horizon_bars"],
                entry_reference_price=row["entry_reference_price"],
                stop_loss_price=row["stop_loss_price"],
                target_price=row["target_price"],
                invalidation_price=row["invalidation_price"],
                market_regime=row["market_regime"],
                session=row["session"],
                structure_state=row["structure_state"],
                reasoning_summary=row["reasoning_summary"],
                feature_evidence_json=row["feature_evidence_json"],
                outcome_observed=bool(row["outcome_observed"]),
                outcome_timestamp=row["outcome_timestamp"],
                exit_price=row["exit_price"],
                exit_reason=row["exit_reason"],
                bars_held=row["bars_held"],
                gross_pnl=row["gross_pnl"],
                estimated_friction=row["estimated_friction"],
                net_pnl=row["net_pnl"],
                mfe=row["mfe"],
                mae=row["mae"],
                is_failure=bool(row["is_failure"]) if row["is_failure"] is not None else None,
                primary_error_category=row["primary_error_category"],
                error_categories_json=row["error_categories_json"],
                post_outcome_diagnosis=row["post_outcome_diagnosis"],
                corrective_hypothesis=row["corrective_hypothesis"],
            )

    def query(
        self,
        model_version: Optional[str] = None,
        strategy_id: Optional[str] = None,
        decision: Optional[str] = None,
        outcome_observed_only: bool = False,
    ) -> pd.DataFrame:
        """Query journal entries and return as a pandas DataFrame."""
        query = "SELECT * FROM decision_journal WHERE 1=1"
        params: List[Any] = []

        if model_version is not None:
            query += " AND model_version = ?"
            params.append(model_version)
        if strategy_id is not None:
            query += " AND strategy_id = ?"
            params.append(strategy_id)
        if decision is not None:
            query += " AND decision = ?"
            params.append(decision)
        if outcome_observed_only:
            query += " AND outcome_observed = 1"

        query += " ORDER BY timestamp ASC;"

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        return df

    def summarize_performance(self, model_version: Optional[str] = None) -> Dict[str, Any]:
        """Generate high-level aggregated performance and error breakdown metrics."""
        df = self.query(model_version=model_version, outcome_observed_only=True)
        if len(df) == 0:
            return {
                "total_decisions": 0,
                "matured_trades": 0,
                "net_pnl": 0.0,
                "profit_factor": 0.0,
                "win_rate": 0.0,
                "error_distribution": {},
            }

        trades_df = df[df["decision"].isin(["BUY", "SELL"])]
        if len(trades_df) == 0:
            return {
                "total_decisions": len(df),
                "matured_trades": 0,
                "net_pnl": 0.0,
                "profit_factor": 0.0,
                "win_rate": 0.0,
                "error_distribution": {},
            }

        wins = trades_df[trades_df["net_pnl"] > 0]
        losses = trades_df[trades_df["net_pnl"] < 0]

        total_net_pnl = float(trades_df["net_pnl"].sum())
        gross_profit = float(wins["net_pnl"].sum()) if len(wins) > 0 else 0.0
        gross_loss = abs(float(losses["net_pnl"].sum())) if len(losses) > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
        win_rate = len(wins) / len(trades_df) if len(trades_df) > 0 else 0.0

        # Aggregate error categories
        error_dist: Dict[str, int] = {}
        for row in losses["primary_error_category"].dropna():
            error_dist[row] = error_dist.get(row, 0) + 1

        return {
            "total_decisions": len(df),
            "matured_trades": len(trades_df),
            "total_net_pnl": total_net_pnl,
            "profit_factor": profit_factor,
            "win_rate": win_rate,
            "avg_mfe": float(trades_df["mfe"].mean()) if "mfe" in trades_df else 0.0,
            "avg_mae": float(trades_df["mae"].mean()) if "mae" in trades_df else 0.0,
            "error_distribution": error_dist,
        }

    def export_to_parquet(self, output_path: Union[str, Path]) -> Path:
        """Export the full decision journal table to a Parquet file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df = self.query()
        df.to_parquet(out, index=False)
        return out
