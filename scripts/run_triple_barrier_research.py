"""Phase 7: Volatility-Scaled Triple-Barrier Labeling & Economic Research.

Strict Quantitative Research Protocol:
1. Labeling Framework:
   - Target barrier: +2.0 x ATR (causal, known at bar t close)
   - Stop barrier: -1.0 x ATR (causal, known at bar t close)
   - Time horizon: 24 M5 bars (2 hours)
   - Signal at bar t close, entry at bar t+1 open.
   - Barrier touch monitoring with conservative same-bar stop-first.
   - Gap fills execute at open price (realistic execution).
   - Tail boundary and weekend-crossing purge.
2. Expanding-Window Walk-Forward Validation (2021-2024):
   - Fold 1: Train 2021 -> Eval 2022
   - Fold 2: Train 2021-2022 -> Eval 2023
   - Fold 3: Train 2021-2023 -> Eval 2024
   - Boundary purging: last (1 + H_max) bars of each training fold purged.
3. Policy Modes:
   - Primary: non_overlapping (single-position capacity=1).
   - Secondary diagnostic: overlapping.
4. Experiment Sequence:
   - A. Fixed-Horizon H=24 baseline comparison.
   - B. Triple-Barrier model (2.0 ATR target, 1.0 ATR stop, 24-bar limit) with thresholding.
   - C. Cost sensitivity: Baseline, 2x spread & slippage, 3x spread & slippage.
   - D. Trend filter ablation: H4 EMA slope (Both directions, Long-only, Short-only).
   - E. Session gating ablation: London/NY overlap (13:00-16:30 UTC).
5. Accounting & Statistical Rigor:
   - Net PnL = Gross PnL - (Spread + Slippage + Commission), zero double-counting.
   - Aggregate metrics computed directly from underlying trade records.
   - Outlier sensitivity analysis (top 1% / top 3 trades removed).
   - 2026 Test partition strictly frozen and untouched.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.triple_barrier_simulator import (
    TripleBarrierMetrics,
    TripleBarrierSimulator,
    TripleBarrierTrade,
)
from treading_ai.models.baselines import LogisticRegressionBaseline
from treading_ai.models.evaluation import evaluate_classification
from treading_ai.models.triple_barrier_labeler import TripleBarrierLabeler
from treading_ai.models.walk_forward import ChronologicalWalkForward
from treading_ai.policies.selective import compute_brier_scores


def generate_directional_signals(
    probas: np.ndarray,
    threshold: Optional[float] = None,
    trend_filter: Optional[np.ndarray] = None,
    direction_mode: str = "both",  # "both", "long_only", "short_only"
    session_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Generate discrete directional signals {-1, 0, +1} from model probabilities with optional filters."""
    n_samples = len(probas)
    signals = np.zeros(n_samples, dtype=int)

    p_short = probas[:, 0]
    p_long = probas[:, 2]

    if threshold is None:
        # Standard argmax
        raw = np.argmax(probas, axis=1) - 1
        signals = raw.copy()
    elif threshold >= 1.0:
        # No-trade baseline
        return signals
    else:
        # Thresholded
        long_eligible = p_long >= threshold
        short_eligible = p_short >= threshold
        both_eligible = long_eligible & short_eligible
        long_eligible = long_eligible & (~both_eligible | (p_long > p_short))
        short_eligible = short_eligible & (~both_eligible | (p_short > p_long))

        signals[long_eligible] = 1
        signals[short_eligible] = -1

    # Direction mode filtering
    if direction_mode == "long_only":
        signals[signals == -1] = 0
    elif direction_mode == "short_only":
        signals[signals == 1] = 0

    # Trend filter alignment (H4 EMA slope)
    if trend_filter is not None:
        # Long only if slope > 0
        signals[(signals == 1) & (trend_filter <= 0.0)] = 0
        # Short only if slope < 0
        signals[(signals == -1) & (trend_filter >= 0.0)] = 0

    # Session gating filter
    if session_mask is not None:
        signals[~session_mask] = 0

    return signals


