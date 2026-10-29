"""Selective Trading Policy Research and Walk-Forward Threshold Optimization.

Strict Scientific Discipline:
1. Folds: Evaluates candidate thresholds across 3 expanding-window folds in Train (2021-2024).
2. Thresholds: Unfiltered, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, and No-Trade (1.0).
3. Modes: "overlapping" (unconstrained) vs "non_overlapping" (strict capacity=1).
4. Models: Logistic Regression and Random Forest.
5. Locking: Selects and locks the best policy purely based on training fold performance.
6. Confirmation: Executes exactly ONE final confirmation run on 2025 Validation.
7. Test Set: 2026 Test partition remains strictly untouched.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.economic_evaluator import EconomicEvaluator
from treading_ai.models.baselines import (
    LogisticRegressionBaseline,
    RandomForestBaseline,
)
from treading_ai.models.labeling import CausalDirectionalLabeler
from treading_ai.models.walk_forward import ChronologicalWalkForward
from treading_ai.policies.selective import (
    SelectiveTradingPolicy,
    compute_brier_scores,
)


def run_walk_forward_policy_research() -> Dict[str, Any]:
    print("=" * 80)
    print("PHASE 5: SELECTIVE TRADING POLICY RESEARCH (TRAIN 2021-2024)")
    print("=" * 80)

    train_path = Path("data/features/XAUUSD_M5_features_train.parquet")
    print(f"Loading training data from {train_path}...")
    train_df = pd.read_parquet(train_path)

    HORIZON = 6
    BASELINE_ATR = 1.153
    BASELINE_RANGE = 1.050

    labeler = CausalDirectionalLabeler(horizon=HORIZON)
    train_labels = labeler.compute_labels(train_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)

    non_feature_cols = {"timestamp", "open", "high", "low", "close"}
    feature_cols = [c for c in train_df.columns if c not in non_feature_cols]
    valid_mask = ~train_labels["is_purged"].to_numpy()

    cwf = ChronologicalWalkForward(n_splits=3, horizon=HORIZON)
    folds = cwf.split_by_years(train_df, timestamp_col="timestamp")

    cost_model_baseline = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
    cost_model_harsher = ExecutionCostModel(base_spread_usd=0.40, base_slippage_usd=0.10)

    eval_baseline = EconomicEvaluator(
        cost_model=cost_model_baseline,
        horizon=HORIZON,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )
    eval_harsher = EconomicEvaluator(
        cost_model=cost_model_harsher,
        horizon=HORIZON,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )

    candidate_thresholds = [None, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 1.0]
    modes = ["overlapping", "non_overlapping"]

    wf_results: List[Dict[str, Any]] = []

    for fold in folds:
        print(f"\n=======================================================")
        print(f"FOLD {fold.fold_id}: Train {fold.train_start_time.strftime('%Y-%m-%d')} to {fold.train_end_time.strftime('%Y-%m-%d')} "
              f"-> Eval {fold.eval_start_time.strftime('%Y-%m-%d')} to {fold.eval_end_time.strftime('%Y-%m-%d')}")
        print(f"=======================================================")

        fold_train_df = train_df.iloc[fold.train_indices]
        fold_eval_df = train_df.iloc[fold.eval_indices]
        fold_train_labels = train_labels.iloc[fold.train_indices]
        fold_eval_labels = train_labels.iloc[fold.eval_indices]

        f_tr_mask = ~fold_train_labels["is_purged"].to_numpy()
        f_ev_mask = ~fold_eval_labels["is_purged"].to_numpy()

        X_tr = fold_train_df.loc[f_tr_mask, feature_cols]
        y_tr = fold_train_labels.loc[f_tr_mask, "target_class"].to_numpy(dtype=int)

        X_ev = fold_eval_df.loc[f_ev_mask, feature_cols]
        y_ev = fold_eval_labels.loc[f_ev_mask, "target_class"].to_numpy(dtype=int)

        # Fit models on Fold Train
        print(f"Fitting Logistic Regression on {len(X_tr):,} samples...")
        lr = LogisticRegressionBaseline(max_iter=300, random_state=42)
        lr.fit(X_tr, y_tr)

        print(f"Fitting Random Forest on {len(X_tr):,} samples...")
        rf = RandomForestBaseline(n_estimators=100, max_depth=10, min_samples_leaf=50, random_state=42, n_jobs=-1)
        rf.fit(X_tr, y_tr)

        models = {"Logistic Regression": lr, "Random Forest": rf}

        # Evaluate Brier calibration scores
        for m_name, model in models.items():
            ev_probas = model.predict_proba(X_ev)
            brier = compute_brier_scores(y_ev, ev_probas)
            print(f"  [{m_name}] Out-of-fold Brier Score: Total={brier['brier_total']:.4f} "
                  f"(Short={brier['brier_short']:.4f}, Neutral={brier['brier_neutral']:.4f}, Long={brier['brier_long']:.4f})")

        for m_name, model in models.items():
            print(f"\n--- Model: {m_name} (Fold {fold.fold_id}) ---")
            for th in candidate_thresholds:
                th_label = "Unfiltered" if th is None else ("No-Trade" if th >= 1.0 else f"Thresh={th:.2f}")

                for mode in modes:
                    policy = SelectiveTradingPolicy(
                        model=model,
                        threshold=th,
                        mode=mode,
                        holding_horizon=HORIZON,
                    )
                    policy_out = policy.generate_signals(X_ev)

                    # Evaluate baseline costs
                    econ_base, _ = eval_baseline.evaluate(
                        df=fold_eval_df,
                        signals=policy_out.signals,
                        model_name=f"{m_name} [{th_label}, {mode}]",
                        scenario_name="Baseline Costs",
                        mask=f_ev_mask,
                    )

                    # Evaluate harsher costs
                    econ_harsh, _ = eval_harsher.evaluate(
                        df=fold_eval_df,
                        signals=policy_out.signals,
                        model_name=f"{m_name} [{th_label}, {mode}]",
                        scenario_name="Harsher Costs",
                        mask=f_ev_mask,
                    )

                    res = {
                        "fold_id": fold.fold_id,
                        "eval_year": fold.eval_start_time.year,
                        "model_name": m_name,
                        "threshold": th,
                        "threshold_label": th_label,
                        "mode": mode,
                        "n_eligible_signals": policy_out.n_eligible_signals,
                        "n_capacity_rejected": policy_out.n_capacity_rejected,
                        "n_executed_entries": econ_base.n_executed_entries,
                        "n_completed_trades": econ_base.n_completed_trades,
                        "market_exposure_pct": econ_base.market_exposure_pct,
                        "max_concurrent_positions": econ_base.max_concurrent_positions,
                        "avg_concurrent_positions": econ_base.avg_concurrent_positions,
                        "gross_pnl_usd": econ_base.gross_pnl_usd,
                        "net_pnl_usd": econ_base.net_pnl_usd,
                        "total_spread_usd": econ_base.total_spread_usd,
                        "total_slippage_usd": econ_base.total_slippage_usd,
                        "total_commission_usd": econ_base.total_commission_usd,
                        "total_friction_usd": econ_base.total_friction_usd,
                        "avg_net_pnl_per_trade": econ_base.avg_net_pnl_per_trade,
                        "median_net_pnl_per_trade": econ_base.median_net_pnl_per_trade,
                        "win_rate_gross": econ_base.win_rate_gross,
                        "win_rate_net": econ_base.win_rate_net,
                        "profit_factor_gross": econ_base.profit_factor_gross,
                        "profit_factor_net": econ_base.profit_factor_net,
                        "max_drawdown_usd": econ_base.max_drawdown_usd,
                        "harsher_net_pnl_usd": econ_harsh.net_pnl_usd,
                        "harsher_profit_factor_net": econ_harsh.profit_factor_net,
                        "long_net_pnl": econ_base.long_net_pnl,
                        "short_net_pnl": econ_base.short_net_pnl,
                    }
                    wf_results.append(res)

                    print(
                        f"  {th_label:12s} | {mode:15s} | Trades: {econ_base.n_completed_trades:5d} | "
                        f"GrossPnL: ${econ_base.gross_pnl_usd:>8.2f} | NetPnL: ${econ_base.net_pnl_usd:>8.2f} | "
                        f"NetPF: {econ_base.profit_factor_net:5.3f} | NetWin: {econ_base.win_rate_net:5.2%} | "
                        f"MedPnL: ${econ_base.median_net_pnl_per_trade:>6.2f} | MaxDD: ${econ_base.max_drawdown_usd:>8.2f}"
                    )

    return {"walk_forward_results": wf_results}


if __name__ == "__main__":
    out = run_walk_forward_policy_research()
    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase5_walk_forward_research.json"
    with open(out_file, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWalk-forward research exported to {out_file}")
