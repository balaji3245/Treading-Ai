#!/usr/bin/env python3
"""Phase 17: Research Feasibility & Edge Diagnostic Script.

Strict Data Governance:
- Accesses ONLY data/features/XAUUSD_M5_features_train.parquet.
- Zero access to protected validation (2025) or frozen test (2026) partitions.
- Saves all diagnostics under reports/phase17/.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from treading_ai.features.market_structure import MarketStructureEngine
from treading_ai.models.labeling import (
    CausalDirectionalLabeler,
    PURGE_BOUNDARY_SPLIT_OVERFLOW,
    PURGE_ROLLOVER_CLOSED,
    PURGE_ROLLOVER_CROSSING,
    PURGE_WEEKEND_CROSSING,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Phase17Diagnostic")

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
TRAIN_DATA_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_train.parquet"
OOF_PREDICTIONS_PATH = PROJECT_ROOT / "reports/phase16/phase16_oof_predictions.parquet"
OUTPUT_DIR = PROJECT_ROOT / "reports/phase17"

BASELINE_ATR = 1.153
BASELINE_RANGE = 1.050
COST_BASE_ROUND_TURN = 0.40   # $0.20/oz half-spread
COST_STRESS_ROUND_TURN = 0.60 # $0.30/oz half-spread
HORIZONS = [12, 24, 48, 72, 96, 120, 288]


class NpEncoder(json.JSONEncoder):
    """JSON Encoder handling NumPy primitives."""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (pd.Timestamp, pd.Timedelta)):
            return str(obj)
        return super().default(obj)


def audit_label_feasibility(df: pd.DataFrame) -> Dict[str, Any]:
    """Audit target labels across all project horizons."""
    logger.info("Executing Section 1: Label Feasibility Audit across horizons %s...", HORIZONS)
    results = {}

    years = df["timestamp"].dt.year.unique()

    for h in HORIZONS:
        logger.info("  Analyzing horizon H=%d...", h)
        labeler = CausalDirectionalLabeler(horizon=h)
        labels_df = labeler.compute_labels(df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)

        is_purged = labels_df["is_purged"].to_numpy()
        valid_mask = ~is_purged
        target = labels_df["target_class"].to_numpy()

        n_total = len(df)
        n_valid = int(np.sum(valid_mask))
        n_purged = int(np.sum(is_purged))

        # Purge reasons breakdown
        purge_reasons = labels_df.loc[is_purged, "purge_reason"].value_counts().to_dict()

        # Class counts and percentages
        valid_targets = target[valid_mask].astype(int)
        class_counts = {
            "-1": int(np.sum(valid_targets == -1)),
            "0": int(np.sum(valid_targets == 0)),
            "1": int(np.sum(valid_targets == 1)),
        }
        class_pcts = {
            k: float(v / n_valid * 100.0) if n_valid > 0 else 0.0
            for k, v in class_counts.items()
        }

        # Yearly breakdown
        yearly_breakdown = {}
        max_shift = 0.0
        pct_1_by_year = []
        for y in sorted(years):
            y_mask = (df["timestamp"].dt.year == y).to_numpy()
            y_valid_mask = valid_mask & y_mask
            y_valid = int(np.sum(y_valid_mask))
            if y_valid > 0:
                y_targets = target[y_valid_mask].astype(int)
                y_c1 = int(np.sum(y_targets == 1))
                y_c0 = int(np.sum(y_targets == 0))
                y_cm1 = int(np.sum(y_targets == -1))
                p_long = float(y_c1 / y_valid * 100.0)
                p_neut = float(y_c0 / y_valid * 100.0)
                p_short = float(y_cm1 / y_valid * 100.0)
                pct_1_by_year.append(p_long)
                yearly_breakdown[int(y)] = {
                    "valid_rows": y_valid,
                    "counts": {"-1": y_cm1, "0": y_c0, "1": y_c1},
                    "pcts": {"-1": p_short, "0": p_neut, "1": p_long},
                }

        if len(pct_1_by_year) > 1:
            max_shift = float(max(pct_1_by_year) - min(pct_1_by_year))

        # Autocorrelation of target labels
        # Impute non-valid as 0 for contiguous autocorrelation calculation
        imputed_target = np.where(valid_mask, target, 0.0)
        target_series = pd.Series(imputed_target)
        lags = [1, 5, 12, 24, h]
        autocorrs = {}
        for lag in lags:
            if lag < len(target_series):
                autocorrs[f"lag_{lag}"] = float(target_series.autocorr(lag=lag))

        overlap_ratio = float((h - 1) / h)
        effective_n = float(n_valid / h)

        results[f"H_{h}"] = {
            "horizon_bars": h,
            "horizon_hours": float(h * 5 / 60.0),
            "total_rows": n_total,
            "valid_rows": n_valid,
            "purged_rows": n_purged,
            "purge_pct": float(n_purged / n_total * 100.0),
            "purge_reasons": purge_reasons,
            "class_counts": class_counts,
            "class_pcts": class_pcts,
            "majority_class": 1 if class_counts["1"] >= class_counts["-1"] else -1,
            "majority_baseline_accuracy": float(max(class_pcts.values()) / 100.0),
            "yearly_breakdown": yearly_breakdown,
            "max_yearly_class1_shift_pct": max_shift,
            "autocorrelations": autocorrs,
            "consecutive_bar_overlap_ratio": overlap_ratio,
            "effective_sample_size_neff": effective_n,
            "sample_inflation_factor": float(h),
        }

    return results


def audit_price_movement_vs_friction(df: pd.DataFrame) -> Dict[str, Any]:
    """Audit gross price movement, excursion (MFE/MAE), and transaction friction."""
    logger.info("Executing Section 2: Price Movement vs Execution Costs Audit...")
    results = {}

    opens = df["open"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    n_rows = len(df)

    high_series = df["high"]
    low_series = df["low"]
    open_series = df["open"]

    for h in HORIZONS:
        logger.info("  Analyzing movement & friction for H=%d...", h)

        # Forward entry is Open at t+1; Forward exit is Open at t+1+h
        # Valid indices: i in [0, n_rows - 1 - h)
        max_idx = n_rows - 1 - h
        if max_idx <= 0:
            continue

        entry_open = opens[1 : max_idx + 1]
        exit_open = opens[1 + h : max_idx + 1 + h]

        # Terminal move
        gross_terminal_move = np.abs(exit_open - entry_open)
        signed_terminal_move = exit_open - entry_open

        # Forward rolling max high and min low over the window [t+1, t+1+h]
        # Fast pandas rolling on reversed series
        fwd_max_high = high_series.iloc[::-1].rolling(h, min_periods=h).max().iloc[::-1].shift(-1).to_numpy()[1 : max_idx + 1]
        fwd_min_low = low_series.iloc[::-1].rolling(h, min_periods=h).min().iloc[::-1].shift(-1).to_numpy()[1 : max_idx + 1]

        valid_m = ~(np.isnan(fwd_max_high) | np.isnan(fwd_min_low) | np.isnan(gross_terminal_move))
        g_move = gross_terminal_move[valid_m]
        s_move = signed_terminal_move[valid_m]
        e_open = entry_open[valid_m]
        f_max = fwd_max_high[valid_m]
        f_min = fwd_min_low[valid_m]

        # Long MFE / MAE
        long_mfe = np.maximum(0.0, f_max - e_open)
        long_mae = np.maximum(0.0, e_open - f_min)

        # Short MFE / MAE
        short_mfe = np.maximum(0.0, e_open - f_min)
        short_mae = np.maximum(0.0, f_max - e_open)

        # Pooled MFE and MAE
        pooled_mfe = 0.5 * (long_mfe + short_mfe)
        pooled_mae = 0.5 * (long_mae + short_mae)

        mean_move = float(np.mean(g_move))
        median_move = float(np.median(g_move))
        std_move = float(np.std(g_move))

        # Friction drag percentages
        base_drag_mean = float(COST_BASE_ROUND_TURN / mean_move * 100.0)
        base_drag_median = float(COST_BASE_ROUND_TURN / median_move * 100.0)
        stress_drag_mean = float(COST_STRESS_ROUND_TURN / mean_move * 100.0)
        stress_drag_median = float(COST_STRESS_ROUND_TURN / median_move * 100.0)

        # Proportions covering cost
        pct_terminal_covers_base = float(np.mean(g_move > COST_BASE_ROUND_TURN) * 100.0)
        pct_terminal_covers_stress = float(np.mean(g_move > COST_STRESS_ROUND_TURN) * 100.0)

        pct_mfe_covers_base = float(np.mean(pooled_mfe > COST_BASE_ROUND_TURN) * 100.0)
        pct_mfe_covers_stress = float(np.mean(pooled_mfe > COST_STRESS_ROUND_TURN) * 100.0)

        pct_favorable_rr = float(np.mean(pooled_mfe > 2.0 * pooled_mae) * 100.0)

        # Theoretical required break-even win rate: w_be = 0.5 * (1 + Cost / G)
        be_win_rate_base = float(0.5 * (1.0 + COST_BASE_ROUND_TURN / median_move) * 100.0)
        be_win_rate_stress = float(0.5 * (1.0 + COST_STRESS_ROUND_TURN / median_move) * 100.0)

        results[f"H_{h}"] = {
            "horizon_bars": h,
            "horizon_hours": float(h * 5 / 60.0),
            "sample_count": int(np.sum(valid_m)),
            "gross_terminal_move": {
                "mean_usd": mean_move,
                "median_usd": median_move,
                "std_usd": std_move,
                "p25_usd": float(np.percentile(g_move, 25)),
                "p75_usd": float(np.percentile(g_move, 75)),
                "p90_usd": float(np.percentile(g_move, 90)),
                "p95_usd": float(np.percentile(g_move, 95)),
            },
            "signed_terminal_move": {
                "mean_usd": float(np.mean(s_move)),
                "median_usd": float(np.median(s_move)),
            },
            "excursions": {
                "mean_mfe_usd": float(np.mean(pooled_mfe)),
                "median_mfe_usd": float(np.median(pooled_mfe)),
                "mean_mae_usd": float(np.mean(pooled_mae)),
                "median_mae_usd": float(np.median(pooled_mae)),
                "mfe_mae_ratio": float(np.mean(pooled_mfe) / (np.mean(pooled_mae) + 1e-9)),
                "long_mean_mfe_usd": float(np.mean(long_mfe)),
                "long_mean_mae_usd": float(np.mean(long_mae)),
                "short_mean_mfe_usd": float(np.mean(short_mfe)),
                "short_mean_mae_usd": float(np.mean(short_mae)),
            },
            "cost_drag": {
                "base_round_turn_usd": COST_BASE_ROUND_TURN,
                "stress_round_turn_usd": COST_STRESS_ROUND_TURN,
                "base_cost_drag_pct_of_mean": base_drag_mean,
                "base_cost_drag_pct_of_median": base_drag_median,
                "stress_cost_drag_pct_of_mean": stress_drag_mean,
                "stress_cost_drag_pct_of_median": stress_drag_median,
            },
            "opportunity_coverage": {
                "pct_terminal_covers_base_cost": pct_terminal_covers_base,
                "pct_terminal_covers_stress_cost": pct_terminal_covers_stress,
                "pct_mfe_covers_base_cost": pct_mfe_covers_base,
                "pct_mfe_covers_stress_cost": pct_mfe_covers_stress,
                "pct_favorable_risk_reward_2x": pct_favorable_rr,
            },
            "break_even_hurdles": {
                "required_win_rate_base_cost_pct": be_win_rate_base,
                "required_win_rate_stress_cost_pct": be_win_rate_stress,
                "edge_hurdle_gap_vs_50pct_base": float(be_win_rate_base - 50.0),
                "edge_hurdle_gap_vs_50pct_stress": float(be_win_rate_stress - 50.0),
            },
        }

    return results


def audit_feature_redundancy_and_stability(df: pd.DataFrame) -> Dict[str, Any]:
    """Audit feature collinearity, redundancy, effective rank, and temporal drift."""
    logger.info("Executing Section 3: Feature Collinearity, Redundancy, and Stability Audit...")

    # Compute 42 causal market structure features
    logger.info("  Generating market structure features...")
    ms_engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)
    ms_df = ms_engine.compute_features(df, atr_series=df["atr_14"])
    full_df = pd.concat([df, ms_df], axis=1)

    non_feature_cols = {"timestamp", "open", "high", "low", "close", "volume"}
    feature_cols = [
        c for c in full_df.columns
        if c not in non_feature_cols and pd.api.types.is_numeric_dtype(full_df[c])
    ]
    n_features = len(feature_cols)
    logger.info("  Total features to audit: %d", n_features)

    # 1. Collinearity & Correlation Matrix
    X = full_df[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0).values
    corr_matrix = np.corrcoef(X.T)
    np.fill_diagonal(corr_matrix, 0.0)

    # Count high correlations
    abs_corr = np.abs(corr_matrix)
    triu_indices = np.triu_indices_from(abs_corr, k=1)
    pair_corrs = abs_corr[triu_indices]

    n_pairs_90 = int(np.sum(pair_corrs > 0.90))
    n_pairs_95 = int(np.sum(pair_corrs > 0.95))
    n_pairs_98 = int(np.sum(pair_corrs > 0.98))
    n_pairs_99 = int(np.sum(pair_corrs > 0.99))
    total_pairs = len(pair_corrs)

    # Top collinear pairs
    top_pair_indices = np.argsort(pair_corrs)[::-1][:20]
    top_collinear_pairs = []
    for idx in top_pair_indices:
        i, j = triu_indices[0][idx], triu_indices[1][idx]
        top_collinear_pairs.append({
            "feature_1": feature_cols[i],
            "feature_2": feature_cols[j],
            "abs_correlation": float(pair_corrs[idx]),
        })

    # 2. PCA & Effective Rank
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    pca = PCA().fit(X_scaled)
    cum_var = np.cumsum(pca.explained_variance_ratio_)

    n_comp_80 = int(np.searchsorted(cum_var, 0.80) + 1)
    n_comp_90 = int(np.searchsorted(cum_var, 0.90) + 1)
    n_comp_95 = int(np.searchsorted(cum_var, 0.95) + 1)
    n_comp_99 = int(np.searchsorted(cum_var, 0.99) + 1)

    # 3. Temporal Stability (2021 vs 2024 Distribution Drift)
    mask_2021 = (df["timestamp"].dt.year == 2021).to_numpy()
    mask_2024 = (df["timestamp"].dt.year == 2024).to_numpy()

    sample_features = [
        "ret_1", "log_ret_5", "atr_14", "natr_14", "rsi_14", "bb_bandwidth",
        "dist_ema_50", "dist_ema_200", "ema_slope_200", "garman_klass_vol_30",
        "ms_regime_bos", "ms_dist_swing_high_norm", "ms_dist_swing_low_norm"
    ]
    # Filter to existing
    sample_features = [f for f in sample_features if f in feature_cols]

    drift_results = {}
    for f in sample_features:
        vals_2021 = full_df.loc[mask_2021, f].dropna().values
        vals_2024 = full_df.loc[mask_2024, f].dropna().values
        if len(vals_2021) > 100 and len(vals_2024) > 100:
            ks_stat, ks_pval = stats.ks_2samp(vals_2021, vals_2024)

            # PSI computation (10 quantile bins based on 2021)
            quantiles = np.linspace(0, 1, 11)
            bins = np.percentile(vals_2021, quantiles * 100)
            bins = np.unique(bins)
            if len(bins) > 2:
                bins[0] = -np.inf
                bins[-1] = np.inf
                counts_21, _ = np.histogram(vals_2021, bins=bins)
                counts_24, _ = np.histogram(vals_2024, bins=bins)
                p21 = np.maximum(counts_21 / len(vals_2021), 1e-6)
                p24 = np.maximum(counts_24 / len(vals_2024), 1e-6)
                psi = float(np.sum((p24 - p21) * np.log(p24 / p21)))
            else:
                psi = 0.0

            drift_results[f] = {
                "mean_2021": float(np.mean(vals_2021)),
                "std_2021": float(np.std(vals_2021)),
                "mean_2024": float(np.mean(vals_2024)),
                "std_2024": float(np.std(vals_2024)),
                "ks_statistic": float(ks_stat),
                "ks_pvalue": float(ks_pval),
                "psi": psi,
                "is_drift_significant": bool(psi > 0.25 or ks_stat > 0.15),
            }

    return {
        "total_features": n_features,
        "collinearity": {
            "total_feature_pairs": total_pairs,
            "pairs_gt_90_corr": n_pairs_90,
            "pct_pairs_gt_90": float(n_pairs_90 / total_pairs * 100.0),
            "pairs_gt_95_corr": n_pairs_95,
            "pairs_gt_98_corr": n_pairs_98,
            "pairs_gt_99_corr": n_pairs_99,
            "top_collinear_pairs": top_collinear_pairs,
        },
        "pca_effective_rank": {
            "components_80_pct_variance": n_comp_80,
            "components_90_pct_variance": n_comp_90,
            "components_95_pct_variance": n_comp_95,
            "components_99_pct_variance": n_comp_99,
            "effective_rank_compression_ratio": float(n_comp_90 / n_features),
            "redundant_dimensions_count": int(n_features - n_comp_90),
        },
        "distributional_drift_2021_vs_2024": drift_results,
    }


def audit_regime_error_clustering(df: pd.DataFrame) -> Dict[str, Any]:
    """Audit model error patterns across market regimes using Phase 16 OOF predictions."""
    logger.info("Executing Section 4: Regime Error Clustering Audit...")
    if not OOF_PREDICTIONS_PATH.exists():
        logger.warning("OOF predictions file not found at %s. Skipping regime audit.", OOF_PREDICTIONS_PATH)
        return {"status": "SKIPPED_OOF_PREDICTIONS_MISSING"}

    oof_df = pd.read_parquet(OOF_PREDICTIONS_PATH)
    logger.info("  Loaded %d OOF prediction rows.", len(oof_df))

    # Merge features needed for regime classification: atr_14, dist_ema_200, timestamp
    feature_sub = df[["timestamp", "atr_14", "dist_ema_200"]].copy()
    merged = pd.merge(oof_df, feature_sub, on="timestamp", how="inner")
    logger.info("  Merged %d rows with features for regime analysis.", len(merged))

    # 1. Volatility Regimes (ATR Quartiles)
    atr = merged["atr_14"].to_numpy()
    atr_q = np.percentile(atr, [25, 50, 75])
    vol_regime = np.zeros(len(merged), dtype=int)
    vol_regime[atr < atr_q[0]] = 1      # Low Vol
    vol_regime[(atr >= atr_q[0]) & (atr < atr_q[1])] = 2  # Mid-Low Vol
    vol_regime[(atr >= atr_q[1]) & (atr < atr_q[2])] = 3  # Mid-High Vol
    vol_regime[atr >= atr_q[2]] = 4     # High Vol

    vol_labels = {1: "Low_Vol", 2: "MidLow_Vol", 3: "MidHigh_Vol", 4: "High_Vol"}
    vol_breakdown = {}
    for q_idx, q_name in vol_labels.items():
        q_mask = (vol_regime == q_idx)
        n_q = int(np.sum(q_mask))
        if n_q > 0:
            # Incumbent H=24 accuracy
            sub_24 = merged.loc[q_mask & merged["is_valid_h24"]]
            p_inc = np.argmax(sub_24[["prob_inc_short_h24", "prob_inc_neut_h24", "prob_inc_long_h24"]].values, axis=1) - 1
            y_24 = sub_24["target_class_h24"].values
            acc_24 = float(np.mean(p_inc == y_24)) if len(y_24) > 0 else 0.0

            # Candidate 5 H=96 accuracy
            sub_96 = merged.loc[q_mask & merged["is_valid_h96"]]
            p_c5 = np.argmax(sub_96[["prob_cand5_short_h96", "prob_cand5_neut_h96", "prob_cand5_long_h96"]].values, axis=1) - 1
            y_96 = sub_96["target_class_h96"].values
            acc_96 = float(np.mean(p_c5 == y_96)) if len(y_96) > 0 else 0.0

            vol_breakdown[q_name] = {
                "sample_count": n_q,
                "atr_range_usd": [float(np.min(atr[q_mask])), float(np.max(atr[q_mask]))],
                "incumbent_h24_accuracy": acc_24,
                "candidate5_h96_accuracy": acc_96,
                "incumbent_h24_error_rate": float(1.0 - acc_24),
                "candidate5_h96_error_rate": float(1.0 - acc_96),
            }

    # 2. Trend Regimes (dist_ema_200)
    dist_ema = merged["dist_ema_200"].to_numpy()
    trend_regime = np.zeros(len(merged), dtype=int)
    trend_regime[dist_ema > 2.0] = 1   # Strong Uptrend
    trend_regime[dist_ema < -2.0] = -1 # Strong Downtrend
    trend_regime[np.abs(dist_ema) <= 2.0] = 0 # Choppy/Range

    trend_labels = {1: "Strong_Uptrend", 0: "Choppy_Range", -1: "Strong_Downtrend"}
    trend_breakdown = {}
    for t_idx, t_name in trend_labels.items():
        t_mask = (trend_regime == t_idx)
        n_t = int(np.sum(t_mask))
        if n_t > 0:
            sub_24 = merged.loc[t_mask & merged["is_valid_h24"]]
            p_inc = np.argmax(sub_24[["prob_inc_short_h24", "prob_inc_neut_h24", "prob_inc_long_h24"]].values, axis=1) - 1
            y_24 = sub_24["target_class_h24"].values
            acc_24 = float(np.mean(p_inc == y_24)) if len(y_24) > 0 else 0.0

            sub_96 = merged.loc[t_mask & merged["is_valid_h96"]]
            p_c5 = np.argmax(sub_96[["prob_cand5_short_h96", "prob_cand5_neut_h96", "prob_cand5_long_h96"]].values, axis=1) - 1
            y_96 = sub_96["target_class_h96"].values
            acc_96 = float(np.mean(p_c5 == y_96)) if len(y_96) > 0 else 0.0

            trend_breakdown[t_name] = {
                "sample_count": n_t,
                "incumbent_h24_accuracy": acc_24,
                "candidate5_h96_accuracy": acc_96,
                "incumbent_h24_error_rate": float(1.0 - acc_24),
                "candidate5_h96_error_rate": float(1.0 - acc_96),
            }

    # 3. Session Regimes
    hours = merged["timestamp"].dt.hour.to_numpy()
    mins = merged["timestamp"].dt.minute.to_numpy()
    time_dec = hours + mins / 60.0

    session_regime = np.zeros(len(merged), dtype=object)
    session_regime[(time_dec >= 0.0) & (time_dec < 8.0)] = "Asian"
    session_regime[(time_dec >= 8.0) & (time_dec < 12.0)] = "London"
    session_regime[(time_dec >= 12.0) & (time_dec <= 16.5)] = "London_NY_Overlap"
    session_regime[(time_dec > 16.5) & (time_dec < 21.0)] = "NY_Afternoon"
    session_regime[session_regime == 0] = "Off_Hours"

    session_breakdown = {}
    for s_name in ["Asian", "London", "London_NY_Overlap", "NY_Afternoon", "Off_Hours"]:
        s_mask = (session_regime == s_name)
        n_s = int(np.sum(s_mask))
        if n_s > 0:
            sub_24 = merged.loc[s_mask & merged["is_valid_h24"]]
            p_inc = np.argmax(sub_24[["prob_inc_short_h24", "prob_inc_neut_h24", "prob_inc_long_h24"]].values, axis=1) - 1
            y_24 = sub_24["target_class_h24"].values
            acc_24 = float(np.mean(p_inc == y_24)) if len(y_24) > 0 else 0.0

            sub_96 = merged.loc[s_mask & merged["is_valid_h96"]]
            p_c5 = np.argmax(sub_96[["prob_cand5_short_h96", "prob_cand5_neut_h96", "prob_cand5_long_h96"]].values, axis=1) - 1
            y_96 = sub_96["target_class_h96"].values
            acc_96 = float(np.mean(p_c5 == y_96)) if len(y_96) > 0 else 0.0

            session_breakdown[s_name] = {
                "sample_count": n_s,
                "incumbent_h24_accuracy": acc_24,
                "candidate5_h96_accuracy": acc_96,
                "incumbent_h24_error_rate": float(1.0 - acc_24),
                "candidate5_h96_error_rate": float(1.0 - acc_96),
            }

    # 4. Directional Asymmetry by Year
    yearly_dir = {}
    for yr in [2022, 2023, 2024]:
        yr_mask = (merged["timestamp"].dt.year == yr)
        # H=96 Candidate 5 directional precision
        sub_96 = merged.loc[yr_mask & merged["is_valid_h96"]]
        p_c5 = np.argmax(sub_96[["prob_cand5_short_h96", "prob_cand5_neut_h96", "prob_cand5_long_h96"]].values, axis=1) - 1
        y_96 = sub_96["target_class_h96"].values

        long_preds = (p_c5 == 1)
        short_preds = (p_c5 == -1)
        long_prec = float(np.mean(y_96[long_preds] == 1)) if np.sum(long_preds) > 0 else 0.0
        short_prec = float(np.mean(y_96[short_preds] == -1)) if np.sum(short_preds) > 0 else 0.0

        yearly_dir[str(yr)] = {
            "candidate5_long_precision": long_prec,
            "candidate5_short_precision": short_prec,
            "long_short_precision_gap": float(long_prec - short_prec),
            "macro_regime_context": (
                "2022: Fed hiking cycle / rangebound gold"
                if yr == 2022 else (
                    "2023: Pause cycle / mild uptrend"
                    if yr == 2023 else "2024: Secular gold bull market rally (+26%)"
                )
            ),
        }

    return {
        "volatility_regimes": vol_breakdown,
        "trend_regimes": trend_breakdown,
        "session_regimes": session_breakdown,
        "directional_asymmetry_by_year": yearly_dir,
        "governance_note": (
            "All regime findings are exploratory diagnostic patterns identifying historical "
            "failure modes, NOT proven predictive signals. They must NOT be used for post-hoc "
            "rule filtering without independent, pre-specified validation."
        ),
    }


def main():
    """Main execution entrypoint for Phase 17 Diagnostic."""
    logger.info("=" * 80)
    logger.info("PHASE 17: RESEARCH FEASIBILITY & EDGE DIAGNOSTIC AUDIT")
    logger.info("=" * 80)

    # Verify protected partitions exist and are NOT modified
    val_path = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
    test_path = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"
    if not val_path.exists() or not test_path.exists():
        logger.error("Protected partitions missing from disk!")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Training Data ONLY
    logger.info("Loading training data from %s...", TRAIN_DATA_PATH)
    train_df = pd.read_parquet(TRAIN_DATA_PATH)
    logger.info("Loaded %d training rows spanning %s to %s.", len(train_df), train_df["timestamp"].min(), train_df["timestamp"].max())

    # 2. Section 1: Label Feasibility Audit
    label_diag = audit_label_feasibility(train_df)
    label_out = OUTPUT_DIR / "phase17_label_diagnostics.json"
    logger.info("Saving label diagnostics to %s...", label_out)
    with open(label_out, "w") as f:
        json.dump(label_diag, f, indent=2, cls=NpEncoder)

    # 3. Section 2: Price Movement vs Execution Costs Audit
    friction_diag = audit_price_movement_vs_friction(train_df)
    friction_out = OUTPUT_DIR / "phase17_friction_diagnostics.json"
    logger.info("Saving friction diagnostics to %s...", friction_out)
    with open(friction_out, "w") as f:
        json.dump(friction_diag, f, indent=2, cls=NpEncoder)

    # 4. Section 3: Feature Collinearity, Redundancy, and Stability Audit
    feature_diag = audit_feature_redundancy_and_stability(train_df)
    feature_out = OUTPUT_DIR / "phase17_feature_diagnostics.json"
    logger.info("Saving feature diagnostics to %s...", feature_out)
    with open(feature_out, "w") as f:
        json.dump(feature_diag, f, indent=2, cls=NpEncoder)

    # 5. Section 4: Regime Error Clustering Audit
    regime_diag = audit_regime_error_clustering(train_df)
    regime_out = OUTPUT_DIR / "phase17_regime_error_diagnostics.json"
    logger.info("Saving regime diagnostics to %s...", regime_out)
    with open(regime_out, "w") as f:
        json.dump(regime_diag, f, indent=2, cls=NpEncoder)

    logger.info("=" * 80)
    logger.info("PHASE 17 DIAGNOSTIC EXECUTION COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