def analyze_outlier_sensitivity(trades: List[TripleBarrierTrade]) -> Dict[str, Any]:
    """Assess whether performance is driven by a small number of outlier winning trades."""
    if not trades:
        return {"n_trades": 0, "status": "no_trades"}

    net_pnls = np.array([t.net_pnl for t in trades], dtype=float)
    total_net = float(np.sum(net_pnls))
    sorted_pnls = np.sort(net_pnls)

    # Top 1% trades
    n_top_1pct = max(1, int(np.ceil(len(net_pnls) * 0.01)))
    pnl_without_top_1pct = float(np.sum(sorted_pnls[:-n_top_1pct]))

    # Top 3 trades
    n_top_3 = min(3, len(net_pnls))
    pnl_without_top_3 = float(np.sum(sorted_pnls[:-n_top_3]))

    return {
        "n_trades": len(trades),
        "total_net_pnl": total_net,
        "n_top_1pct": n_top_1pct,
        "pnl_without_top_1pct": pnl_without_top_1pct,
        "impact_top_1pct_usd": total_net - pnl_without_top_1pct,
        "n_top_3": n_top_3,
        "pnl_without_top_3": pnl_without_top_3,
        "impact_top_3_usd": total_net - pnl_without_top_3,
        "max_single_trade_pnl": float(sorted_pnls[-1]),
        "min_single_trade_pnl": float(sorted_pnls[0]),
    }


