"""Phase 16: AI Model Capability Assessment & Benchmark Evaluation.

Objective:
Determine whether existing Treading-Ai models demonstrate genuine, statistically credible
predictive value beyond simple baselines across 2021-2024 research/training data.

Strict Data Protection & Research Protocol:
1. Scope: 2021-2024 Training partition ONLY (260,821 M5 bars).
2. Protected Partitions: ZERO access, querying, loading, or inspection of 2025 Validation
   or frozen 2026 Test partitions.
3. Chronological Walk-Forward: 3 expanding-window folds (Fold 1=2022, Fold 2=2023, Fold 3=2024).
4. Models Evaluated:
   - Majority-Class Baselines (H=24, H=96)
   - Directional Heuristic Baselines (RSI+Momentum, H=24, H=96)
   - Existing Incumbent Model (H=24, 191 base features)
   - Existing Market-Structure Model (H=24, 233 features)
   - Existing Adaptive Challenger (H=24, 233 features + causal error-gating)
   - Phase 13 Candidate 5 Predictive Model (H=96, 233 features + overlap policy)
   - No-Trade Economic Baseline ($0.00 reference)
5. Comprehensive Metrics:
   - Predictive: Class distribution, Accuracy, Balanced Acc, Precision, Recall, Macro-F1,
     OvR ROC-AUC, OvR PR-AUC, Log Loss, Brier Score, ECE, confidence bin calibration,
     selective threshold calibration.
   - Economic: Trades, Gross PnL, Costs, Net PnL, Net Expectancy, PF, Drawdown,
     Cost sensitivity (Base, Stress, Frictionless), Break-even multipliers.
   - Uncertainty: Moving Block Bootstrap (288 bars) & Trade Bootstrap 95% CIs.
6. Deliverables:
   - reports/phase16/phase16_predictive_metrics.json
   - reports/phase16/phase16_economic_metrics.json
   - reports/phase16/phase16_oof_predictions.parquet
"""

import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize

from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.economic_evaluator import EconomicEvaluator, TradeRecord
from treading_ai.config import FEATURES_DATA_DIR, REPORTS_DIR
from treading_ai.features.market_structure import MarketStructureEngine
from treading_ai.models.baselines import (
    DirectionalHeuristicBaseline,
    LogisticRegressionBaseline,
    MajorityClassBaseline,
)
from treading_ai.models.labeling import CausalDirectionalLabeler
from treading_ai.models.walk_forward import ChronologicalWalkForward
from treading_ai.policies.selective import SelectiveTradingPolicy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Phase16Assessment")

CLASSES = np.array([-1, 0, 1])


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> Tuple[float, List[Dict[str, Any]]]:
    """Compute Expected Calibration Error (ECE) and reliability bin details."""
    confidences = np.max(y_prob, axis=1)
    predictions = CLASSES[np.argmax(y_prob, axis=1)]
    accuracies = (predictions == y_true).astype(float)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_details = []
    ece = 0.0
    n_samples = len(y_true)

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        mask = (confidences >= low) & (confidences < high) if i < n_bins - 1 else (confidences >= low) & (confidences <= high)
        n_bin = int(np.sum(mask))
        if n_bin > 0:
            bin_acc = float(np.mean(accuracies[mask]))
            bin_conf = float(np.mean(confidences[mask]))
            weight = n_bin / n_samples
            ece += weight * abs(bin_acc - bin_conf)
            bin_details.append({
                "bin_idx": i,
                "range": [float(low), float(high)],
                "count": n_bin,
                "pct": float(weight * 100),
                "avg_confidence": bin_conf,
                "accuracy": bin_acc,
                "gap": float(abs(bin_acc - bin_conf)),
            })
        else:
            bin_details.append({
                "bin_idx": i,
                "range": [float(low), float(high)],
                "count": 0,
                "pct": 0.0,
                "avg_confidence": float((low + high) / 2.0),
                "accuracy": 0.0,
                "gap": 0.0,
            })

    return float(ece), bin_details


def evaluate_selective_thresholds(
    y_true: np.ndarray, y_prob: np.ndarray, thresholds: List[float] = [0.50, 0.55, 0.60, 0.65, 0.70]
) -> List[Dict[str, Any]]:
    """Compute selective accuracy/precision at various confidence thresholds."""
    results = []
    p_short = y_prob[:, 0]
    p_long = y_prob[:, 2]

    for tau in thresholds:
        long_mask = p_long >= tau
        short_mask = p_short >= tau
        n_long = int(np.sum(long_mask))
        n_short = int(np.sum(short_mask))
        n_total = n_long + n_short

        long_prec = float(np.mean(y_true[long_mask] == 1)) if n_long > 0 else 0.0
        short_prec = float(np.mean(y_true[short_mask] == -1)) if n_short > 0 else 0.0
        total_prec = (
            float((np.sum(y_true[long_mask] == 1) + np.sum(y_true[short_mask] == -1)) / n_total)
            if n_total > 0
            else 0.0
        )

        results.append({
            "threshold": tau,
            "total_signals": n_total,
            "coverage_pct": float(n_total / len(y_true) * 100),
            "long_signals": n_long,
            "long_precision": long_prec,
            "short_signals": n_short,
            "short_precision": short_prec,
            "combined_precision": total_prec,
        })
    return results


