"""Phase 11 Controlled Research Experiment: Rigorous Validation of Market Structure and Adaptive Learning.

Strict Scientific Discipline:
1. Data: 2021-2024 Training partition ONLY (260,821 M5 bars).
2. Protected Partition Isolation: Zero access to 2025 Validation or frozen 2026 Test partitions.
3. Chronological Walk-Forward: 3 expanding-window folds with 1+H boundary purging.
4. Candidates Evaluated:
   - Candidate A: No-Trade Baseline ($0.00)
   - Candidate B: Existing Incumbent Strategy (Logistic Regression on 191 technical features, threshold=0.60)
   - Candidate C: Strategy with Market Structure (Logistic Regression on 233 features including 42 MS features, threshold=0.60)
   - Candidate D: Adaptive Challenger (Retrained ML + Causal Error-Gated Structural & Regime Policy)
5. Execution Friction: Causal bid-only model (Spread $0.20 base, Slippage $0.05, Commission $0.05)
6. Spread Stress Scenario: 1.5x Spread ($0.30 base), 1.5x Slippage ($0.075), Commission ($0.05)
7. Outputs: JSON report at reports/phase11_experiment_results.json
"""

import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from treading_ai.audit.error_classifier import ErrorCategory, TradeErrorClassifier
from treading_ai.audit.trade_journal import DecisionJournal
from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.economic_evaluator import EconomicEvaluator, EconomicMetrics
from treading_ai.config import FEATURES_DATA_DIR, REPORTS_DIR
from treading_ai.features.market_structure import MarketStructureEngine
from treading_ai.governance.challenger_gate import ChallengerGate, PromotionCriteria
from treading_ai.governance.model_registry import ModelRegistry
from treading_ai.models.baselines import LogisticRegressionBaseline
from treading_ai.models.labeling import CausalDirectionalLabeler
from treading_ai.models.walk_forward import ChronologicalWalkForward, WalkForwardFold
from treading_ai.policies.selective import SelectiveTradingPolicy, compute_brier_scores

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Phase11Experiment")