def run_triple_barrier_research() -> Dict[str, Any]:
    print("=" * 80)
    print("PHASE 7: VOLATILITY-SCALED TRIPLE-BARRIER WALK-FORWARD RESEARCH (2021-2024)")
    print("=" * 80)

    train_path = Path("data/features/XAUUSD_M5_features_train.parquet")
    if not train_path.exists():
        raise FileNotFoundError(f"Training features not found at {train_path}")

    print(f"Loading training data from {train_path}...")
    train_df = pd.read_parquet(train_path)
    n_total_bars = len(train_df)
    print(f"Loaded {n_total_bars:,} M5 bars spanning {train_df['timestamp'].min()} to {train_df['timestamp'].max()}")

    # Assert test partition is not touched
    assert "test" not in str(train_path).lower(), "Safety violation: test dataset accessed!"

    non_feature_cols = {"timestamp", "open", "high", "low", "close"}
    feature_cols = [c for c in train_df.columns if c not in non_feature_cols]
    print(f"Feature set size: {len(feature_cols)} features")

    BASELINE_ATR = 1.153
    BASELINE_RANGE = 1.050
    PT_ATR = 2.0
    SL_ATR = 1.0
    MAX_HOLDING = 24  # 2 hours

    # 1. Generate Causal Triple-Barrier Labels
    print("\n" + "-" * 80)
    print("STEP 1: GENERATING TRIPLE-BARRIER CAUSAL LABELS (PT=2.0 ATR, SL=1.0 ATR, H_max=24)")
    print("-" * 80)
    labeler = TripleBarrierLabeler(
        pt_atr=PT_ATR,
        sl_atr=SL_ATR,
        max_holding_bars=MAX_HOLDING,
        conservative_stop_first=True,
    )
    labels_df = labeler.compute_labels(
        train_df,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )

    valid_mask = ~labels_df["is_purged"].to_numpy()
    n_valid = int(np.sum(valid_mask))
    n_purged = int(np.sum(~valid_mask))
    print(f"Labels Generated: Valid={n_valid:,} ({n_valid/n_total_bars:.2%}), Purged={n_purged:,} ({n_purged/n_total_bars:.2%})")

    # Label Class Distribution
    valid_classes = labels_df.loc[valid_mask, "target_class"].to_numpy()
    n_long = int(np.sum(valid_classes == 1))
    n_neutral = int(np.sum(valid_classes == 0))
    n_short = int(np.sum(valid_classes == -1))
    print(f"Class Distribution: Long(+1)={n_long:,} ({n_long/n_valid:.2%}), Neutral(0)={n_neutral:,} ({n_neutral/n_valid:.2%}), Short(-1)={n_short:,} ({n_short/n_valid:.2%})")

    # Long event distribution
    long_events = labels_df.loc[valid_mask, "long_barrier_event"].value_counts().to_dict()
    short_events = labels_df.loc[valid_mask, "short_barrier_event"].value_counts().to_dict()
    print(f"Long Scenarios: {long_events}")
    print(f"Short Scenarios: {short_events}")

    label_diagnostics = {
        "total_bars": n_total_bars,
        "n_valid": n_valid,
        "n_purged": n_purged,
        "purge_rate": float(n_purged / n_total_bars),
        "class_distribution": {
            "long": n_long,
            "neutral": n_neutral,
            "short": n_short,
            "pct_long": float(n_long / n_valid),
            "pct_neutral": float(n_neutral / n_valid),
            "pct_short": float(n_short / n_valid),
        },
        "long_events": long_events,
        "short_events": short_events,
    }

    # 2. Configure Cost Models
    cost_base = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
    cost_2x = ExecutionCostModel(base_spread_usd=0.40, base_slippage_usd=0.10)
    cost_3x = ExecutionCostModel(base_spread_usd=0.60, base_slippage_usd=0.15)

    sim_base = TripleBarrierSimulator(
        pt_atr=PT_ATR,
        sl_atr=SL_ATR,
        max_holding_bars=MAX_HOLDING,
        cost_model=cost_base,
        mode="non_overlapping",
        conservative_stop_first=True,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )
    sim_2x = TripleBarrierSimulator(
        pt_atr=PT_ATR,
        sl_atr=SL_ATR,
        max_holding_bars=MAX_HOLDING,
        cost_model=cost_2x,
        mode="non_overlapping",
        conservative_stop_first=True,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )
    sim_3x = TripleBarrierSimulator(
        pt_atr=PT_ATR,
        sl_atr=SL_ATR,
        max_holding_bars=MAX_HOLDING,
        cost_model=cost_3x,
        mode="non_overlapping",
        conservative_stop_first=True,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )
    sim_base_overlap = TripleBarrierSimulator(
        pt_atr=PT_ATR,
        sl_atr=SL_ATR,
        max_holding_bars=MAX_HOLDING,
        cost_model=cost_base,
        mode="overlapping",
        conservative_stop_first=True,
        baseline_atr=BASELINE_ATR,
        baseline_candle_range=BASELINE_RANGE,
    )

    # 3. Setup Walk-Forward Validation
    cwf = ChronologicalWalkForward(n_splits=3, horizon=MAX_HOLDING)
    folds = cwf.split_by_years(train_df, timestamp_col="timestamp")

    # Grid of experiments to evaluate
    thresholds = [None, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 1.0]

    # Pre-train models and store evaluation probabilities per fold
    fold_models = {}
    fold_eval_data = {}

    print("\n" + "-" * 80)
    print("STEP 2: TRAINING DIRECTIONAL MODELS ON EXPANDING FOLDS (2021-2024)")
    print("-" * 80)

    for fold in folds:
        print(f"\nFitting Model on Fold {fold.fold_id} (Train {fold.train_start_time.year}-{fold.train_end_time.year} -> Eval {fold.eval_start_time.year})")
        fold_tr_df = train_df.iloc[fold.train_indices]
        fold_ev_df = train_df.iloc[fold.eval_indices]
        fold_tr_lbl = labels_df.iloc[fold.train_indices]
        fold_ev_lbl = labels_df.iloc[fold.eval_indices]

        tr_mask = ~fold_tr_lbl["is_purged"].to_numpy()
        ev_mask = ~fold_ev_lbl["is_purged"].to_numpy()

        X_tr = fold_tr_df.loc[tr_mask, feature_cols]
        y_tr = fold_tr_lbl.loc[tr_mask, "target_class"].to_numpy(dtype=int)

        X_ev = fold_ev_df.loc[ev_mask, feature_cols]
        y_ev = fold_ev_lbl.loc[ev_mask, "target_class"].to_numpy(dtype=int)

        model = LogisticRegressionBaseline(max_iter=300, random_state=42)
        model.fit(X_tr, y_tr)

        ev_probas = model.predict_proba(X_ev)
        brier = compute_brier_scores(y_ev, ev_probas)

        unfilt_preds = model.predict(X_ev)
        cls_metrics = evaluate_classification(
            y_true=y_ev,
            y_pred=unfilt_preds,
            model_name=f"LR_TripleBarrier_Fold{fold.fold_id}",
            split_name=f"Fold_{fold.fold_id}_Eval_{fold.eval_start_time.year}",
            n_total=fold.n_eval,
            n_purged=int(np.sum(~ev_mask)),
        )

        print(f"  Fold {fold.fold_id} Eval: Acc={cls_metrics.accuracy:.4f} | BalAcc={cls_metrics.balanced_accuracy:.4f} | "
              f"Macro-F1={cls_metrics.macro_f1:.4f} | Brier={brier['brier_total']:.4f}")

        # Trend filter (H4 EMA slope) on evaluation set
        trend_h4 = fold_ev_df["htf_h4_ema_slope_50"].to_numpy(dtype=float)
        # Session overlap mask on evaluation set
        session_overlap = fold_ev_df["session_london_ny_overlap"].to_numpy(dtype=int) == 1

        fold_models[fold.fold_id] = model
        fold_eval_data[fold.fold_id] = {
            "eval_df": fold_ev_df,
            "eval_mask": ev_mask,
            "y_ev": y_ev,
            "probas": ev_probas,
            "cls_metrics": cls_metrics,
            "brier": brier,
            "trend_h4": trend_h4,
            "session_overlap": session_overlap,
        }

    # 4. Run Experiment Matrix across all folds
    # Configurations to test:
    # 1. Base threshold sweep (non_overlapping & overlapping)
    # 2. Cost sensitivity on threshold sweep (2x and 3x costs)
    # 3. Trend filter ablation (Both-direction, Long-only, Short-only)
    # 4. Session gating ablation (London/NY overlap)

    experiment_definitions: List[Dict[str, Any]] = []

    # B. Core Threshold Grid (Non-overlapping)
    for th in thresholds:
        th_name = "Unfiltered" if th is None else ("No-Trade" if th >= 1.0 else f"Thresh={th:.2f}")
        experiment_definitions.append({
            "category": "core_threshold_non_overlapping",
            "name": f"TB_{th_name}_NonOverlap",
            "threshold": th,
            "mode": "non_overlapping",
            "direction_mode": "both",
            "trend_filter": False,
            "session_gating": False,
            "cost_tier": "base",
        })

    # Core Threshold Grid (Overlapping diagnostic)
    for th in [None, 0.50, 0.60, 1.0]:
        th_name = "Unfiltered" if th is None else ("No-Trade" if th >= 1.0 else f"Thresh={th:.2f}")
        experiment_definitions.append({
            "category": "core_threshold_overlapping_diagnostic",
            "name": f"TB_{th_name}_Overlapping",
            "threshold": th,
            "mode": "overlapping",
            "direction_mode": "both",
            "trend_filter": False,
            "session_gating": False,
            "cost_tier": "base",
        })

    # C. Cost Sensitivity Grid (2x and 3x costs on Non-overlapping)
    for cost_tier in ["cost_2x", "cost_3x"]:
        for th in [None, 0.50, 0.55, 0.60, 0.65]:
            th_name = "Unfiltered" if th is None else f"Thresh={th:.2f}"
            tier_label = "2xCosts" if cost_tier == "cost_2x" else "3xCosts"
            experiment_definitions.append({
                "category": "cost_sensitivity",
                "name": f"TB_{th_name}_{tier_label}",
                "threshold": th,
                "mode": "non_overlapping",
                "direction_mode": "both",
                "trend_filter": False,
                "session_gating": False,
                "cost_tier": cost_tier,
            })

    # D. Trend Filter Ablation Grid (H4 EMA Slope)
    for d_mode in ["both", "long_only", "short_only"]:
        for th in [None, 0.50, 0.60]:
            th_name = "Unfiltered" if th is None else f"Thresh={th:.2f}"
            experiment_definitions.append({
                "category": "trend_ablation",
                "name": f"TB_{th_name}_TrendH4_{d_mode}",
                "threshold": th,
                "mode": "non_overlapping",
                "direction_mode": d_mode,
                "trend_filter": True,
                "session_gating": False,
                "cost_tier": "base",
            })

    # Long-only / Short-only without trend filter (directional isolation)
    for d_mode in ["long_only", "short_only"]:
        for th in [None, 0.50, 0.60]:
            th_name = "Unfiltered" if th is None else f"Thresh={th:.2f}"
            experiment_definitions.append({
                "category": "direction_ablation",
                "name": f"TB_{th_name}_NoTrend_{d_mode}",
                "threshold": th,
                "mode": "non_overlapping",
                "direction_mode": d_mode,
                "trend_filter": False,
                "session_gating": False,
                "cost_tier": "base",
            })

    # E. Session Gating Ablation Grid (London/NY overlap)
    for th in [None, 0.50, 0.60]:
        th_name = "Unfiltered" if th is None else f"Thresh={th:.2f}"
        experiment_definitions.append({
            "category": "session_ablation",
            "name": f"TB_{th_name}_SessionOverlapOnly",
            "threshold": th,
            "mode": "non_overlapping",
            "direction_mode": "both",
            "trend_filter": False,
            "session_gating": True,
            "cost_tier": "base",
        })

    print(f"\nTotal experimental configurations to evaluate across 3 folds: {len(experiment_definitions)}")

    all_experiments_results = []

    # Reference fixed-horizon H=24 baseline for direct comparison
    # (From Phase 6 research records)
    h24_reference_baseline = {
        "Unfiltered": {"trades": 8184, "gross_usd": 2.81, "net_usd": -4872.40, "pf_net": 0.726},
        "Thresh=0.50": {"trades": 5879, "gross_usd": 232.10, "net_usd": -3194.03, "pf_net": 0.772},
        "Thresh=0.60": {"trades": 2733, "gross_usd": 308.00, "net_usd": -1340.90, "pf_net": 0.835},
        "No-Trade": {"trades": 0, "gross_usd": 0.0, "net_usd": 0.0, "pf_net": 0.0},
    }

    # Execute all configurations
    for exp in experiment_definitions:
        exp_name = exp["name"]
        cat = exp["category"]
        th = exp["threshold"]
        mode = exp["mode"]
        d_mode = exp["direction_mode"]
        use_trend = exp["trend_filter"]
        use_session = exp["session_gating"]
        cost_tier = exp["cost_tier"]

        fold_records = []
        combined_trades: List[TripleBarrierTrade] = []
        total_eval_bars = 0
        total_tradable_bars = 0
        sum_eligible = 0
        sum_cap_rej = 0
        sum_close_rej = 0

        for fold in folds:
            f_data = fold_eval_data[fold.fold_id]
            ev_df = f_data["eval_df"]
            ev_mask = f_data["eval_mask"]
            probas = f_data["probas"]
            trend_h4 = f_data["trend_h4"] if use_trend else None
            session_overlap = f_data["session_overlap"] if use_session else None

            # Generate signals on valid evaluation bars
            signals_valid = generate_directional_signals(
                probas=probas,
                threshold=th,
                trend_filter=trend_h4[ev_mask] if use_trend else None,
                direction_mode=d_mode,
                session_mask=session_overlap[ev_mask] if use_session else None,
            )

            # Map signals back to full eval_df indexing
            full_signals = np.zeros(len(ev_df), dtype=int)
            full_signals[ev_mask] = signals_valid

            # Select simulator
            if mode == "overlapping":
                sim = sim_base_overlap
            else:
                if cost_tier == "cost_2x":
                    sim = sim_2x
                elif cost_tier == "cost_3x":
                    sim = sim_3x
                else:
                    sim = sim_base

            metrics, trades = sim.simulate(
                df=ev_df,
                signals=full_signals,
                strategy_name=exp_name,
                scenario_name=cost_tier,
                mask=None,
            )

            fold_records.append({
                "fold_id": fold.fold_id,
                "eval_year": fold.eval_start_time.year,
                "metrics": metrics.to_dict(),
            })

            combined_trades.extend(trades)
            total_eval_bars += metrics.total_bars
            total_tradable_bars += metrics.tradable_bars
            sum_eligible += metrics.n_eligible_signals
            sum_cap_rej += metrics.n_capacity_rejected
            sum_close_rej += metrics.n_closure_rejected

        # Compute Aggregate Metrics directly from combined underlying trades
        agg_metrics = TripleBarrierSimulator.compute_aggregate_metrics(
            trades=combined_trades,
            total_bars=total_eval_bars,
            tradable_bars=total_tradable_bars,
            n_eligible_signals=sum_eligible,
            n_capacity_rejected=sum_cap_rej,
            n_closure_rejected=sum_close_rej,
            strategy_name=exp_name,
            scenario_name=cost_tier,
        )

        # Outlier sensitivity
        outlier_analysis = analyze_outlier_sensitivity(combined_trades)

        # Fold stability check: count positive folds
        positive_folds = sum(1 for fr in fold_records if fr["metrics"]["net_pnl_usd"] > 0)

        result_entry = {
            "experiment": exp,
            "aggregate_metrics": agg_metrics.to_dict(),
            "outlier_sensitivity": outlier_analysis,
            "fold_stability": {
                "positive_folds": positive_folds,
                "total_folds": len(folds),
                "is_consistently_positive": positive_folds == len(folds),
            },
            "fold_records": fold_records,
        }
        all_experiments_results.append(result_entry)

        # Print summary for primary non_overlapping core experiments
        if cat in ["core_threshold_non_overlapping", "core_threshold_overlapping_diagnostic"]:
            print(
                f"  {exp_name:30s} | Trades: {agg_metrics.n_completed_trades:5d} | "
                f"Gross: ${agg_metrics.gross_pnl_usd:>8.2f} | Net: ${agg_metrics.net_pnl_usd:>8.2f} | "
                f"PF_net: {agg_metrics.profit_factor_net:5.3f} | WinNet: {agg_metrics.win_rate_net:5.2%} | "
                f"MeanNet: ${agg_metrics.avg_net_pnl_per_trade:>6.3f} | MaxDD: ${agg_metrics.max_drawdown_usd:>7.2f}"
            )

    print("\n" + "=" * 80)
    print("STEP 3: SUMMARY OF RESULTS & ABLATIONS")
    print("=" * 80)

    # Print summary of trend ablations
    print("\n--- Trend Ablation Summary (Primary Non-overlapping, Base Costs) ---")
    trend_res = [r for r in all_experiments_results if r["experiment"]["category"] == "trend_ablation"]
    for r in trend_res:
        agg = r["aggregate_metrics"]
        print(f"  {agg['strategy_name']:32s} | Trades: {agg['n_completed_trades']:5d} | Net: ${agg['net_pnl_usd']:>8.2f} | PF: {agg['profit_factor_net']:5.3f} | WinNet: {agg['win_rate_net']:5.2%}")

    # Print summary of session ablations
    print("\n--- Session Gating Ablation Summary (London/NY Overlap, Base Costs) ---")
    sess_res = [r for r in all_experiments_results if r["experiment"]["category"] == "session_ablation"]
    for r in sess_res:
        agg = r["aggregate_metrics"]
        print(f"  {agg['strategy_name']:32s} | Trades: {agg['n_completed_trades']:5d} | Net: ${agg['net_pnl_usd']:>8.2f} | PF: {agg['profit_factor_net']:5.3f} | WinNet: {agg['win_rate_net']:5.2%}")

    # Print summary of cost sensitivity
    print("\n--- Cost Sensitivity Summary ---")
    cost_res = [r for r in all_experiments_results if r["experiment"]["category"] == "cost_sensitivity"]
    for r in cost_res:
        agg = r["aggregate_metrics"]
        print(f"  {agg['strategy_name']:32s} | Trades: {agg['n_completed_trades']:5d} | Gross: ${agg['gross_pnl_usd']:>8.2f} | Net: ${agg['net_pnl_usd']:>8.2f} | PF: {agg['profit_factor_net']:5.3f}")

    # Check candidate qualification against training folds
    print("\n" + "=" * 80)
    print("STEP 4: CANDIDATE POLICY QUALIFICATION CHECK")
    print("=" * 80)
    # Qualification criteria:
    # 1. Aggregate Net PnL > $0.00
    # 2. At least 2 of 3 folds have Net PnL > $0.00
    # 3. Minimum 100 completed trades
    # 4. Profit Factor Net > 1.0 under baseline costs
    # 5. Non-overlapping mode

    qualifying_candidates = []
    for r in all_experiments_results:
        exp = r["experiment"]
        agg = r["aggregate_metrics"]
        stab = r["fold_stability"]

        # Only evaluate non_overlapping under base costs for candidate status
        if exp["mode"] == "non_overlapping" and exp["cost_tier"] == "base" and exp["threshold"] is not None and exp["threshold"] < 1.0:
            is_positive_net = agg["net_pnl_usd"] > 0.0
            is_consistent = stab["positive_folds"] >= 2
            has_min_trades = agg["n_completed_trades"] >= 100
            pf_valid = agg["profit_factor_net"] > 1.0

            if is_positive_net and is_consistent and has_min_trades and pf_valid:
                qualifying_candidates.append(r)
                print(f"  QUALIFIED: {exp['name']} | Net PnL: ${agg['net_pnl_usd']:.2f} | PF: {agg['profit_factor_net']:.3f} | Folds Pos: {stab['positive_folds']}/3 | Trades: {agg['n_completed_trades']}")

    if not qualifying_candidates:
        print("  NO candidate policy qualified under the pre-registered training-fold criteria.")
        print("  All triple-barrier configurations produced negative net expectancy after transaction costs.")
        qualification_status = "REJECTED_ON_TRAIN"
    else:
        print(f"  {len(qualifying_candidates)} candidate policies qualified for locked 2025 confirmation.")
        qualification_status = "QUALIFIED_FOR_CONFIRMATION"

    final_payload = {
        "metadata": {
            "research_phase": "Phase 7",
            "strategy": "Volatility-Scaled Triple Barrier",
            "dataset": "XAUUSD_M5_features_train.parquet (2021-2024)",
            "test_partition_status": "FROZEN_AND_UNTOUCHED",
            "qualification_status": qualification_status,
            "baseline_atr": BASELINE_ATR,
            "baseline_range": BASELINE_RANGE,
            "pt_atr": PT_ATR,
            "sl_atr": SL_ATR,
            "max_holding_bars": MAX_HOLDING,
            "qualification_criteria": {
                "min_aggregate_net_pnl_usd": 0.0,
                "min_positive_folds": 2,
                "min_completed_trades": 100,
                "min_profit_factor_net": 1.0,
                "mode": "non_overlapping",
            },
        },
        "label_diagnostics": label_diagnostics,
        "h24_reference_baseline": h24_reference_baseline,
        "experiment_results": all_experiments_results,
        "qualifying_candidates": [q["experiment"]["name"] for q in qualifying_candidates],
    }

    return final_payload


if __name__ == "__main__":
    results = run_triple_barrier_research()
    out_dir = Path("data/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase7_triple_barrier_research.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nPhase 7 Triple-Barrier research successfully exported to {out_file}")
