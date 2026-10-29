"""Phase 6: Multi-Horizon Strategy Research (H=6, H=24, H=48).

Strict Quantitative Methodology:
1. Horizons:
   - H=6: 30 minutes (reference baseline)
   - H=24: 2 hours (nominal intraday swing)
   - H=48: 4 hours (nominal macro session swing)
2. Labeling:
   - Separate causal label calculation per horizon.
   - Boundary purging of 1 + H tail bars.
   - Weekend-crossing purge.
3. Training-Period Walk-Forward Cross-Validation (2021-2024):
   - Fold 1: Train 2021 -> Eval 2022
   - Fold 2: Train 2021-2022 -> Eval 2023
   - Fold 3: Train 2021-2023 -> Eval 2024
   - Preprocessing and Logistic Regression fit strictly on fold train.
4. Primary Mode:
   - non_overlapping (single-position capacity=1).
   - overlapping (for baseline comparison).
5. Cost Models:
   - Baseline Costs ($0.20 spread, $0.05 slippage, $0.10 comm round-turn).
   - Harsher Costs ($0.40 spread, $0.10 slippage, $0.10 comm round-turn).
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.economic_evaluator import EconomicEvaluator
from treading_ai.models.baselines import LogisticRegressionBaseline
from treading_ai.models.evaluation import evaluate_classification
from treading_ai.models.labeling import CausalDirectionalLabeler
from treading_ai.models.walk_forward import ChronologicalWalkForward
from treading_ai.policies.selective import (
    SelectiveTradingPolicy,
    compute_brier_scores,
)


def run_horizon_research() -> Dict[str, Any]:
    print("=" * 80)
    print("PHASE 6: MULTI-HORIZON RESEARCH ON TRAINING FOLDS (2021-2024)")
    print("=" * 80)

    train_path = Path("data/features/XAUUSD_M5_features_train.parquet")
    print(f"Loading training data from {train_path}...")
    train_df = pd.read_parquet(train_path)

    non_feature_cols = {"timestamp", "open", "high", "low", "close"}
    feature_cols = [c for c in train_df.columns if c not in non_feature_cols]

    horizons = [6, 24, 48]
    BASELINE_ATR = 1.153
    BASELINE_RANGE = 1.050

    cost_model_baseline = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
    cost_model_harsher = ExecutionCostModel(base_spread_usd=0.40, base_slippage_usd=0.10)

    candidate_thresholds = [None, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 1.0]

    all_results: List[Dict[str, Any]] = []

    for H in horizons:
        print("\n" + "=" * 80)
        print(f"EVALUATING HORIZON H={H} ({H * 5} minutes / {H / 12:.1f} hours)")
        print("=" * 80)

        # 1. Generate causal labels for horizon H
        labeler = CausalDirectionalLabeler(horizon=H)
        train_labels = labeler.compute_labels(train_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
        valid_mask = ~train_labels["is_purged"].to_numpy()

        n_valid = int(np.sum(valid_mask))
        n_purged = int(np.sum(~valid_mask))
        print(f"Horizon H={H}: Valid={n_valid:,}, Purged={n_purged:,} (Purge rate: {n_purged / len(train_df):.2%})")

        eval_base = EconomicEvaluator(
            cost_model=cost_model_baseline,
            horizon=H,
            baseline_atr=BASELINE_ATR,
            baseline_candle_range=BASELINE_RANGE,
        )
        eval_harsh = EconomicEvaluator(
            cost_model=cost_model_harsher,
            horizon=H,
            baseline_atr=BASELINE_ATR,
            baseline_candle_range=BASELINE_RANGE,
        )

        cwf = ChronologicalWalkForward(n_splits=3, horizon=H)
        folds = cwf.split_by_years(train_df, timestamp_col="timestamp")

        for fold in folds:
            print(f"\n--- Horizon H={H} | Fold {fold.fold_id} (Eval Year: {fold.eval_start_time.year}) ---")
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

            # Fit Logistic Regression strictly on fold train
            model = LogisticRegressionBaseline(max_iter=300, random_state=42)
            model.fit(X_tr, y_tr)

            ev_probas = model.predict_proba(X_ev)
            brier = compute_brier_scores(y_ev, ev_probas)

            # Evaluate unfiltered classification
            unfilt_preds = model.predict(X_ev)
            cls_metrics = evaluate_classification(
                y_true=y_ev,
                y_pred=unfilt_preds,
                model_name=f"LR_H{H}_Fold{fold.fold_id}",
                split_name=f"Fold_{fold.fold_id}_Eval",
                n_total=fold.n_eval,
                n_purged=int(np.sum(~f_ev_mask)),
            )

            print(f"  Unfiltered Acc: {cls_metrics.accuracy:.4f} | BalAcc: {cls_metrics.balanced_accuracy:.4f} | "
                  f"Macro-F1: {cls_metrics.macro_f1:.4f} | Brier: {brier['brier_total']:.4f}")

            # Test candidate thresholds in primary non_overlapping mode and baseline overlapping mode
            for th in candidate_thresholds:
                th_label = "Unfiltered" if th is None else ("No-Trade" if th >= 1.0 else f"Thresh={th:.2f}")

                for mode in ["non_overlapping", "overlapping"]:
                    policy = SelectiveTradingPolicy(
                        model=model,
                        threshold=th,
                        mode=mode,
                        holding_horizon=H,
                    )
                    policy_out = policy.generate_signals(X_ev)

                    econ_b, _ = eval_base.evaluate(
                        df=fold_eval_df,
                        signals=policy_out.signals,
                        model_name=f"LR_H{H}_{th_label}_{mode}",
                        scenario_name="Baseline Costs",
                        mask=f_ev_mask,
                    )

                    econ_h, _ = eval_harsh.evaluate(
                        df=fold_eval_df,
                        signals=policy_out.signals,
                        model_name=f"LR_H{H}_{th_label}_{mode}",
                        scenario_name="Harsher Costs",
                        mask=f_ev_mask,
                    )

                    rec = {
                        "horizon": H,
                        "fold_id": fold.fold_id,
                        "eval_year": fold.eval_start_time.year,
                        "threshold": th,
                        "threshold_label": th_label,
                        "mode": mode,
                        "accuracy": cls_metrics.accuracy,
                        "balanced_accuracy": cls_metrics.balanced_accuracy,
                        "macro_f1": cls_metrics.macro_f1,
                        "brier_score": brier["brier_total"],
                        "n_eligible_signals": policy_out.n_eligible_signals,
                        "n_capacity_rejected": policy_out.n_capacity_rejected,
                        "n_executed_entries": econ_b.n_executed_entries,
                        "n_completed_trades": econ_b.n_completed_trades,
                        "market_exposure_pct": econ_b.market_exposure_pct,
                        "trade_frequency_pct": econ_b.trade_frequency_pct,
                        "gross_pnl_usd": econ_b.gross_pnl_usd,
                        "net_pnl_usd": econ_b.net_pnl_usd,
                        "total_spread_usd": econ_b.total_spread_usd,
                        "total_slippage_usd": econ_b.total_slippage_usd,
                        "total_commission_usd": econ_b.total_commission_usd,
                        "total_friction_usd": econ_b.total_friction_usd,
                        "avg_net_pnl_per_trade": econ_b.avg_net_pnl_per_trade,
                        "median_net_pnl_per_trade": econ_b.median_net_pnl_per_trade,
                        "win_rate_gross": econ_b.win_rate_gross,
                        "win_rate_net": econ_b.win_rate_net,
                        "profit_factor_gross": econ_b.profit_factor_gross,
                        "profit_factor_net": econ_b.profit_factor_net,
                        "max_drawdown_usd": econ_b.max_drawdown_usd,
                        "harsher_net_pnl_usd": econ_h.net_pnl_usd,
                        "harsher_profit_factor_net": econ_h.profit_factor_net,
                        "long_net_pnl": econ_b.long_net_pnl,
                        "short_net_pnl": econ_b.short_net_pnl,
                    }
                    all_results.append(rec)

                    if mode == "non_overlapping":
                        print(
                            f"  {th_label:12s} | Trades: {econ_b.n_completed_trades:5d} | Exp: {econ_b.market_exposure_pct:5.2f}% | "
                            f"Gross: ${econ_b.gross_pnl_usd:>8.2f} | Net: ${econ_b.net_pnl_usd:>8.2f} | "
                            f"PF: {econ_b.profit_factor_net:5.3f} | WinNet: {econ_b.win_rate_net:5.2%} | MedNet: ${econ_b.median_net_pnl_per_trade:>6.2f}"
                        )

    return {"horizon_research_results": all_results}


if __name__ == "__main__":
    out = run_horizon_research()
    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase6_horizon_walk_forward_research.json"
    with open(out_file, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nPhase 6 Horizon research exported to {out_file}")
