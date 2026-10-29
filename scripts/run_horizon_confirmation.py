"""Phase 6: Multi-Horizon Locked Policy Confirmation Run on Validation (2025).

Strict Protocol:
- Models fit strictly on the full 4-year Training partition (2021-2024).
- Locked candidate policies selected solely from training-period walk-forward evidence:
  * H=6:  LR Thresh=0.60 (Non-Overlapping)
  * H=24: LR Thresh=0.70 (Non-Overlapping)
  * H=48: LR Thresh=0.70 (Non-Overlapping)
- Evaluated on 2025 Validation split.
- Executed ONCE. Zero repeated tuning on 2025.
- 2026 Test partition remains completely untouched and frozen.
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
from treading_ai.policies.selective import (
    SelectiveTradingPolicy,
    compute_brier_scores,
)


def run_confirmation() -> None:
    print("=" * 80)
    print("PHASE 6: ONE-TIME MULTI-HORIZON CONFIRMATION RUN (VALIDATION 2025)")
    print("=" * 80)

    train_path = Path("data/features/XAUUSD_M5_features_train.parquet")
    val_path = Path("data/features/XAUUSD_M5_features_val.parquet")

    print(f"Loading full training data from {train_path}...")
    train_df = pd.read_parquet(train_path)
    print(f"Loading validation data from {val_path}...")
    val_df = pd.read_parquet(val_path)

    non_feature_cols = {"timestamp", "open", "high", "low", "close"}
    feature_cols = [c for c in train_df.columns if c not in non_feature_cols]

    horizons = [6, 24, 48]
    BASELINE_ATR = 1.153
    BASELINE_RANGE = 1.050

    cost_model_baseline = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
    cost_model_harsher = ExecutionCostModel(base_spread_usd=0.40, base_slippage_usd=0.10)

    # Locked policy candidate per horizon
    locked_configs = {
        6: {"threshold": 0.60, "mode": "non_overlapping"},
        24: {"threshold": 0.70, "mode": "non_overlapping"},
        48: {"threshold": 0.70, "mode": "non_overlapping"},
    }

    confirmation_results: List[Dict[str, Any]] = []

    for H in horizons:
        print("\n" + "=" * 80)
        print(f"CONFIRMATION FOR HORIZON H={H} ({H * 5}m / {H / 12:.1f}h)")
        print("=" * 80)

        # 1. Generate causal labels for horizon H
        labeler = CausalDirectionalLabeler(horizon=H)
        train_labels = labeler.compute_labels(train_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
        val_labels = labeler.compute_labels(val_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)

        tr_valid_mask = ~train_labels["is_purged"].to_numpy()
        val_valid_mask = ~val_labels["is_purged"].to_numpy()

        X_train = train_df.loc[tr_valid_mask, feature_cols]
        y_train = train_labels.loc[tr_valid_mask, "target_class"].to_numpy(dtype=int)

        X_val = val_df.loc[val_valid_mask, feature_cols]
        y_val = val_labels.loc[val_valid_mask, "target_class"].to_numpy(dtype=int)

        print(f"Train Valid: {len(X_train):,}, Purged: {np.sum(~tr_valid_mask):,}")
        print(f"Val Valid:   {len(X_val):,}, Purged: {np.sum(~val_valid_mask):,}")

        # 2. Fit Logistic Regression on full 2021-2024 training split
        print(f"Fitting Logistic Regression on Train for H={H}...")
        model = LogisticRegressionBaseline(max_iter=300, random_state=42)
        model.fit(X_train, y_train)

        val_probas = model.predict_proba(X_val)
        brier = compute_brier_scores(y_val, val_probas)
        print(f"Validation Brier Score (H={H}): {brier['brier_total']:.4f}")

        # Classification metrics (unfiltered)
        val_preds_unfilt = model.predict(X_val)
        cls_metrics = evaluate_classification(
            y_true=y_val,
            y_pred=val_preds_unfilt,
            model_name=f"LR_H{H}_Validation",
            split_name="Validation_2025",
            n_total=len(val_df),
            n_purged=int(np.sum(~val_valid_mask)),
        )
        print(f"Classification: Acc={cls_metrics.accuracy:.4f}, BalAcc={cls_metrics.balanced_accuracy:.4f}, Macro-F1={cls_metrics.macro_f1:.4f}")

        eval_b = EconomicEvaluator(cost_model_baseline, horizon=H, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
        eval_h = EconomicEvaluator(cost_model_harsher, horizon=H, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)

        # Policies to evaluate on Validation:
        # 1. The Locked Active Policy
        # 2. Unfiltered baseline (non_overlapping)
        # 3. No-trade baseline
        cfg = locked_configs[H]
        policies = [
            (f"Locked Policy: LR H={H} Thresh={cfg['threshold']} (Non-Overlapping)", cfg["threshold"], cfg["mode"]),
            (f"Reference: LR H={H} Unfiltered (Non-Overlapping)", None, "non_overlapping"),
            (f"Reference: LR H={H} Unfiltered (Overlapping)", None, "overlapping"),
            (f"Reference: No-Trade Baseline H={H}", 1.0, "non_overlapping"),
        ]

        for p_name, th, mode in policies:
            policy = SelectiveTradingPolicy(model=model, threshold=th, mode=mode, holding_horizon=H)
            p_out = policy.generate_signals(X_val)

            econ_base, _ = eval_b.evaluate(
                df=val_df,
                signals=p_out.signals,
                model_name=p_name,
                scenario_name="Baseline Costs",
                mask=val_valid_mask,
            )

            econ_harsh, _ = eval_h.evaluate(
                df=val_df,
                signals=p_out.signals,
                model_name=p_name,
                scenario_name="Harsher Costs (2x)",
                mask=val_valid_mask,
            )

            print("\n" + econ_base.summary_table())
            print(f"  [Harsher Costs 2x] Net PnL: ${econ_harsh.net_pnl_usd:+,.2f}/oz | Net PF: {econ_harsh.profit_factor_net:.3f} | Net Win: {econ_harsh.win_rate_net:.2%}")

            confirmation_results.append({
                "horizon": H,
                "policy_name": p_name,
                "threshold": th,
                "mode": mode,
                "classification": cls_metrics.to_dict(),
                "brier_score": brier["brier_total"],
                "baseline_metrics": econ_base.to_dict(),
                "harsher_metrics": econ_harsh.to_dict(),
            })

    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase6_horizon_locked_confirmation.json"
    with open(out_file, "w") as f:
        json.dump({"confirmation_results": confirmation_results}, f, indent=2)
    print(f"\nPhase 6 Horizon confirmation results exported to {out_file}")


if __name__ == "__main__":
    run_confirmation()
