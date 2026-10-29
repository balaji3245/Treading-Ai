"""Phase 5 Locked Policy One-Time Confirmation Run on Validation (2025).

Strict Protocol:
- Models fit strictly on full Training split (2021-2024).
- Evaluated on 2025 Validation split.
- Executed ONCE. Zero repeated tuning or threshold search on 2025.
- 2026 Test partition remains completely untouched and frozen.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.economic_evaluator import EconomicEvaluator
from treading_ai.models.baselines import (
    LogisticRegressionBaseline,
    RandomForestBaseline,
)
from treading_ai.models.labeling import CausalDirectionalLabeler
from treading_ai.policies.selective import (
    SelectiveTradingPolicy,
    compute_brier_scores,
)


def run_confirmation() -> None:
    print("=" * 80)
    print("PHASE 5: ONE-TIME LOCKED POLICY CONFIRMATION RUN (VALIDATION 2025)")
    print("=" * 80)

    train_path = Path("data/features/XAUUSD_M5_features_train.parquet")
    val_path = Path("data/features/XAUUSD_M5_features_val.parquet")

    print(f"Loading full training data from {train_path}...")
    train_df = pd.read_parquet(train_path)
    print(f"Loading validation data from {val_path}...")
    val_df = pd.read_parquet(val_path)

    HORIZON = 6
    BASELINE_ATR = 1.153
    BASELINE_RANGE = 1.050

    labeler = CausalDirectionalLabeler(horizon=HORIZON)
    train_labels = labeler.compute_labels(train_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    val_labels = labeler.compute_labels(val_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)

    non_feature_cols = {"timestamp", "open", "high", "low", "close"}
    feature_cols = [c for c in train_df.columns if c not in non_feature_cols]

    train_valid_mask = ~train_labels["is_purged"].to_numpy()
    val_valid_mask = ~val_labels["is_purged"].to_numpy()

    X_train = train_df.loc[train_valid_mask, feature_cols]
    y_train = train_labels.loc[train_valid_mask, "target_class"].to_numpy(dtype=int)

    X_val = val_df.loc[val_valid_mask, feature_cols]
    y_val = val_labels.loc[val_valid_mask, "target_class"].to_numpy(dtype=int)

    cost_model_baseline = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
    cost_model_harsher = ExecutionCostModel(base_spread_usd=0.40, base_slippage_usd=0.10)

    eval_base = EconomicEvaluator(
        cost_model=cost_model_baseline,
        horizon=HORIZON,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )
    eval_harsh = EconomicEvaluator(
        cost_model=cost_model_harsher,
        horizon=HORIZON,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )

    # 1. Fit models on complete Training dataset (2021-2024)
    print(f"\nFitting Logistic Regression on full training split ({len(X_train):,} samples)...")
    lr = LogisticRegressionBaseline(max_iter=300, random_state=42)
    lr.fit(X_train, y_train)

    print(f"Fitting Random Forest on full training split ({len(X_train):,} samples)...")
    rf = RandomForestBaseline(n_estimators=100, max_depth=10, min_samples_leaf=50, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)

    # 2. Probability Calibration Check on Validation
    lr_probas = lr.predict_proba(X_val)
    rf_probas = rf.predict_proba(X_val)

    brier_lr = compute_brier_scores(y_val, lr_probas)
    brier_rf = compute_brier_scores(y_val, rf_probas)

    print(f"\nValidation Probability Calibration:")
    print(f"  Logistic Regression Brier: Total={brier_lr['brier_total']:.4f} "
          f"(Short={brier_lr['brier_short']:.4f}, Neutral={brier_lr['brier_neutral']:.4f}, Long={brier_lr['brier_long']:.4f})")
    print(f"  Random Forest Brier:       Total={brier_rf['brier_total']:.4f} "
          f"(Short={brier_rf['brier_short']:.4f}, Neutral={brier_rf['brier_neutral']:.4f}, Long={brier_rf['brier_long']:.4f})")

    # 3. Define the Locked Policies for One-Time Confirmation
    # Locked Policy: Logistic Regression, Threshold 0.60, Non-Overlapping (Single Position)
    # Comparative Reference Policies:
    # - LR Thresh=0.60 Overlapping
    # - RF Thresh=0.50 Non-Overlapping
    # - Unfiltered LR Baseline
    # - Unfiltered RF Baseline
    # - No-Trade Baseline
    confirmation_policies = [
        ("Locked Policy: LR Thresh=0.60 (Non-Overlapping)", lr, 0.60, "non_overlapping"),
        ("Reference: LR Thresh=0.60 (Overlapping)", lr, 0.60, "overlapping"),
        ("Reference: RF Thresh=0.50 (Non-Overlapping)", rf, 0.50, "non_overlapping"),
        ("Reference: LR Unfiltered (Overlapping)", lr, None, "overlapping"),
        ("Reference: RF Unfiltered (Overlapping)", rf, None, "overlapping"),
        ("Reference: No-Trade Baseline", lr, 1.0, "non_overlapping"),
    ]

    confirmation_results = []

    print("\n" + "=" * 80)
    print("ONE-TIME 2025 CONFIRMATION RESULTS")
    print("=" * 80)

    for pol_name, model, th, mode in confirmation_policies:
        policy = SelectiveTradingPolicy(model=model, threshold=th, mode=mode, holding_horizon=HORIZON)
        out = policy.generate_signals(X_val)

        econ_b, _ = eval_base.evaluate(
            df=val_df,
            signals=out.signals,
            model_name=pol_name,
            scenario_name="Baseline Costs",
            mask=val_valid_mask,
        )

        econ_h, _ = eval_harsh.evaluate(
            df=val_df,
            signals=out.signals,
            model_name=pol_name,
            scenario_name="Harsher Costs (2x)",
            mask=val_valid_mask,
        )

        print("\n" + econ_b.summary_table())
        print(f"  [Harsher Costs 2x] Net PnL: ${econ_h.net_pnl_usd:+,.2f}/oz | Net PF: {econ_h.profit_factor_net:.3f} | Net Win: {econ_h.win_rate_net:.2%}")

        confirmation_results.append({
            "policy_name": pol_name,
            "threshold": th,
            "mode": mode,
            "baseline_metrics": econ_b.to_dict(),
            "harsher_metrics": econ_h.to_dict(),
        })

    # Save to report artifact
    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase5_locked_confirmation.json"
    with open(out_file, "w") as f:
        json.dump({
            "brier_lr": brier_lr,
            "brier_rf": brier_rf,
            "confirmation_results": confirmation_results,
        }, f, indent=2)
    print(f"\nConfirmation results successfully exported to {out_file}")


if __name__ == "__main__":
    run_confirmation()