def compute_predictive_metrics(y_true: np.ndarray, y_prob: np.ndarray, model_name: str) -> Dict[str, Any]:
    """Compute comprehensive multiclass predictive metrics on valid evaluation rows."""
    n_samples = len(y_true)
    y_pred = CLASSES[np.argmax(y_prob, axis=1)]
    y_onehot = label_binarize(y_true, classes=CLASSES)

    # Class distributions
    unique_classes, counts = np.unique(y_true, return_counts=True)
    class_dist = {int(c): int(cnt) for c, cnt in zip(unique_classes, counts)}
    class_pcts = {int(c): float(cnt / n_samples * 100) for c, cnt in zip(unique_classes, counts)}
    maj_class = int(unique_classes[np.argmax(counts)])
    maj_baseline_acc = float(np.max(counts) / n_samples)

    # Classification accuracy metrics
    acc = float(accuracy_score(y_true, y_pred))
    balanced_acc = float(balanced_accuracy_score(y_true, y_pred))
    prec_macro, rec_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    prec_per_cls, rec_per_cls, f1_per_cls, _ = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=CLASSES, zero_division=0
    )

    # Loss metrics
    # Clip probas to avoid log(0)
    eps = 1e-15
    y_prob_clipped = np.clip(y_prob, eps, 1.0 - eps)
    y_prob_clipped = y_prob_clipped / np.sum(y_prob_clipped, axis=1, keepdims=True)
    ll = float(log_loss(y_true, y_prob_clipped, labels=CLASSES))
    brier = float(np.mean(np.sum((y_onehot - y_prob) ** 2, axis=1)))

    # Ranking metrics (ROC-AUC and PR-AUC)
    # Check if probas are constant (majority baseline)
    is_constant_prob = np.allclose(y_prob, y_prob[0])
    if is_constant_prob:
        roc_auc = 0.5
        pr_auc = float(np.mean([class_pcts.get(c, 0.0) / 100.0 for c in CLASSES]))
    else:
        try:
            roc_auc = float(roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro", labels=CLASSES))
        except Exception:
            roc_auc = 0.5
        try:
            pr_auc = float(average_precision_score(y_onehot, y_prob, average="macro"))
        except Exception:
            pr_auc = float(np.mean([class_pcts.get(c, 0.0) / 100.0 for c in CLASSES]))

    # Directional Binary metrics (conditioned on price moving outside dead zone: y_true != 0)
    dir_mask = y_true != 0
    if np.sum(dir_mask) > 0:
        y_true_dir = y_true[dir_mask]
        y_prob_dir = y_prob[dir_mask]
        y_pred_dir = y_pred[dir_mask]
        dir_acc = float(np.mean(y_pred_dir == y_true_dir))
        # Binary Long vs Short prob
        p_long_rel = y_prob_dir[:, 2] / np.maximum(y_prob_dir[:, 0] + y_prob_dir[:, 2], 1e-12)
        y_binary = (y_true_dir == 1).astype(int)
        if len(np.unique(y_binary)) > 1 and not np.allclose(p_long_rel, p_long_rel[0]):
            dir_roc = float(roc_auc_score(y_binary, p_long_rel))
        else:
            dir_roc = 0.5
    else:
        dir_acc = 0.0
        dir_roc = 0.5

    # Calibration analysis
    ece, bin_details = compute_ece(y_true, y_prob, n_bins=10)
    selective_cal = evaluate_selective_thresholds(y_true, y_prob)

    return {
        "model_name": model_name,
        "sample_count": n_samples,
        "class_distribution": class_dist,
        "class_percentages": class_pcts,
        "majority_class": maj_class,
        "majority_class_baseline_accuracy": maj_baseline_acc,
        "accuracy": acc,
        "balanced_accuracy": balanced_acc,
        "precision_macro": float(prec_macro),
        "recall_macro": float(rec_macro),
        "f1_macro": float(f1_macro),
        "per_class_metrics": {
            str(c): {
                "precision": float(prec_per_cls[i]),
                "recall": float(rec_per_cls[i]),
                "f1": float(f1_per_cls[i]),
            }
            for i, c in enumerate(CLASSES)
        },
        "roc_auc_ovr_macro": roc_auc,
        "pr_auc_ovr_macro": pr_auc,
        "log_loss": ll,
        "brier_score": brier,
        "directional_binary_accuracy": dir_acc,
        "directional_binary_roc_auc": dir_roc,
        "expected_calibration_error": ece,
        "calibration_bins": bin_details,
        "selective_threshold_metrics": selective_cal,
    }


def block_bootstrap_classification_ci(
    y_true: np.ndarray, y_prob: np.ndarray, block_size: int = 288, n_bootstraps: int = 500, ci: float = 0.95
) -> Dict[str, Tuple[float, float, float]]:
    """Compute fast vectorized moving block bootstrap confidence intervals."""
    n = len(y_true)
    n_blocks = int(np.ceil(n / block_size))
    rng = np.random.RandomState(42)

    boot_accs = []
    boot_baccs = []
    boot_f1s = []
    boot_lls = []
    boot_briers = []

    y_pred = CLASSES[np.argmax(y_prob, axis=1)]
    eps = 1e-15
    y_prob_clipped = np.clip(y_prob, eps, 1.0 - eps)
    y_prob_clipped = y_prob_clipped / np.sum(y_prob_clipped, axis=1, keepdims=True)
    y_onehot = label_binarize(y_true, classes=CLASSES)
    y_true_cls_idx = y_true + 1

    block_starts = rng.randint(0, max(1, n - block_size + 1), size=(n_bootstraps, n_blocks))

    for b in range(n_bootstraps):
        starts = block_starts[b]
        sample_idx = np.concatenate([np.arange(s, min(n, s + block_size)) for s in starts])[:n]

        y_t = y_true[sample_idx]
        y_p = y_pred[sample_idx]
        s_prob = y_prob[sample_idx]
        s_prob_clip = y_prob_clipped[sample_idx]
        s_oh = y_onehot[sample_idx]
        s_cls_idx = y_true_cls_idx[sample_idx]

        boot_accs.append(float(np.mean(y_t == y_p)))

        recalls = []
        f1s = []
        for c in [-1, 0, 1]:
            mask_t = (y_t == c)
            mask_p = (y_p == c)
            tp = int(np.sum(mask_t & mask_p))
            fn = int(np.sum(mask_t & ~mask_p))
            fp = int(np.sum(~mask_t & mask_p))
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            f1 = 2.0 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            recalls.append(rec)
            f1s.append(f1)
        boot_baccs.append(float(np.mean(recalls)))
        boot_f1s.append(float(np.mean(f1s)))

        boot_lls.append(float(-np.mean(np.log(s_prob_clip[np.arange(len(sample_idx)), s_cls_idx]))))
        boot_briers.append(float(np.mean(np.sum((s_oh - s_prob) ** 2, axis=1))))

    alpha = (1.0 - ci) / 2.0
    results = {}
    pt_prec, pt_rec, pt_f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    for name, arr, point in [
        ("accuracy", boot_accs, accuracy_score(y_true, y_pred)),
        ("balanced_accuracy", boot_baccs, balanced_accuracy_score(y_true, y_pred)),
        ("f1_macro", boot_f1s, pt_f1),
        ("log_loss", boot_lls, log_loss(y_true, y_prob_clipped, labels=CLASSES)),
        ("brier_score", boot_briers, np.mean(np.sum((y_onehot - y_prob) ** 2, axis=1))),
    ]:
        results[name] = (
            float(point),
            float(np.percentile(arr, 100 * alpha)),
            float(np.percentile(arr, 100 * (1.0 - alpha))),
        )
    return results


def trade_bootstrap_ci(trades: List[TradeRecord], n_bootstraps: int = 1000, ci: float = 0.95) -> Dict[str, Tuple[float, float, float]]:
    """Compute trade-level bootstrap confidence intervals for economic metrics."""
    if len(trades) == 0:
        return {
            "net_expectancy": (0.0, 0.0, 0.0),
            "net_pnl": (0.0, 0.0, 0.0),
            "profit_factor": (0.0, 0.0, 0.0),
        }

    net_pnls = np.array([t.net_pnl for t in trades], dtype=float)
    n = len(net_pnls)
    rng = np.random.RandomState(42)

    boot_exp = []
    boot_tot = []
    boot_pf = []

    for _ in range(n_bootstraps):
        sample = rng.choice(net_pnls, size=n, replace=True)
        boot_exp.append(np.mean(sample))
        boot_tot.append(np.sum(sample))
        wins = sample[sample > 0]
        losses = sample[sample < 0]
        pf = float(np.sum(wins) / abs(np.sum(losses))) if len(losses) > 0 and np.sum(losses) != 0 else 0.0
        boot_pf.append(pf)

    alpha = (1.0 - ci) / 2.0
    wins_tot = net_pnls[net_pnls > 0]
    losses_tot = net_pnls[net_pnls < 0]
    pt_pf = float(np.sum(wins_tot) / abs(np.sum(losses_tot))) if len(losses_tot) > 0 and np.sum(losses_tot) != 0 else 0.0

    return {
        "net_expectancy": (
            float(np.mean(net_pnls)),
            float(np.percentile(boot_exp, 100 * alpha)),
            float(np.percentile(boot_exp, 100 * (1.0 - alpha))),
        ),
        "net_pnl": (
            float(np.sum(net_pnls)),
            float(np.percentile(boot_tot, 100 * alpha)),
            float(np.percentile(boot_tot, 100 * (1.0 - alpha))),
        ),
        "profit_factor": (
            pt_pf,
            float(np.percentile(boot_pf, 100 * alpha)),
            float(np.percentile(boot_pf, 100 * (1.0 - alpha))),
        ),
    }


def run_phase16_assessment() -> None:
    logger.info("=" * 80)
    logger.info("PHASE 16: AI MODEL CAPABILITY ASSESSMENT & BENCHMARK AUDIT")
    logger.info("=" * 80)

    t0_start = time.time()

    # 1. Verify Partition Isolation
    train_path = FEATURES_DATA_DIR / "XAUUSD_M5_features_train.parquet"
    val_path = FEATURES_DATA_DIR / "XAUUSD_M5_features_val.parquet"
    test_path = FEATURES_DATA_DIR / "XAUUSD_M5_features_test.parquet"

    # Assert that val and test exist but will NOT be opened
    assert train_path.exists(), f"Train dataset missing at {train_path}"
    assert val_path.exists(), f"Protected validation dataset missing at {val_path}"
    assert test_path.exists(), f"Protected test dataset missing at {test_path}"

    logger.info("Loading 2021-2024 training dataset from %s ONLY...", train_path)
    train_df = pd.read_parquet(train_path)
    n_rows = len(train_df)
    logger.info("Loaded %d rows with %d columns.", n_rows, len(train_df.columns))

    non_feature_cols = {"timestamp", "open", "high", "low", "close", "volume"}
    base_feature_cols = [c for c in train_df.columns if c not in non_feature_cols]

    # Compute Market Structure Features
    logger.info("Computing 42 causal market structure features across training data...")
    ms_engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)
    ms_features_df = ms_engine.compute_features(train_df, atr_series=train_df["atr_14"])
    augmented_df = pd.concat([train_df, ms_features_df], axis=1)
    all_feature_cols = base_feature_cols + list(ms_features_df.columns)
    logger.info("Feature engineering complete: Base=%d, Augmented=%d", len(base_feature_cols), len(all_feature_cols))

    BASELINE_ATR = 1.153
    BASELINE_RANGE = 1.050

    # 2. Compute Causal Directional Labels for H=24 and H=96
    logger.info("Computing causal directional labels for H=24 and H=96...")
    labeler_24 = CausalDirectionalLabeler(horizon=24)
    labels_24_df = labeler_24.compute_labels(train_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    valid_mask_24 = ~labels_24_df["is_purged"].to_numpy()

    labeler_96 = CausalDirectionalLabeler(horizon=96)
    labels_96_df = labeler_96.compute_labels(train_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    valid_mask_96 = ~labels_96_df["is_purged"].to_numpy()

    logger.info("H=24 labels: %d valid, %d purged", np.sum(valid_mask_24), np.sum(~valid_mask_24))
    logger.info("H=96 labels: %d valid, %d purged", np.sum(valid_mask_96), np.sum(~valid_mask_96))

    # 3. Setup Walk-Forward Splits (3 expanding folds)
    cwf = ChronologicalWalkForward(n_splits=3, horizon=24)
    folds = cwf.split_by_years(train_df, timestamp_col="timestamp")
    logger.info("Configured %d expanding chronological walk-forward folds.", len(folds))

    # 4. Cost Models and Evaluators
    cost_base = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
    cost_stress = ExecutionCostModel(base_spread_usd=0.30, base_slippage_usd=0.075)
    cost_frictionless = ExecutionCostModel(base_spread_usd=0.0, base_slippage_usd=0.0, commission_per_lot_usd=0.0)

    eval_24_base = EconomicEvaluator(cost_base, horizon=24, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    eval_24_stress = EconomicEvaluator(cost_stress, horizon=24, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    eval_24_fric = EconomicEvaluator(cost_frictionless, horizon=24, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)

    eval_96_base = EconomicEvaluator(cost_base, horizon=96, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    eval_96_stress = EconomicEvaluator(cost_stress, horizon=96, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
    eval_96_fric = EconomicEvaluator(cost_frictionless, horizon=96, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)

    # 5. Containers for Out-of-Fold Predictions & Metrics
    model_keys = [
        "majority_class_h24",
        "heuristic_rsi_mom_h24",
        "incumbent_lr_h24",
        "market_structure_lr_h24",
        "adaptive_challenger_h24",
        "majority_class_h96",
        "heuristic_rsi_mom_h96",
        "candidate5_overlap_h96",
        "no_trade_baseline",
    ]

    per_fold_predictive: Dict[str, List[Dict[str, Any]]] = {k: [] for k in model_keys if k != "no_trade_baseline"}
    per_fold_economic: Dict[str, List[Dict[str, Any]]] = {k: [] for k in model_keys}
    raw_trades: Dict[str, List[TradeRecord]] = {k: [] for k in model_keys}

    oof_dfs: List[pd.DataFrame] = []

    # 6. Walk-Forward Training and Evaluation Loop
    for fold in folds:
        logger.info("=" * 70)
        logger.info(
            "FOLD %d: Train %s to %s (%d) -> Eval %s to %s (%d)",
            fold.fold_id,
            fold.train_start_time.strftime("%Y-%m-%d"),
            fold.train_end_time.strftime("%Y-%m-%d"),
            fold.n_train,
            fold.eval_start_time.strftime("%Y-%m-%d"),
            fold.eval_end_time.strftime("%Y-%m-%d"),
            fold.n_eval,
        )
        logger.info("=" * 70)

        ev_df = train_df.iloc[fold.eval_indices].copy().reset_index(drop=True)
        ev_aug_df = augmented_df.iloc[fold.eval_indices].copy().reset_index(drop=True)
        n_ev = len(ev_df)

        # Labels for fold evaluation
        y24_ev_full = labels_24_df.iloc[fold.eval_indices]["target_class"].to_numpy()
        valid_ev_24 = valid_mask_24[fold.eval_indices]

        y96_ev_full = labels_96_df.iloc[fold.eval_indices]["target_class"].to_numpy()
        valid_ev_96 = valid_mask_96[fold.eval_indices]

        # Training slices for H=24
        tr_clean_24 = fold.train_indices[valid_mask_24[fold.train_indices]]
        y24_tr = labels_24_df.iloc[tr_clean_24]["target_class"].to_numpy(dtype=int)
        X24_tr_base = train_df.iloc[tr_clean_24][base_feature_cols]
        X24_tr_all = augmented_df.iloc[tr_clean_24][all_feature_cols]

        # Training slices for H=96
        tr_clean_96 = fold.train_indices[valid_mask_96[fold.train_indices]]
        y96_tr = labels_96_df.iloc[tr_clean_96]["target_class"].to_numpy(dtype=int)
        X96_tr_all = augmented_df.iloc[tr_clean_96][all_feature_cols]

        # Evaluation slices
        X24_ev_base = ev_df[base_feature_cols]
        X24_ev_all = ev_aug_df[all_feature_cols]
        X96_ev_all = ev_aug_df[all_feature_cols]

        # Context features for policy logic
        atr_arr = ev_aug_df["atr_14"].to_numpy()
        med_atr_arr = ev_aug_df["atr_14"].rolling(288, min_periods=10).median().to_numpy()
        trend_state_arr = ev_aug_df["ms_trend_state"].to_numpy()
        session_names = cost_base.get_session_name_series(ev_df["timestamp"]).to_numpy()

        # -------------------------------------------------------------
        # FIT MODELS
        # -------------------------------------------------------------
        logger.info("Fitting H=24 and H=96 models on Fold %d training partition...", fold.fold_id)

        # 1. Majority Class Baseline H=24
        maj_24 = MajorityClassBaseline()
        maj_24.fit(X24_tr_base, y24_tr)

        # 2. Directional Heuristic H=24
        heur_24 = DirectionalHeuristicBaseline()
        heur_24.fit(X24_tr_base, y24_tr)

        # 3. Incumbent Model H=24 (191 features)
        incumbent_24 = LogisticRegressionBaseline(max_iter=300, random_state=42)
        incumbent_24.fit(X24_tr_base, y24_tr)

        # 4. Market Structure Model H=24 (233 features)
        ms_model_24 = LogisticRegressionBaseline(max_iter=300, random_state=42)
        ms_model_24.fit(X24_tr_all, y24_tr)

        # 5. Majority Class Baseline H=96
        maj_96 = MajorityClassBaseline()
        maj_96.fit(X96_tr_all, y96_tr)

        # 6. Directional Heuristic H=96
        heur_96 = DirectionalHeuristicBaseline()
        heur_96.fit(X96_tr_all, y96_tr)

        # 7. Candidate 5 Predictive Model H=96 (233 features)
        cand5_model_96 = LogisticRegressionBaseline(max_iter=300, random_state=42)
        cand5_model_96.fit(X96_tr_all, y96_tr)

        # -------------------------------------------------------------
        # GENERATE PREDICTIONS & PROBABILITIES
        # -------------------------------------------------------------
        prob_maj_24 = maj_24.predict_proba(X24_ev_base)
        prob_heur_24 = heur_24.predict_proba(X24_ev_base)
        prob_inc_24 = incumbent_24.predict_proba(X24_ev_base)
        prob_ms_24 = ms_model_24.predict_proba(X24_ev_all)

        prob_maj_96 = maj_96.predict_proba(X96_ev_all)
        prob_heur_96 = heur_96.predict_proba(X96_ev_all)
        prob_cand5_96 = cand5_model_96.predict_proba(X96_ev_all)

        # Adaptive Challenger H=24:
        # Uses ms_model_24 probabilities + causal error-gating abstention
        prob_adapt_24 = prob_ms_24.copy()

        # -------------------------------------------------------------
        # COMPUTE PREDICTIVE METRICS (ON VALID EVAL ROWS)
        # -------------------------------------------------------------
        y24_valid = y24_ev_full[valid_ev_24].astype(int)
        y96_valid = y96_ev_full[valid_ev_96].astype(int)

        eval_pairs = [
            ("majority_class_h24", y24_valid, prob_maj_24[valid_ev_24], "Majority Class (H=24)"),
            ("heuristic_rsi_mom_h24", y24_valid, prob_heur_24[valid_ev_24], "Heuristic RSI+Mom (H=24)"),
            ("incumbent_lr_h24", y24_valid, prob_inc_24[valid_ev_24], "Incumbent LR (H=24, 191f)"),
            ("market_structure_lr_h24", y24_valid, prob_ms_24[valid_ev_24], "Market Structure LR (H=24, 233f)"),
            ("adaptive_challenger_h24", y24_valid, prob_adapt_24[valid_ev_24], "Adaptive Challenger (H=24)"),
            ("majority_class_h96", y96_valid, prob_maj_96[valid_ev_96], "Majority Class (H=96)"),
            ("heuristic_rsi_mom_h96", y96_valid, prob_heur_96[valid_ev_96], "Heuristic RSI+Mom (H=96)"),
            ("candidate5_overlap_h96", y96_valid, prob_cand5_96[valid_ev_96], "Cand 5 Model (H=96, 233f)"),
        ]

        for k, y_true_v, p_v, disp_name in eval_pairs:
            m_dict = compute_predictive_metrics(y_true_v, p_v, disp_name)
            m_dict["fold_id"] = fold.fold_id
            per_fold_predictive[k].append(m_dict)

        # -------------------------------------------------------------
        # ECONOMIC SIGNAL POLICIES & BACKTEST EVALUATION
        # -------------------------------------------------------------
        # 1. No-Trade Baseline
        sigs_notrade = np.zeros(n_ev, dtype=int)
        met_nt_b, tr_nt = eval_24_base.evaluate(ev_df, sigs_notrade, model_name="NoTrade")
        met_nt_s, _ = eval_24_stress.evaluate(ev_df, sigs_notrade, model_name="NoTrade")
        met_nt_f, _ = eval_24_fric.evaluate(ev_df, sigs_notrade, model_name="NoTrade")

        # 2. Majority Class H=24 (Directional benchmark)
        # Note: If maj class is Long (+1), take continuous non-overlapping long trades
        maj_dir_24 = maj_24.majority_class_
        sigs_maj_24 = np.zeros(n_ev, dtype=int)
        lock = 0
        for i in range(n_ev):
            if lock > 0:
                lock -= 1
                continue
            sigs_maj_24[i] = maj_dir_24
            lock = 24
        met_maj24_b, tr_maj24 = eval_24_base.evaluate(ev_df, sigs_maj_24, model_name="MajClass_H24")
        met_maj24_s, _ = eval_24_stress.evaluate(ev_df, sigs_maj_24, model_name="MajClass_H24")
        met_maj24_f, _ = eval_24_fric.evaluate(ev_df, sigs_maj_24, model_name="MajClass_H24")

        # 3. Heuristic H=24 (Non-overlapping lockout for 24 bars)
        raw_heur_24 = heur_24.predict(X24_ev_base)
        sigs_heur_24 = np.zeros(n_ev, dtype=int)
        lock = 0
        for i in range(n_ev):
            if lock > 0:
                lock -= 1
                continue
            if raw_heur_24[i] != 0:
                sigs_heur_24[i] = raw_heur_24[i]
                lock = 24
        met_heur24_b, tr_heur24 = eval_24_base.evaluate(ev_df, sigs_heur_24, model_name="Heuristic_H24")
        met_heur24_s, _ = eval_24_stress.evaluate(ev_df, sigs_heur_24, model_name="Heuristic_H24")
        met_heur24_f, _ = eval_24_fric.evaluate(ev_df, sigs_heur_24, model_name="Heuristic_H24")

        # 4. Incumbent H=24 (Threshold 0.60, non-overlapping 24)
        policy_inc = SelectiveTradingPolicy(model=incumbent_24, threshold=0.60, mode="non_overlapping", holding_horizon=24)
        sigs_inc_24 = policy_inc.generate_signals(X24_ev_base).signals
        met_inc24_b, tr_inc24 = eval_24_base.evaluate(ev_df, sigs_inc_24, model_name="Incumbent_H24")
        met_inc24_s, _ = eval_24_stress.evaluate(ev_df, sigs_inc_24, model_name="Incumbent_H24")
        met_inc24_f, _ = eval_24_fric.evaluate(ev_df, sigs_inc_24, model_name="Incumbent_H24")

        # 5. Market Structure H=24 (Threshold 0.60, non-overlapping 24)
        policy_ms = SelectiveTradingPolicy(model=ms_model_24, threshold=0.60, mode="non_overlapping", holding_horizon=24)
        sigs_ms_24 = policy_ms.generate_signals(X24_ev_all).signals
        met_ms24_b, tr_ms24 = eval_24_base.evaluate(ev_df, sigs_ms_24, model_name="MarketStructure_H24")
        met_ms24_s, _ = eval_24_stress.evaluate(ev_df, sigs_ms_24, model_name="MarketStructure_H24")
        met_ms24_f, _ = eval_24_fric.evaluate(ev_df, sigs_ms_24, model_name="MarketStructure_H24")

        # 6. Adaptive Challenger H=24 (Causal Error-Gated Structural Policy)
        p_long_24 = prob_ms_24[:, 2]
        p_short_24 = prob_ms_24[:, 0]
        raw_adapt_24 = np.zeros(n_ev, dtype=int)
        for idx in range(n_ev):
            cand_d = 1 if p_long_24[idx] >= 0.60 else (-1 if p_short_24[idx] >= 0.60 else 0)
            if cand_d == 0:
                continue
            cur_med = med_atr_arr[idx] if not np.isnan(med_atr_arr[idx]) else atr_arr[idx]
            if atr_arr[idx] < cur_med * 0.90:
                continue  # Suppress in low vol compression
            if cand_d == 1 and trend_state_arr[idx] == -1:
                continue  # Suppress counter-trend
            if cand_d == -1 and trend_state_arr[idx] == 1:
                continue
            raw_adapt_24[idx] = cand_d

        sigs_adapt_24 = np.zeros(n_ev, dtype=int)
        lock = 0
        for i in range(n_ev):
            if lock > 0:
                lock -= 1
                continue
            if raw_adapt_24[i] != 0:
                sigs_adapt_24[i] = raw_adapt_24[i]
                lock = 24
        met_adapt24_b, tr_adapt24 = eval_24_base.evaluate(ev_df, sigs_adapt_24, model_name="AdaptiveChallenger_H24")
        met_adapt24_s, _ = eval_24_stress.evaluate(ev_df, sigs_adapt_24, model_name="AdaptiveChallenger_H24")
        met_adapt24_f, _ = eval_24_fric.evaluate(ev_df, sigs_adapt_24, model_name="AdaptiveChallenger_H24")

        # 7. Majority Class H=96 (Directional benchmark)
        maj_dir_96 = maj_96.majority_class_
        sigs_maj_96 = np.zeros(n_ev, dtype=int)
        lock = 0
        for i in range(n_ev):
            if lock > 0:
                lock -= 1
                continue
            sigs_maj_96[i] = maj_dir_96
            lock = 96
        met_maj96_b, tr_maj96 = eval_96_base.evaluate(ev_df, sigs_maj_96, model_name="MajClass_H96")
        met_maj96_s, _ = eval_96_stress.evaluate(ev_df, sigs_maj_96, model_name="MajClass_H96")
        met_maj96_f, _ = eval_96_fric.evaluate(ev_df, sigs_maj_96, model_name="MajClass_H96")

        # 8. Heuristic H=96 (Lockout 96)
        raw_heur_96 = heur_96.predict(X96_ev_all)
        sigs_heur_96 = np.zeros(n_ev, dtype=int)
        lock = 0
        for i in range(n_ev):
            if lock > 0:
                lock -= 1
                continue
            if raw_heur_96[i] != 0:
                sigs_heur_96[i] = raw_heur_96[i]
                lock = 96
        met_heur96_b, tr_heur96 = eval_96_base.evaluate(ev_df, sigs_heur_96, model_name="Heuristic_H96")
        met_heur96_s, _ = eval_96_stress.evaluate(ev_df, sigs_heur_96, model_name="Heuristic_H96")
        met_heur96_f, _ = eval_96_fric.evaluate(ev_df, sigs_heur_96, model_name="Heuristic_H96")

        # 9. Candidate 5 H=96 (London/NY Overlap, Regime Gating, Trend Align, Lockout 96)
        p_long_96 = prob_cand5_96[:, 2]
        p_short_96 = prob_cand5_96[:, 0]
        raw_cand5_96 = np.zeros(n_ev, dtype=int)
        for idx in range(n_ev):
            cand_d = 1 if p_long_96[idx] >= 0.60 else (-1 if p_short_96[idx] >= 0.60 else 0)
            if cand_d == 0:
                continue
            if session_names[idx] != "LONDON_NY_OVERLAP":
                continue
            cur_med = med_atr_arr[idx] if not np.isnan(med_atr_arr[idx]) else atr_arr[idx]
            if atr_arr[idx] < cur_med * 0.90:
                continue
            if cand_d == 1 and trend_state_arr[idx] == -1:
                continue
            if cand_d == -1 and trend_state_arr[idx] == 1:
                continue
            raw_cand5_96[idx] = cand_d

        sigs_cand5_96 = np.zeros(n_ev, dtype=int)
        lock = 0
        for i in range(n_ev):
            if lock > 0:
                lock -= 1
                continue
            if raw_cand5_96[i] != 0:
                sigs_cand5_96[i] = raw_cand5_96[i]
                lock = 96
        met_cand5_b, tr_cand5 = eval_96_base.evaluate(ev_df, sigs_cand5_96, model_name="Cand5_Overlap96")
        met_cand5_s, _ = eval_96_stress.evaluate(ev_df, sigs_cand5_96, model_name="Cand5_Overlap96")
        met_cand5_f, _ = eval_96_fric.evaluate(ev_df, sigs_cand5_96, model_name="Cand5_Overlap96")

        # Record economic results for fold
        econ_pairs = [
            ("no_trade_baseline", met_nt_b, met_nt_s, met_nt_f, tr_nt),
            ("majority_class_h24", met_maj24_b, met_maj24_s, met_maj24_f, tr_maj24),
            ("heuristic_rsi_mom_h24", met_heur24_b, met_heur24_s, met_heur24_f, tr_heur24),
            ("incumbent_lr_h24", met_inc24_b, met_inc24_s, met_inc24_f, tr_inc24),
            ("market_structure_lr_h24", met_ms24_b, met_ms24_s, met_ms24_f, tr_ms24),
            ("adaptive_challenger_h24", met_adapt24_b, met_adapt24_s, met_adapt24_f, tr_adapt24),
            ("majority_class_h96", met_maj96_b, met_maj96_s, met_maj96_f, tr_maj96),
            ("heuristic_rsi_mom_h96", met_heur96_b, met_heur96_s, met_heur96_f, tr_heur96),
            ("candidate5_overlap_h96", met_cand5_b, met_cand5_s, met_cand5_f, tr_cand5),
        ]

        for k, mb, ms, mf, tr_list in econ_pairs:
            raw_trades[k].extend(tr_list)
            n_tr = mb.n_completed_trades
            per_fold_economic[k].append({
                "fold_id": fold.fold_id,
                "trades": n_tr,
                "gross_pnl_usd": mb.gross_pnl_usd,
                "friction_usd": mb.total_friction_usd,
                "net_pnl_base_usd": mb.net_pnl_usd,
                "net_pnl_stress_usd": ms.net_pnl_usd,
                "gross_pnl_frictionless_usd": mf.gross_pnl_usd,
                "net_expectancy": mb.net_pnl_usd / n_tr if n_tr > 0 else 0.0,
                "gross_expectancy": mb.gross_pnl_usd / n_tr if n_tr > 0 else 0.0,
                "friction_expectancy": mb.total_friction_usd / n_tr if n_tr > 0 else 0.0,
                "profit_factor_net": mb.profit_factor_net,
                "profit_factor_gross": mb.profit_factor_gross,
                "win_rate_net": mb.win_rate_net,
                "max_drawdown_usd": mb.max_drawdown_usd,
            })

        # Save out-of-fold predictions DataFrame slice
        oof_slice = pd.DataFrame({
            "timestamp": ev_df["timestamp"],
            "fold_id": fold.fold_id,
            "target_class_h24": y24_ev_full,
            "is_valid_h24": valid_ev_24,
            "target_class_h96": y96_ev_full,
            "is_valid_h96": valid_ev_96,
            # Model H=24 Probas
            "prob_inc_short_h24": prob_inc_24[:, 0],
            "prob_inc_neut_h24": prob_inc_24[:, 1],
            "prob_inc_long_h24": prob_inc_24[:, 2],
            "prob_ms_short_h24": prob_ms_24[:, 0],
            "prob_ms_neut_h24": prob_ms_24[:, 1],
            "prob_ms_long_h24": prob_ms_24[:, 2],
            # Model H=96 Probas
            "prob_cand5_short_h96": prob_cand5_96[:, 0],
            "prob_cand5_neut_h96": prob_cand5_96[:, 1],
            "prob_cand5_long_h96": prob_cand5_96[:, 2],
            # Signals
            "signal_incumbent_h24": sigs_inc_24,
            "signal_market_structure_h24": sigs_ms_24,
            "signal_adaptive_challenger_h24": sigs_adapt_24,
            "signal_cand5_overlap_h96": sigs_cand5_96,
            "signal_heuristic_h24": sigs_heur_24,
            "signal_heuristic_h96": sigs_heur_96,
        })
        oof_dfs.append(oof_slice)

    # 7. Aggregate Full Out-of-Fold Predictions & Metrics
    logger.info("=" * 80)
    logger.info("COMPUTING AGGREGATE OUT-OF-FOLD (OOF) PREDICTIVE & ECONOMIC METRICS")
    logger.info("=" * 80)

    full_oof_df = pd.concat(oof_dfs, ignore_index=True)
    v24_full = full_oof_df["is_valid_h24"].to_numpy()
    v96_full = full_oof_df["is_valid_h96"].to_numpy()

    y24_oof = full_oof_df.loc[v24_full, "target_class_h24"].to_numpy(dtype=int)
    y96_oof = full_oof_df.loc[v96_full, "target_class_h96"].to_numpy(dtype=int)

    # Extract full pooled probability arrays
    probas_oof = {
        "incumbent_lr_h24": np.column_stack([
            full_oof_df.loc[v24_full, "prob_inc_short_h24"],
            full_oof_df.loc[v24_full, "prob_inc_neut_h24"],
            full_oof_df.loc[v24_full, "prob_inc_long_h24"],
        ]),
        "market_structure_lr_h24": np.column_stack([
            full_oof_df.loc[v24_full, "prob_ms_short_h24"],
            full_oof_df.loc[v24_full, "prob_ms_neut_h24"],
            full_oof_df.loc[v24_full, "prob_ms_long_h24"],
        ]),
        "adaptive_challenger_h24": np.column_stack([
            full_oof_df.loc[v24_full, "prob_ms_short_h24"],
            full_oof_df.loc[v24_full, "prob_ms_neut_h24"],
            full_oof_df.loc[v24_full, "prob_ms_long_h24"],
        ]),
        "candidate5_overlap_h96": np.column_stack([
            full_oof_df.loc[v96_full, "prob_cand5_short_h96"],
            full_oof_df.loc[v96_full, "prob_cand5_neut_h96"],
            full_oof_df.loc[v96_full, "prob_cand5_long_h96"],
        ]),
    }

    # Baseline probability arrays across pooled OOF
    # Majority H=24 (from training folds, average priors)
    maj_priors_24 = np.array([
        np.mean([f["class_percentages"][c] for f in per_fold_predictive["majority_class_h24"]]) / 100.0
        for c in [-1, 0, 1]
    ])
    probas_oof["majority_class_h24"] = np.tile(maj_priors_24, (len(y24_oof), 1))

    maj_priors_96 = np.array([
        np.mean([f["class_percentages"][c] for f in per_fold_predictive["majority_class_h96"]]) / 100.0
        for c in [-1, 0, 1]
    ])
    probas_oof["majority_class_h96"] = np.tile(maj_priors_96, (len(y96_oof), 1))

    # Heuristics on full OOF
    heur_full_24 = DirectionalHeuristicBaseline()
    heur_full_24.fit(train_df[base_feature_cols], labels_24_df["target_class"])
    probas_oof["heuristic_rsi_mom_h24"] = heur_full_24.predict_proba(train_df.iloc[full_oof_df.index[v24_full]][base_feature_cols])

    heur_full_96 = DirectionalHeuristicBaseline()
    heur_full_96.fit(augmented_df[all_feature_cols], labels_96_df["target_class"])
    probas_oof["heuristic_rsi_mom_h96"] = heur_full_96.predict_proba(augmented_df.iloc[full_oof_df.index[v96_full]][all_feature_cols])

    # Compute overall OOF predictive summaries + Block Bootstrap CIs
    aggregate_predictive = {}
    for k in [
        "majority_class_h24",
        "heuristic_rsi_mom_h24",
        "incumbent_lr_h24",
        "market_structure_lr_h24",
        "adaptive_challenger_h24",
        "majority_class_h96",
        "heuristic_rsi_mom_h96",
        "candidate5_overlap_h96",
    ]:
        y_true_target = y96_oof if "_h96" in k else y24_oof
        p_arr = probas_oof[k]
        logger.info("Computing pooled metrics and block bootstrap CIs for %s...", k)
        m_dict = compute_predictive_metrics(y_true_target, p_arr, k)
        ci_dict = block_bootstrap_classification_ci(y_true_target, p_arr, block_size=288, n_bootstraps=1000)
        m_dict["bootstrap_95_ci"] = ci_dict
        m_dict["per_fold_metrics"] = per_fold_predictive[k]
        aggregate_predictive[k] = m_dict

    # Compute aggregate Economic summaries + Trade Bootstrap CIs
    aggregate_economic = {}
    for k in model_keys:
        t_list = raw_trades[k]
        f_list = per_fold_economic[k]
        n_tr = len(t_list)

        tot_gross = sum(f["gross_pnl_usd"] for f in f_list)
        tot_fric = sum(f["friction_usd"] for f in f_list)
        tot_net_base = sum(f["net_pnl_base_usd"] for f in f_list)
        tot_net_stress = sum(f["net_pnl_stress_usd"] for f in f_list)
        tot_fric_free = sum(f["gross_pnl_frictionless_usd"] for f in f_list)

        if n_tr > 0:
            net_pnls = np.array([t.net_pnl for t in t_list], dtype=float)
            gross_pnls = np.array([t.gross_pnl for t in t_list], dtype=float)
            wins_net = net_pnls[net_pnls > 0]
            loss_net = net_pnls[net_pnls < 0]
            pf_net = float(np.sum(wins_net) / abs(np.sum(loss_net))) if len(loss_net) > 0 and np.sum(loss_net) != 0 else 0.0

            wins_gross = gross_pnls[gross_pnls > 0]
            loss_gross = gross_pnls[gross_pnls < 0]
            pf_gross = float(np.sum(wins_gross) / abs(np.sum(loss_gross))) if len(loss_gross) > 0 and np.sum(loss_gross) != 0 else 0.0

            win_rate_net = float(len(wins_net) / n_tr)
            win_rate_gross = float(len(wins_gross) / n_tr)

            # Max drawdown on combined trades
            cum_net = np.cumsum(net_pnls)
            peak = np.maximum.accumulate(cum_net)
            dd = peak - cum_net
            max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

            ci_dict = trade_bootstrap_ci(t_list, n_bootstraps=1000)

            # Directional split
            long_t = [t for t in t_list if t.direction == 1]
            short_t = [t for t in t_list if t.direction == -1]

            be_mult = float(tot_gross / tot_fric) if tot_fric > 0 else 0.0
            be_spread = float(0.20 * be_mult)

            # Hypothesis test vs No-Trade: Student's t-test and Wilcoxon
            t_stat, p_val_t = stats.ttest_1samp(net_pnls, 0.0)
            try:
                _, p_val_wilcoxon = stats.wilcoxon(net_pnls)
            except Exception:
                p_val_wilcoxon = 1.0
        else:
            net_pnls = np.array([])
            pf_net = 0.0
            pf_gross = 0.0
            win_rate_net = 0.0
            win_rate_gross = 0.0
            max_dd = 0.0
            ci_dict = {
                "net_expectancy": (0.0, 0.0, 0.0),
                "net_pnl": (0.0, 0.0, 0.0),
                "profit_factor": (0.0, 0.0, 0.0),
            }
            long_t = []
            short_t = []
            be_mult = 0.0
            be_spread = 0.0
            t_stat, p_val_t, p_val_wilcoxon = 0.0, 1.0, 1.0

        aggregate_economic[k] = {
            "model_key": k,
            "total_trades": n_tr,
            "gross_pnl_usd": tot_gross,
            "friction_usd": tot_fric,
            "net_pnl_base_usd": tot_net_base,
            "net_pnl_stress_usd": tot_net_stress,
            "gross_pnl_frictionless_usd": tot_fric_free,
            "net_expectancy_usd": tot_net_base / n_tr if n_tr > 0 else 0.0,
            "gross_expectancy_usd": tot_gross / n_tr if n_tr > 0 else 0.0,
            "friction_expectancy_usd": tot_fric / n_tr if n_tr > 0 else 0.0,
            "profit_factor_net": pf_net,
            "profit_factor_gross": pf_gross,
            "win_rate_net": win_rate_net,
            "win_rate_gross": win_rate_gross,
            "max_drawdown_usd": max_dd,
            "break_even_cost_multiplier": be_mult,
            "break_even_base_spread_usd": be_spread,
            "t_statistic_vs_zero": float(t_stat),
            "p_value_t": float(p_val_t),
            "p_value_wilcoxon": float(p_val_wilcoxon),
            "bootstrap_95_ci": ci_dict,
            "long_breakdown": {
                "trades": len(long_t),
                "net_pnl": sum(t.net_pnl for t in long_t) if len(long_t) > 0 else 0.0,
                "win_rate": float(np.mean([t.net_pnl > 0 for t in long_t])) if len(long_t) > 0 else 0.0,
            },
            "short_breakdown": {
                "trades": len(short_t),
                "net_pnl": sum(t.net_pnl for t in short_t) if len(short_t) > 0 else 0.0,
                "win_rate": float(np.mean([t.net_pnl > 0 for t in short_t])) if len(short_t) > 0 else 0.0,
            },
            "per_fold_results": f_list,
        }

    # 8. Save Deliverables to reports/phase16/
    out_dir = Path("reports/phase16")
    out_dir.mkdir(parents=True, exist_ok=True)

    pred_out_file = out_dir / "phase16_predictive_metrics.json"
    econ_out_file = out_dir / "phase16_economic_metrics.json"
    oof_out_file = out_dir / "phase16_oof_predictions.parquet"

    logger.info("Saving predictive metrics to %s...", pred_out_file)
    with open(pred_out_file, "w") as f:
        json.dump(aggregate_predictive, f, indent=2)

    logger.info("Saving economic metrics to %s...", econ_out_file)
    with open(econ_out_file, "w") as f:
        json.dump(aggregate_economic, f, indent=2)

    logger.info("Saving OOF predictions to %s...", oof_out_file)
    full_oof_df.to_parquet(oof_out_file, index=False)

    logger.info("=" * 80)
    logger.info("PHASE 16 ASSESSMENT EXECUTION COMPLETE IN %.2f SECONDS", time.time() - t0_start)
    logger.info("=" * 80)


if __name__ == "__main__":
    run_phase16_assessment()