def run_phase11_experiment() -> Dict[str, Any]:
    logger.info("=" * 80)
    logger.info("PHASE 11: CONTROLLED RESEARCH EXPERIMENT & VALIDATION")
    logger.info("=" * 80)

    t0_start = time.time()

    # 1. Load 2021-2024 Training Data
    train_path = FEATURES_DATA_DIR / "XAUUSD_M5_features_train.parquet"
    logger.info("Loading 2021-2024 training dataset from %s...", train_path)
    train_df = pd.read_parquet(train_path)
    n_rows = len(train_df)
    logger.info("Loaded %d rows with %d columns.", n_rows, len(train_df.columns))

    # Base feature isolation (191 original features)
    non_feature_cols = {"timestamp", "open", "high", "low", "close", "volume"}
    base_feature_cols = [c for c in train_df.columns if c not in non_feature_cols]
    logger.info("Identified %d base technical/time feature columns.", len(base_feature_cols))

    # 2. Extract 42 Causal Market Structure Features
    logger.info("Extracting 42 causal market structure features across full dataset...")
    t0_ms = time.time()
    ms_engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)
    ms_features_df = ms_engine.compute_features(train_df, atr_series=train_df["atr_14"])
    ms_feature_cols = list(ms_features_df.columns)
    logger.info("Computed %d market structure features in %.2fs (NaNs: %d).", len(ms_feature_cols), time.time() - t0_ms, ms_features_df.isna().sum().sum())

    # Combined dataset with market structure
    augmented_df = pd.concat([train_df, ms_features_df], axis=1)
    all_feature_cols = base_feature_cols + ms_feature_cols
    logger.info("Total augmented feature count: %d columns.", len(all_feature_cols))

    # 3. Generate Causal Directional Labels (Horizon H=24 bars = 2 hours)
    HORIZON = 24
    BASELINE_ATR = 1.153
    BASELINE_RANGE = 1.050

    logger.info("Generating Phase 3 causal directional labels (H=%d)...", HORIZON)
    labeler = CausalDirectionalLabeler(horizon=HORIZON)
    labels_df = labeler.compute_labels(train_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    valid_mask = ~labels_df["is_purged"].to_numpy()
    logger.info("Labels generated: %d valid rows, %d purged rows (boundary/weekend).", np.sum(valid_mask), np.sum(~valid_mask))

    # 4. Set up Walk-Forward Folds (3 Expanding Folds)
    cwf = ChronologicalWalkForward(n_splits=3, horizon=HORIZON)
    folds = cwf.split_by_years(train_df, timestamp_col="timestamp")
    logger.info("Configured %d chronological expanding folds inside 2021-2024.", len(folds))

    # 5. Set up Cost Models and Evaluators
    cost_model_base = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
    cost_model_stress = ExecutionCostModel(base_spread_usd=0.30, base_slippage_usd=0.075)

    eval_base = EconomicEvaluator(cost_model=cost_model_base, horizon=HORIZON, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    eval_stress = EconomicEvaluator(cost_model=cost_model_stress, horizon=HORIZON, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)

    # Containers for results across folds
    results = {
        "candidate_a_notrade": {"folds": [], "net_pnl_base": 0.0, "net_pnl_stress": 0.0, "trades": 0, "pf": 0.0, "win_rate": 0.0, "drawdown": 0.0},
        "candidate_b_incumbent": {"folds": [], "net_pnl_base": 0.0, "net_pnl_stress": 0.0, "trades": 0, "gross_pnl": 0.0, "friction": 0.0, "pf": 0.0, "win_rate": 0.0, "drawdown": 0.0, "brier": 0.0},
        "candidate_c_market_structure": {"folds": [], "net_pnl_base": 0.0, "net_pnl_stress": 0.0, "trades": 0, "gross_pnl": 0.0, "friction": 0.0, "pf": 0.0, "win_rate": 0.0, "drawdown": 0.0, "brier": 0.0},
        "candidate_d_adaptive_challenger": {"folds": [], "net_pnl_base": 0.0, "net_pnl_stress": 0.0, "trades": 0, "gross_pnl": 0.0, "friction": 0.0, "pf": 0.0, "win_rate": 0.0, "drawdown": 0.0, "brier": 0.0},
    }

    # 6. Execute Fold-by-Fold Evaluation
    for fold in folds:
        logger.info("-" * 80)
        logger.info(
            "FOLD %d: Train %s to %s (%d rows) -> Eval %s to %s (%d rows)",
            fold.fold_id,
            fold.train_start_time.strftime("%Y-%m-%d"),
            fold.train_end_time.strftime("%Y-%m-%d"),
            fold.n_train,
            fold.eval_start_time.strftime("%Y-%m-%d"),
            fold.eval_end_time.strftime("%Y-%m-%d"),
            fold.n_eval,
        )

        f_tr_mask = valid_mask[fold.train_indices]
        f_ev_mask = valid_mask[fold.eval_indices]

        # Training data
        tr_clean_indices = fold.train_indices[f_tr_mask]
        X_tr_base = train_df.iloc[tr_clean_indices][base_feature_cols]
        X_tr_all = augmented_df.iloc[tr_clean_indices][all_feature_cols]
        y_tr = labels_df.iloc[tr_clean_indices]["target_class"].to_numpy(dtype=int)

        # Full evaluation slice (for EconomicEvaluator)
        ev_df = train_df.iloc[fold.eval_indices].copy().reset_index(drop=True)
        ev_aug_df = augmented_df.iloc[fold.eval_indices].copy().reset_index(drop=True)

        X_ev_base = ev_df[base_feature_cols]
        X_ev_all = ev_aug_df[all_feature_cols]
        y_ev_true = labels_df.iloc[fold.eval_indices]["target_class"].to_numpy(dtype=int)

        # --- CANDIDATE A: No-Trade Baseline ---
        sigs_a = np.zeros(len(ev_df), dtype=int)
        metrics_a_base, _ = eval_base.evaluate(ev_df, sigs_a)
        metrics_a_stress, _ = eval_stress.evaluate(ev_df, sigs_a)
        results["candidate_a_notrade"]["folds"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": metrics_a_base.net_pnl_usd,
            "net_pnl_stress": metrics_a_stress.net_pnl_usd,
            "trades": metrics_a_base.n_completed_trades,
            "profit_factor": metrics_a_base.profit_factor_net,
        })

        # --- CANDIDATE B: Existing Incumbent Strategy (Logistic Regression on 191 base features) ---
        logger.info("Fitting Candidate B (Incumbent) on %d samples with %d features...", len(X_tr_base), len(base_feature_cols))
        model_b = LogisticRegressionBaseline(max_iter=300, random_state=42)
        model_b.fit(X_tr_base, y_tr)
        policy_b = SelectiveTradingPolicy(model=model_b, threshold=0.60, mode="non_overlapping", holding_horizon=HORIZON)
        out_b = policy_b.generate_signals(X_ev_base)
        sigs_b = out_b.signals

        metrics_b_base, _ = eval_base.evaluate(ev_df, sigs_b)
        metrics_b_stress, _ = eval_stress.evaluate(ev_df, sigs_b)
        brier_b = compute_brier_scores(y_ev_true[f_ev_mask], out_b.probabilities[f_ev_mask])

        results["candidate_b_incumbent"]["folds"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": metrics_b_base.net_pnl_usd,
            "net_pnl_stress": metrics_b_stress.net_pnl_usd,
            "gross_pnl": metrics_b_base.gross_pnl_usd,
            "friction": metrics_b_base.total_friction_usd,
            "trades": metrics_b_base.n_completed_trades,
            "profit_factor": metrics_b_base.profit_factor_net,
            "win_rate": metrics_b_base.win_rate_net,
            "drawdown": metrics_b_base.max_drawdown_usd,
            "brier_score": brier_b.get("brier_total", 0.0),
        })
        logger.info(
            "Candidate B Fold %d: Trades=%d, Net PnL=$%.2f/oz, PF=%.3f, WinRate=%.1f%%, DD=$%.2f/oz",
            fold.fold_id,
            metrics_b_base.n_completed_trades,
            metrics_b_base.net_pnl_usd,
            metrics_b_base.profit_factor_net,
            metrics_b_base.win_rate_net * 100,
            metrics_b_base.max_drawdown_usd,
        )

        # --- CANDIDATE C: Strategy with Market Structure Features (All 232 features) ---
        logger.info("Fitting Candidate C (Market Structure ML) on %d samples with %d features...", len(X_tr_all), len(all_feature_cols))
        model_c = LogisticRegressionBaseline(max_iter=300, random_state=42)
        model_c.fit(X_tr_all, y_tr)
        policy_c = SelectiveTradingPolicy(model=model_c, threshold=0.60, mode="non_overlapping", holding_horizon=HORIZON)
        out_c = policy_c.generate_signals(X_ev_all)
        sigs_c = out_c.signals

        metrics_c_base, _ = eval_base.evaluate(ev_df, sigs_c)
        metrics_c_stress, _ = eval_stress.evaluate(ev_df, sigs_c)
        brier_c = compute_brier_scores(y_ev_true[f_ev_mask], out_c.probabilities[f_ev_mask])

        results["candidate_c_market_structure"]["folds"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": metrics_c_base.net_pnl_usd,
            "net_pnl_stress": metrics_c_stress.net_pnl_usd,
            "gross_pnl": metrics_c_base.gross_pnl_usd,
            "friction": metrics_c_base.total_friction_usd,
            "trades": metrics_c_base.n_completed_trades,
            "profit_factor": metrics_c_base.profit_factor_net,
            "win_rate": metrics_c_base.win_rate_net,
            "drawdown": metrics_c_base.max_drawdown_usd,
            "brier_score": brier_c.get("brier_total", 0.0),
        })
        logger.info(
            "Candidate C Fold %d: Trades=%d, Net PnL=$%.2f/oz, PF=%.3f, WinRate=%.1f%%, DD=$%.2f/oz",
            fold.fold_id,
            metrics_c_base.n_completed_trades,
            metrics_c_base.net_pnl_usd,
            metrics_c_base.profit_factor_net,
            metrics_c_base.win_rate_net * 100,
            metrics_c_base.max_drawdown_usd,
        )

        # --- CANDIDATE D: Adaptive Challenger (Retrained ML + Causal Error-Gated Structural & Regime Policy) ---
        raw_sigs_d = model_c.predict(X_ev_all)
        probas_d = model_c.predict_proba(X_ev_all)
        p_long = probas_d[:, 2]
        p_short = probas_d[:, 0]

        rolling_med_atr = ev_aug_df["atr_14"].rolling(288, min_periods=10).median()
        atr_arr = ev_aug_df["atr_14"].to_numpy()
        med_atr_arr = rolling_med_atr.to_numpy()
        trend_state_arr = ev_aug_df["ms_trend_state"].to_numpy()

        filtered_sigs_d = np.zeros(len(ev_df), dtype=int)
        for idx in range(len(ev_df)):
            # Probability threshold hurdle
            if p_long[idx] >= 0.60:
                candidate_dir = 1
            elif p_short[idx] >= 0.60:
                candidate_dir = -1
            else:
                candidate_dir = 0

            if candidate_dir == 0:
                continue

            # Causal Rule 1: Regime Gating (Suppress if low volatility compression)
            cur_med = med_atr_arr[idx] if not np.isnan(med_atr_arr[idx]) else atr_arr[idx]
            if atr_arr[idx] < cur_med * 0.90:
                continue  # Suppress trade in compression

            # Causal Rule 2: Structural Trend Alignment (No counter-trend trading)
            if candidate_dir == 1 and trend_state_arr[idx] == -1:
                continue  # Suppress buying in confirmed bearish trend
            if candidate_dir == -1 and trend_state_arr[idx] == 1:
                continue  # Suppress selling in confirmed bullish trend

            filtered_sigs_d[idx] = candidate_dir

        # Enforce non-overlapping capacity control for H bars
        sigs_d = np.zeros(len(ev_df), dtype=int)
        lockout = 0
        for idx in range(len(ev_df)):
            if lockout > 0:
                lockout -= 1
                continue
            if filtered_sigs_d[idx] != 0:
                sigs_d[idx] = filtered_sigs_d[idx]
                lockout = HORIZON

        metrics_d_base, _ = eval_base.evaluate(ev_df, sigs_d)
        metrics_d_stress, _ = eval_stress.evaluate(ev_df, sigs_d)
        brier_d = compute_brier_scores(y_ev_true[f_ev_mask], probas_d[f_ev_mask])

        results["candidate_d_adaptive_challenger"]["folds"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": metrics_d_base.net_pnl_usd,
            "net_pnl_stress": metrics_d_stress.net_pnl_usd,
            "gross_pnl": metrics_d_base.gross_pnl_usd,
            "friction": metrics_d_base.total_friction_usd,
            "trades": metrics_d_base.n_completed_trades,
            "profit_factor": metrics_d_base.profit_factor_net,
            "win_rate": metrics_d_base.win_rate_net,
            "drawdown": metrics_d_base.max_drawdown_usd,
            "brier_score": brier_d.get("brier_total", 0.0),
        })
        logger.info(
            "Candidate D Fold %d: Trades=%d, Net PnL=$%.2f/oz, PF=%.3f, WinRate=%.1f%%, DD=$%.2f/oz",
            fold.fold_id,
            metrics_d_base.n_completed_trades,
            metrics_d_base.net_pnl_usd,
            metrics_d_base.profit_factor_net,
            metrics_d_base.win_rate_net * 100,
            metrics_d_base.max_drawdown_usd,
        )

    # 7. Aggregate Across Folds
    for cand_key in ["candidate_a_notrade", "candidate_b_incumbent", "candidate_c_market_structure", "candidate_d_adaptive_challenger"]:
        c_folds = results[cand_key]["folds"]
        tot_net_base = sum(f["net_pnl_base"] for f in c_folds)
        tot_net_stress = sum(f["net_pnl_stress"] for f in c_folds)
        tot_trades = sum(f["trades"] for f in c_folds)
        tot_gross = sum(f.get("gross_pnl", 0.0) for f in c_folds)
        tot_friction = sum(f.get("friction", 0.0) for f in c_folds)

        results[cand_key]["net_pnl_base"] = tot_net_base
        results[cand_key]["net_pnl_stress"] = tot_net_stress
        results[cand_key]["trades"] = tot_trades
        results[cand_key]["gross_pnl"] = tot_gross
        results[cand_key]["friction"] = tot_friction

        # Weighted win rate and profit factor
        if tot_trades > 0:
            results[cand_key]["win_rate"] = float(np.mean([f["win_rate"] for f in c_folds]))
            results[cand_key]["drawdown"] = float(max(f["drawdown"] for f in c_folds))
            results[cand_key]["net_expectancy"] = tot_net_base / tot_trades

            # Aggregate PF
            gross_losses = tot_friction + max(0.0, -tot_gross)
            gross_wins = max(0.0, tot_gross)
            results[cand_key]["pf"] = (gross_wins / gross_losses) if gross_losses > 0 else 0.0
            if "brier_score" in c_folds[0]:
                results[cand_key]["brier"] = float(np.mean([f["brier_score"] for f in c_folds]))
        else:
            results[cand_key]["win_rate"] = 0.0
            results[cand_key]["drawdown"] = 0.0
            results[cand_key]["net_expectancy"] = 0.0
            results[cand_key]["pf"] = 0.0

    # 8. ChallengerGate Formal Evaluation
    gate = ChallengerGate(PromotionCriteria(
        min_net_expectancy=0.0,
        min_profit_factor=1.0,
        min_trades_count=25,
        max_drawdown_tolerance=1.10,
        min_improvement_net_pnl=50.0,
        stress_spread_multiplier=1.5,
    ))

    incumbent_summary = {
        "net_pnl": results["candidate_b_incumbent"]["net_pnl_base"],
        "profit_factor": results["candidate_b_incumbent"]["pf"],
        "trade_count": results["candidate_b_incumbent"]["trades"],
        "max_drawdown": results["candidate_b_incumbent"]["drawdown"],
        "stress_net_pnl": results["candidate_b_incumbent"]["net_pnl_stress"],
        "fold_pnls": [f["net_pnl_base"] for f in results["candidate_b_incumbent"]["folds"]],
    }

    challenger_summary = {
        "net_pnl": results["candidate_d_adaptive_challenger"]["net_pnl_base"],
        "profit_factor": results["candidate_d_adaptive_challenger"]["pf"],
        "trade_count": results["candidate_d_adaptive_challenger"]["trades"],
        "max_drawdown": results["candidate_d_adaptive_challenger"]["drawdown"],
        "fold_pnls": [f["net_pnl_base"] for f in results["candidate_d_adaptive_challenger"]["folds"]],
    }
    stress_summary = {
        "net_pnl": results["candidate_d_adaptive_challenger"]["net_pnl_stress"],
    }

    gate_decision = gate.evaluate(
        challenger_metrics=challenger_summary,
        incumbent_metrics=incumbent_summary,
        stress_metrics=stress_summary,
    )

    logger.info("=" * 80)
    logger.info("PHASE 11 GATE DECISION: %s", gate_decision.recommendation)
    logger.info("Rejection reasons: %s", gate_decision.rejection_reasons)
    logger.info("=" * 80)

    experiment_report = {
        "experiment_name": "Phase 11 Controlled Research & Learning Validation",
        "dataset": "2021-2024 Training Data Only",
        "total_rows": n_rows,
        "holding_horizon_bars": HORIZON,
        "n_walk_forward_folds": len(folds),
        "results": results,
        "gate_scorecard": gate_decision.scorecard,
        "gate_rejection_reasons": gate_decision.rejection_reasons,
        "gate_recommendation": gate_decision.recommendation,
        "total_elapsed_seconds": time.time() - t0_start,
    }

    out_file = REPORTS_DIR / "phase11_experiment_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(experiment_report, f, indent=2)
    logger.info("Saved full Phase 11 experiment output to %s", out_file)

    return experiment_report


if __name__ == "__main__":
    run_phase11_experiment()
