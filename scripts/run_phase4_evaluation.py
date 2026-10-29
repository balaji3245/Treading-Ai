"""Phase 4 Comprehensive Baseline Modeling and Evaluation Script.

Executes:
1. Walk-Forward Expanding-Window Cross-Validation (3 folds inside Train: 2021-2024).
2. Out-of-Sample Validation Split Evaluation (2025).
3. Economic Backtesting with Baseline Costs and Harsher Costs (2x spread, 2x slippage).
4. Full classification & financial metric reporting.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.economic_evaluator import EconomicEvaluator
from treading_ai.models.baselines import (
    MajorityClassBaseline,
    DirectionalHeuristicBaseline,
    LogisticRegressionBaseline,
    RandomForestBaseline,
)
from treading_ai.models.evaluation import evaluate_classification
from treading_ai.models.labeling import CausalDirectionalLabeler
from treading_ai.models.walk_forward import ChronologicalWalkForward


def main() -> None:
    print("=" * 80)
    print("PHASE 4: BASELINE MODELING AND OUT-OF-SAMPLE EVALUATION")
    print("=" * 80)

    # 1. Load Parquet datasets
    train_path = Path("data/features/XAUUSD_M5_features_train.parquet")
    val_path = Path("data/features/XAUUSD_M5_features_val.parquet")

    print(f"Loading training data from {train_path}...")
    train_df = pd.read_parquet(train_path)
    print(f"Loading validation data from {val_path}...")
    val_df = pd.read_parquet(val_path)

    print(f"Train shape: {train_df.shape}, Val shape: {val_df.shape}")

    # 2. Compute Causal Directional Labels (Horizon H=6, ~30 mins)
    HORIZON = 6
    BASELINE_ATR = 1.153
    BASELINE_RANGE = 1.050

    labeler = CausalDirectionalLabeler(horizon=HORIZON)
    print("\nGenerating Phase 3 causal labels...")
    train_labels = labeler.compute_labels(train_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    val_labels = labeler.compute_labels(val_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)

    # Feature column isolation: exclude timestamps, ohlc, and any targets
    non_feature_cols = {"timestamp", "open", "high", "low", "close"}
    feature_cols = [c for c in train_df.columns if c not in non_feature_cols]
    print(f"Isolated {len(feature_cols)} clean feature columns.")

    # Masks for valid (non-purged) observations
    train_valid_mask = ~train_labels["is_purged"].to_numpy()
    val_valid_mask = ~val_labels["is_purged"].to_numpy()

    print(f"Train: Total={len(train_df):,}, Valid={np.sum(train_valid_mask):,}, Purged={np.sum(~train_valid_mask):,}")
    print(f"Val:   Total={len(val_df):,}, Valid={np.sum(val_valid_mask):,}, Purged={np.sum(~val_valid_mask):,}")

    # Cost models: Baseline vs Harsher
    cost_model_baseline = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
    cost_model_harsher = ExecutionCostModel(base_spread_usd=0.40, base_slippage_usd=0.10)

    econ_eval_baseline = EconomicEvaluator(
        cost_model=cost_model_baseline,
        horizon=HORIZON,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )
    econ_eval_harsher = EconomicEvaluator(
        cost_model=cost_model_harsher,
        horizon=HORIZON,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )

    # =========================================================================
    # PART 1: WALK-FORWARD CROSS-VALIDATION ON TRAINING SPLIT (2021-2024)
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 6: WALK-FORWARD EXPANDING-WINDOW VALIDATION (TRAIN 2021-2024)")
    print("=" * 80)

    cwf = ChronologicalWalkForward(n_splits=3, horizon=HORIZON)
    folds = cwf.split_by_years(train_df, timestamp_col="timestamp")

    models_factory = {
        "Majority-Class": lambda: MajorityClassBaseline(),
        "Directional Heuristic": lambda: DirectionalHeuristicBaseline(),
        "Logistic Regression": lambda: LogisticRegressionBaseline(max_iter=300, random_state=42),
        "Random Forest": lambda: RandomForestBaseline(n_estimators=100, max_depth=10, min_samples_leaf=50, random_state=42),
    }

    walk_forward_results = []

    for fold in folds:
        print(f"\n--- Fold {fold.fold_id} ---")
        print(f"Train Period: {fold.train_start_time.strftime('%Y-%m-%d')} to {fold.train_end_time.strftime('%Y-%m-%d')} ({fold.n_train:,} bars)")
        print(f"Purged Boundary: {fold.n_purged_boundary} bars (horizon={HORIZON})")
        print(f"Eval Period:  {fold.eval_start_time.strftime('%Y-%m-%d')} to {fold.eval_end_time.strftime('%Y-%m-%d')} ({fold.n_eval:,} bars)")

        # Extract fold data
        fold_train_df = train_df.iloc[fold.train_indices]
        fold_eval_df = train_df.iloc[fold.eval_indices]

        fold_train_labels = train_labels.iloc[fold.train_indices]
        fold_eval_labels = train_labels.iloc[fold.eval_indices]

        # Valid masks within fold
        f_train_mask = ~fold_train_labels["is_purged"].to_numpy()
        f_eval_mask = ~fold_eval_labels["is_purged"].to_numpy()

        X_tr = fold_train_df.loc[f_train_mask, feature_cols]
        y_tr = fold_train_labels.loc[f_train_mask, "target_class"].to_numpy(dtype=int)

        X_ev = fold_eval_df.loc[f_eval_mask, feature_cols]
        y_ev = fold_eval_labels.loc[f_eval_mask, "target_class"].to_numpy(dtype=int)

        print(f"Fold {fold.fold_id} Clean Train Samples: {len(X_tr):,}, Eval Samples: {len(X_ev):,}")

        for model_name, factory in models_factory.items():
            model = factory()
            model.fit(X_tr, y_tr)
            preds = model.predict(X_ev)

            # Classification metrics
            cls_metrics = evaluate_classification(
                y_true=y_ev,
                y_pred=preds,
                model_name=model_name,
                split_name=f"Fold_{fold.fold_id}_Eval",
                n_total=fold.n_eval,
                n_purged=int(np.sum(~f_eval_mask)),
            )

            # Economic backtest on fold eval split
            econ_metrics, _ = econ_eval_baseline.evaluate(
                df=fold_eval_df,
                signals=preds,
                model_name=model_name,
                scenario_name=f"Fold_{fold.fold_id}_Baseline_Costs",
                mask=f_eval_mask,
            )

            print(
                f"  {model_name:24s} | Acc: {cls_metrics.accuracy:.4f} | BalAcc: {cls_metrics.balanced_accuracy:.4f} | "
                f"Macro-F1: {cls_metrics.macro_f1:.4f} | Net PnL: ${econ_metrics.net_pnl_usd:+9.2f} | PF: {econ_metrics.profit_factor_net:5.3f} | WinRate: {econ_metrics.win_rate_net:.2%}"
            )

            walk_forward_results.append({
                "fold_id": fold.fold_id,
                "model_name": model_name,
                "classification": cls_metrics.to_dict(),
                "economic": econ_metrics.to_dict(),
            })

    # =========================================================================
    # PART 2: FULL OUT-OF-SAMPLE VALIDATION SPLIT (2025)
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 4 & 5: OUT-OF-SAMPLE VALIDATION EVALUATION (YEAR 2025)")
    print("=" * 80)

    # Fit all models on the COMPLETE training set (2021-2024)
    X_train_full = train_df.loc[train_valid_mask, feature_cols]
    y_train_full = train_labels.loc[train_valid_mask, "target_class"].to_numpy(dtype=int)

    X_val_full = val_df.loc[val_valid_mask, feature_cols]
    y_val_full = val_labels.loc[val_valid_mask, "target_class"].to_numpy(dtype=int)

    val_results = []

    for model_name, factory in models_factory.items():
        print(f"\n--- Training {model_name} on Full Train Split (2021-2024) ---")
        model = factory()
        model.fit(X_train_full, y_train_full)

        val_preds = model.predict(X_val_full)

        # Classification evaluation
        cls_metrics = evaluate_classification(
            y_true=y_val_full,
            y_pred=val_preds,
            model_name=model_name,
            split_name="Validation_2025",
            n_total=len(val_df),
            n_purged=int(np.sum(~val_valid_mask)),
        )

        # Economic evaluation: Baseline Costs
        econ_base, _ = econ_eval_baseline.evaluate(
            df=val_df,
            signals=val_preds,
            model_name=model_name,
            scenario_name="Baseline Costs",
            mask=val_valid_mask,
        )

        # Economic evaluation: Harsher Costs
        econ_harsh, _ = econ_eval_harsher.evaluate(
            df=val_df,
            signals=val_preds,
            model_name=model_name,
            scenario_name="Harsher Costs (2x)",
            mask=val_valid_mask,
        )

        print(cls_metrics.summary_table())
        print(econ_base.summary_table())
        print(econ_harsh.summary_table())

        val_results.append({
            "model_name": model_name,
            "classification": cls_metrics.to_dict(),
            "economic_baseline": econ_base.to_dict(),
            "economic_harsher": econ_harsh.to_dict(),
        })

    # Save summary artifact
    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase4_baseline_evaluation.json"
    with open(out_file, "w") as f:
        json.dump({
            "walk_forward_results": walk_forward_results,
            "validation_results": val_results,
        }, f, indent=2)
    print(f"\nResults successfully exported to {out_file}")


if __name__ == "__main__":
    main()
