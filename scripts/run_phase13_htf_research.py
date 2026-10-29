"""Phase 13: Higher-Timeframe and Extended Horizon Strategy Research.

Strict Quantitative & Anti-Overfitting Protocol:
1. Data Scope: 2021-2024 Training partition ONLY (260,821 M5 bars).
2. Protected Partitions: ZERO access to 2025 Validation or frozen 2026 Test partitions.
3. Chronological Walk-Forward: 3 expanding-window folds with causal boundary purging.
4. Prespecified Candidate Configurations:
   - Candidate 0: No-Trade Baseline ($0.00)
   - Candidate 1: Existing Incumbent Strategy (M5, H=24 bars / 2h, threshold=0.60)
   - Candidate 2: Extended Intraday Swing (M5, H=48 bars / 4h, retrained ML + causal rules)
   - Candidate 3: Full Session Swing (M5, H=96 bars / 8h, retrained ML + causal rules)
   - Candidate 4: Multi-Timeframe Macro Trend Alignment (H=96 bars / 8h, H4 + H1 + M5 alignment)
   - Candidate 5: Peak Liquidity Session Swing (H=96 bars / 8h, London/NY Overlap entries only)
   - Candidate 6: Daily Multi-Session Swing (H=288 bars / 24h, retrained ML + causal rules)
5. Execution Friction:
   - Baseline Costs ($0.20 base spread, $0.05 base slippage, $0.10/oz round-turn commission)
   - Spread-Stress Scenario ($0.30 base spread, $0.075 slippage, $0.10/oz commission)
6. Deliverable: Output saved to reports/phase13_htf_experiment_results.json
"""

import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.economic_evaluator import EconomicEvaluator, TradeRecord
from treading_ai.config import FEATURES_DATA_DIR, REPORTS_DIR
from treading_ai.features.market_structure import MarketStructureEngine
from treading_ai.models.baselines import LogisticRegressionBaseline
from treading_ai.models.labeling import CausalDirectionalLabeler
from treading_ai.models.walk_forward import ChronologicalWalkForward
from treading_ai.policies.selective import SelectiveTradingPolicy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Phase13HTF")


def bootstrap_ci(
    data: np.ndarray,
    stat_func,
    n_bootstraps: int = 1000,
    ci: float = 0.95,
    random_state: int = 42,
) -> Tuple[float, float, float]:
    """Compute bootstrap point estimate and confidence interval."""
    rng = np.random.RandomState(random_state)
    point_est = float(stat_func(data)) if len(data) > 0 else 0.0
    if len(data) == 0:
        return 0.0, 0.0, 0.0
    boot_stats = []
    n = len(data)
    for _ in range(n_bootstraps):
        sample = rng.choice(data, size=n, replace=True)
        boot_stats.append(stat_func(sample))
    alpha = (1.0 - ci) / 2.0
    lower = float(np.percentile(boot_stats, 100 * alpha))
    upper = float(np.percentile(boot_stats, 100 * (1.0 - alpha)))
    return point_est, lower, upper


def holm_bonferroni_correction(p_values: List[float], alpha: float = 0.05) -> List[Dict[str, Any]]:
    """Compute Holm-Bonferroni step-down adjusted p-values."""
    m = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    results = [None] * m

    running_max_adj = 0.0
    for rank, (orig_idx, p_val) in enumerate(indexed):
        k = rank + 1
        adj_p = min(1.0, p_val * (m - k + 1))
        adj_p = max(adj_p, running_max_adj)
        running_max_adj = adj_p
        results[orig_idx] = {
            "raw_p_value": p_val,
            "adjusted_p_value": adj_p,
            "significant": bool(adj_p < alpha),
        }
    return results


def run_phase13_research() -> Dict[str, Any]:
    logger.info("=" * 80)
    logger.info("PHASE 13: HIGHER-TIMEFRAME & EXTENDED HORIZON STRATEGY RESEARCH")
    logger.info("=" * 80)

    t0_start = time.time()

    # 1. Load 2021-2024 Training Data Only
    train_path = FEATURES_DATA_DIR / "XAUUSD_M5_features_train.parquet"
    logger.info("Loading 2021-2024 training dataset from %s...", train_path)
    train_df = pd.read_parquet(train_path)
    n_rows = len(train_df)
    logger.info("Loaded %d rows.", n_rows)

    non_feature_cols = {"timestamp", "open", "high", "low", "close", "volume"}
    base_feature_cols = [c for c in train_df.columns if c not in non_feature_cols]

    # Extract Market Structure features
    logger.info("Computing 42 causal market structure features...")
    ms_engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)
    ms_features_df = ms_engine.compute_features(train_df, atr_series=train_df["atr_14"])
    ms_feature_cols = list(ms_features_df.columns)
    augmented_df = pd.concat([train_df, ms_features_df], axis=1)
    all_feature_cols = base_feature_cols + ms_feature_cols
    logger.info("Total augmented features: %d (Base: %d, MS: %d)", len(all_feature_cols), len(base_feature_cols), len(ms_feature_cols))

    BASELINE_ATR = 1.153
    BASELINE_RANGE = 1.050

    # 2. Prespecified Horizons & Causal Directional Labels
    horizons = [24, 48, 96, 288]
    labels_by_h = {}
    valid_mask_by_h = {}

    for H in horizons:
        # Scale weekend threshold to prevent false weekend purges on long holding periods
        thresh_hours = max(24.0, H * 5 / 60.0 + 20.0)
        lbl = CausalDirectionalLabeler(horizon=H, weekend_threshold_hours=thresh_hours)
        labels_df = lbl.compute_labels(train_df, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE)
        valid = ~labels_df["is_purged"].to_numpy()
        labels_by_h[H] = labels_df
        valid_mask_by_h[H] = valid
        logger.info("Horizon H=%d (%4.1fh): %d valid rows, %d purged rows.", H, H * 5 / 60.0, np.sum(valid), np.sum(~valid))

    # 3. Walk-Forward Setup (3 Expanding Folds)
    cwf = ChronologicalWalkForward(n_splits=3, horizon=24)
    folds = cwf.split_by_years(train_df, timestamp_col="timestamp")

    cost_model_base = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
    cost_model_stress = ExecutionCostModel(base_spread_usd=0.30, base_slippage_usd=0.075)

    evaluators_base = {H: EconomicEvaluator(cost_model_base, horizon=H, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE) for H in horizons}
    evaluators_stress = {H: EconomicEvaluator(cost_model_stress, horizon=H, baseline_atr=BASELINE_ATR, baseline_candle_range=BASELINE_RANGE) for H in horizons}

    # 4. Containers for Candidates
    candidate_keys = [
        "cand_0_notrade",
        "cand_1_incumbent_h24",
        "cand_2_swing_h48",
        "cand_3_session_h96",
        "cand_4_macro_aligned_h96",
        "cand_5_overlap_session_h96",
        "cand_6_daily_h288",
    ]

    candidate_names = {
        "cand_0_notrade": "Candidate 0: No-Trade Baseline",
        "cand_1_incumbent_h24": "Candidate 1: Existing Incumbent (M5, H=24 / 2h)",
        "cand_2_swing_h48": "Candidate 2: Extended Intraday Swing (M5, H=48 / 4h)",
        "cand_3_session_h96": "Candidate 3: Full Session Swing (M5, H=96 / 8h)",
        "cand_4_macro_aligned_h96": "Candidate 4: Multi-Timeframe Macro Trend Alignment (H=96 / 8h)",
        "cand_5_overlap_session_h96": "Candidate 5: Peak Liquidity Session Swing (H=96 / 8h, Overlap Only)",
        "cand_6_daily_h288": "Candidate 6: Daily Multi-Session Swing (H=288 / 24h)",
    }

    fold_results: Dict[str, List[Dict[str, Any]]] = {k: [] for k in candidate_keys}
    raw_trades_all: Dict[str, List[TradeRecord]] = {k: [] for k in candidate_keys}

    # 5. Walk-Forward Loop
    for fold in folds:
        logger.info("=" * 60)
        logger.info("PROCESSING CHRONOLOGICAL FOLD %d: Eval %s to %s", fold.fold_id, fold.eval_start_time.strftime("%Y-%m-%d"), fold.eval_end_time.strftime("%Y-%m-%d"))
        logger.info("=" * 60)

        ev_df = train_df.iloc[fold.eval_indices].copy().reset_index(drop=True)
        ev_aug_df = augmented_df.iloc[fold.eval_indices].copy().reset_index(drop=True)
        n_ev = len(ev_df)

        # Precompute evaluation causal context
        rolling_med_atr = ev_aug_df["atr_14"].rolling(288, min_periods=10).median().to_numpy()
        atr_arr = ev_aug_df["atr_14"].to_numpy()
        trend_state_arr = ev_aug_df["ms_trend_state"].to_numpy()
        session_names = cost_model_base.get_session_name_series(ev_df["timestamp"]).to_numpy()

        # HTF macro signals in eval
        h4_ret5 = ev_aug_df["htf_h4_ret_5"].to_numpy()
        h4_ema_ratio = ev_aug_df["htf_h4_ema_ratio_21_50"].to_numpy()
        h1_ret3 = ev_aug_df["htf_h1_ret_3"].to_numpy()

        # Fit models for H=24, H=48, H=96, H=288 on fold train
        models = {}
        for H in horizons:
            lbl_df = labels_by_h[H]
            v_mask = valid_mask_by_h[H]
            tr_mask = v_mask[fold.train_indices]
            tr_clean_idx = fold.train_indices[tr_mask]

            X_tr_feats = base_feature_cols if H == 24 else all_feature_cols
            X_tr = (train_df if H == 24 else augmented_df).iloc[tr_clean_idx][X_tr_feats]
            y_tr = lbl_df.iloc[tr_clean_idx]["target_class"].to_numpy(dtype=int)

            logger.info("Fitting Model H=%d on %d train samples with %d features...", H, len(X_tr), len(X_tr_feats))
            m = LogisticRegressionBaseline(max_iter=300, random_state=42)
            m.fit(X_tr, y_tr)
            models[H] = m

        # Predict probabilities in eval
        probas = {}
        for H in horizons:
            X_ev_feats = base_feature_cols if H == 24 else all_feature_cols
            X_ev = (ev_df if H == 24 else ev_aug_df)[X_ev_feats]
            probas[H] = models[H].predict_proba(X_ev)

        # -------------------------------------------------------------
        # CANDIDATE 0: No-Trade Baseline
        # -------------------------------------------------------------
        sigs_0 = np.zeros(n_ev, dtype=int)
        met_0_b, tr_0 = evaluators_base[24].evaluate(ev_df, sigs_0, model_name="Cand0_NoTrade")
        met_0_s, _ = evaluators_stress[24].evaluate(ev_df, sigs_0, model_name="Cand0_NoTrade")
        fold_results["cand_0_notrade"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": met_0_b.net_pnl_usd,
            "net_pnl_stress": met_0_s.net_pnl_usd,
            "gross_pnl": met_0_b.gross_pnl_usd,
            "friction": met_0_b.total_friction_usd,
            "trades": 0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "drawdown": 0.0,
        })

        # -------------------------------------------------------------
        # CANDIDATE 1: Existing Incumbent (H=24)
        # -------------------------------------------------------------
        policy_1 = SelectiveTradingPolicy(model=models[24], threshold=0.60, mode="non_overlapping", holding_horizon=24)
        out_1 = policy_1.generate_signals(ev_df[base_feature_cols])
        sigs_1 = out_1.signals
        met_1_b, tr_1 = evaluators_base[24].evaluate(ev_df, sigs_1, model_name="Cand1_Incumbent")
        met_1_s, _ = evaluators_stress[24].evaluate(ev_df, sigs_1, model_name="Cand1_Incumbent")
        raw_trades_all["cand_1_incumbent_h24"].extend(tr_1)
        fold_results["cand_1_incumbent_h24"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": met_1_b.net_pnl_usd,
            "net_pnl_stress": met_1_s.net_pnl_usd,
            "gross_pnl": met_1_b.gross_pnl_usd,
            "friction": met_1_b.total_friction_usd,
            "trades": met_1_b.n_completed_trades,
            "profit_factor": met_1_b.profit_factor_net,
            "win_rate": met_1_b.win_rate_net,
            "drawdown": met_1_b.max_drawdown_usd,
        })

        # Helper function for generating causal filtered & non-overlapping signals
        def build_filtered_signals(p_long, p_short, H_lockout, threshold=0.60, session_filter=None, macro_align=False):
            raw_sigs = np.zeros(n_ev, dtype=int)
            for idx in range(n_ev):
                if p_long[idx] >= threshold:
                    cand_d = 1
                elif p_short[idx] >= threshold:
                    cand_d = -1
                else:
                    cand_d = 0

                if cand_d == 0:
                    continue

                # Session restriction if specified
                if session_filter is not None and session_names[idx] != session_filter:
                    continue

                # Causal Rule 1: Regime Gating (Suppress compression)
                cur_med = rolling_med_atr[idx] if not np.isnan(rolling_med_atr[idx]) else atr_arr[idx]
                if atr_arr[idx] < cur_med * 0.90:
                    continue

                # Causal Rule 2: Structural Trend Alignment
                if cand_d == 1 and trend_state_arr[idx] == -1:
                    continue
                if cand_d == -1 and trend_state_arr[idx] == 1:
                    continue

                # Macro Alignment Rule (Candidate 4)
                if macro_align:
                    if cand_d == 1:
                        # Must be H4 bullish and H1 bullish and M5 bullish
                        if not (h4_ret5[idx] > 0 and h4_ema_ratio[idx] > 1.0 and h1_ret3[idx] > 0 and trend_state_arr[idx] == 1):
                            continue
                    else:
                        # Must be H4 bearish and H1 bearish and M5 bearish
                        if not (h4_ret5[idx] < 0 and h4_ema_ratio[idx] < 1.0 and h1_ret3[idx] < 0 and trend_state_arr[idx] == -1):
                            continue

                raw_sigs[idx] = cand_d

            # Non-overlapping lockout for H_lockout bars
            final_sigs = np.zeros(n_ev, dtype=int)
            lock = 0
            for idx in range(n_ev):
                if lock > 0:
                    lock -= 1
                    continue
                if raw_sigs[idx] != 0:
                    final_sigs[idx] = raw_sigs[idx]
                    lock = H_lockout
            return final_sigs

        # -------------------------------------------------------------
        # CANDIDATE 2: Extended Intraday Swing (H=48)
        # -------------------------------------------------------------
        sigs_2 = build_filtered_signals(probas[48][:, 2], probas[48][:, 0], H_lockout=48, threshold=0.60)
        met_2_b, tr_2 = evaluators_base[48].evaluate(ev_df, sigs_2, model_name="Cand2_Swing48")
        met_2_s, _ = evaluators_stress[48].evaluate(ev_df, sigs_2, model_name="Cand2_Swing48")
        raw_trades_all["cand_2_swing_h48"].extend(tr_2)
        fold_results["cand_2_swing_h48"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": met_2_b.net_pnl_usd,
            "net_pnl_stress": met_2_s.net_pnl_usd,
            "gross_pnl": met_2_b.gross_pnl_usd,
            "friction": met_2_b.total_friction_usd,
            "trades": met_2_b.n_completed_trades,
            "profit_factor": met_2_b.profit_factor_net,
            "win_rate": met_2_b.win_rate_net,
            "drawdown": met_2_b.max_drawdown_usd,
        })

        # -------------------------------------------------------------
        # CANDIDATE 3: Full Session Swing (H=96)
        # -------------------------------------------------------------
        sigs_3 = build_filtered_signals(probas[96][:, 2], probas[96][:, 0], H_lockout=96, threshold=0.60)
        met_3_b, tr_3 = evaluators_base[96].evaluate(ev_df, sigs_3, model_name="Cand3_Session96")
        met_3_s, _ = evaluators_stress[96].evaluate(ev_df, sigs_3, model_name="Cand3_Session96")
        raw_trades_all["cand_3_session_h96"].extend(tr_3)
        fold_results["cand_3_session_h96"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": met_3_b.net_pnl_usd,
            "net_pnl_stress": met_3_s.net_pnl_usd,
            "gross_pnl": met_3_b.gross_pnl_usd,
            "friction": met_3_b.total_friction_usd,
            "trades": met_3_b.n_completed_trades,
            "profit_factor": met_3_b.profit_factor_net,
            "win_rate": met_3_b.win_rate_net,
            "drawdown": met_3_b.max_drawdown_usd,
        })

        # -------------------------------------------------------------
        # CANDIDATE 4: Multi-Timeframe Macro Trend Alignment (H=96)
        # -------------------------------------------------------------
        sigs_4 = build_filtered_signals(probas[96][:, 2], probas[96][:, 0], H_lockout=96, threshold=0.55, macro_align=True)
        met_4_b, tr_4 = evaluators_base[96].evaluate(ev_df, sigs_4, model_name="Cand4_MacroAligned")
        met_4_s, _ = evaluators_stress[96].evaluate(ev_df, sigs_4, model_name="Cand4_MacroAligned")
        raw_trades_all["cand_4_macro_aligned_h96"].extend(tr_4)
        fold_results["cand_4_macro_aligned_h96"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": met_4_b.net_pnl_usd,
            "net_pnl_stress": met_4_s.net_pnl_usd,
            "gross_pnl": met_4_b.gross_pnl_usd,
            "friction": met_4_b.total_friction_usd,
            "trades": met_4_b.n_completed_trades,
            "profit_factor": met_4_b.profit_factor_net,
            "win_rate": met_4_b.win_rate_net,
            "drawdown": met_4_b.max_drawdown_usd,
        })

        # -------------------------------------------------------------
        # CANDIDATE 5: Peak Liquidity Session Swing (H=96, Overlap Only)
        # -------------------------------------------------------------
        sigs_5 = build_filtered_signals(probas[96][:, 2], probas[96][:, 0], H_lockout=96, threshold=0.60, session_filter="LONDON_NY_OVERLAP")
        met_5_b, tr_5 = evaluators_base[96].evaluate(ev_df, sigs_5, model_name="Cand5_OverlapOnly")
        met_5_s, _ = evaluators_stress[96].evaluate(ev_df, sigs_5, model_name="Cand5_OverlapOnly")
        raw_trades_all["cand_5_overlap_session_h96"].extend(tr_5)
        fold_results["cand_5_overlap_session_h96"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": met_5_b.net_pnl_usd,
            "net_pnl_stress": met_5_s.net_pnl_usd,
            "gross_pnl": met_5_b.gross_pnl_usd,
            "friction": met_5_b.total_friction_usd,
            "trades": met_5_b.n_completed_trades,
            "profit_factor": met_5_b.profit_factor_net,
            "win_rate": met_5_b.win_rate_net,
            "drawdown": met_5_b.max_drawdown_usd,
        })

        # -------------------------------------------------------------
        # CANDIDATE 6: Daily Multi-Session Swing (H=288)
        # -------------------------------------------------------------
        sigs_6 = build_filtered_signals(probas[288][:, 2], probas[288][:, 0], H_lockout=288, threshold=0.60)
        met_6_b, tr_6 = evaluators_base[288].evaluate(ev_df, sigs_6, model_name="Cand6_Daily288")
        met_6_s, _ = evaluators_stress[288].evaluate(ev_df, sigs_6, model_name="Cand6_Daily288")
        raw_trades_all["cand_6_daily_h288"].extend(tr_6)
        fold_results["cand_6_daily_h288"].append({
            "fold_id": fold.fold_id,
            "net_pnl_base": met_6_b.net_pnl_usd,
            "net_pnl_stress": met_6_s.net_pnl_usd,
            "gross_pnl": met_6_b.gross_pnl_usd,
            "friction": met_6_b.total_friction_usd,
            "trades": met_6_b.n_completed_trades,
            "profit_factor": met_6_b.profit_factor_net,
            "win_rate": met_6_b.win_rate_net,
            "drawdown": met_6_b.max_drawdown_usd,
        })

        logger.info(
            "Fold %d Summary: Incumbent: Net=$%.2f | H=48: Net=$%.2f | H=96: Net=$%.2f | Macro: Net=$%.2f | Overlap: Net=$%.2f | H=288: Net=$%.2f",
            fold.fold_id,
            met_1_b.net_pnl_usd,
            met_2_b.net_pnl_usd,
            met_3_b.net_pnl_usd,
            met_4_b.net_pnl_usd,
            met_5_b.net_pnl_usd,
            met_6_b.net_pnl_usd,
        )

    # 6. Aggregate Metrics & Statistical Testing for All Candidates
    logger.info("Computing Aggregate Metrics and Statistical Hypothesis Tests...")
    candidate_summaries = {}
    p_values_for_adjustment = []

    for key in candidate_keys:
        f_list = fold_results[key]
        trades = raw_trades_all[key]
        n_trades = len(trades)

        tot_net_base = sum(f["net_pnl_base"] for f in f_list)
        tot_net_stress = sum(f["net_pnl_stress"] for f in f_list)
        tot_gross = sum(f["gross_pnl"] for f in f_list)
        tot_friction = sum(f["friction"] for f in f_list)

        if n_trades > 0:
            net_pnls = np.array([t.net_pnl for t in trades], dtype=float)
            gross_pnls = np.array([t.gross_pnl for t in trades], dtype=float)
            frictions = np.array([t.total_friction for t in trades], dtype=float)
            directions = np.array([t.direction for t in trades], dtype=int)
            holding_bars_arr = np.array([t.holding_bars for t in trades], dtype=float)

            # Trade profit factors (Standard trade-level definition)
            gw = np.sum(gross_pnls[gross_pnls > 0])
            gl = abs(np.sum(gross_pnls[gross_pnls < 0]))
            trade_pf_gross = float(gw / gl) if gl > 0 else (100.0 if gw > 0 else 0.0)

            nw = np.sum(net_pnls[net_pnls > 0])
            nl = abs(np.sum(net_pnls[net_pnls < 0]))
            trade_pf_net = float(nw / nl) if nl > 0 else (100.0 if nw > 0 else 0.0)

            # Drawdown
            cum_net = np.cumsum(net_pnls)
            running_max = np.maximum.accumulate(cum_net)
            max_dd = float(np.max(running_max - cum_net)) if len(cum_net) > 0 else 0.0

            # Expectancies
            gross_exp = float(np.mean(gross_pnls))
            fric_exp = float(np.mean(frictions))
            net_exp = float(np.mean(net_pnls))
            win_rate = float(np.mean(net_pnls > 0))

            # Long / Short
            l_mask = directions == 1
            s_mask = directions == -1
            l_cnt = int(np.sum(l_mask))
            s_cnt = int(np.sum(s_mask))

            l_net = float(np.sum(net_pnls[l_mask])) if l_cnt > 0 else 0.0
            s_net = float(np.sum(net_pnls[s_mask])) if s_cnt > 0 else 0.0
            l_win = float(np.mean(net_pnls[l_mask] > 0)) if l_cnt > 0 else 0.0
            s_win = float(np.mean(net_pnls[s_mask] > 0)) if s_cnt > 0 else 0.0

            # Bootstrap CIs (95%)
            _, net_ci_lo, net_ci_hi = bootstrap_ci(net_pnls, np.mean)
            _, gross_ci_lo, gross_ci_hi = bootstrap_ci(gross_pnls, np.mean)

            # Hypothesis tests vs zero
            t_stat, p_val_t = stats.ttest_1samp(net_pnls, popmean=0.0)
            wilc_stat, p_val_wilc = stats.wilcoxon(net_pnls, alternative="two-sided")
            p_val = float(p_val_t)
            p_values_for_adjustment.append(p_val)

            # Break-even cost
            be_mult = float(gross_exp / fric_exp) if fric_exp > 0 else 0.0
            be_spread = float(0.20 * be_mult)

            avg_bars = float(np.mean(holding_bars_arr))
            avg_hours = float(avg_bars * 5 / 60.0)

        else:
            net_exp = 0.0
            gross_exp = 0.0
            fric_exp = 0.0
            trade_pf_gross = 0.0
            trade_pf_net = 0.0
            max_dd = 0.0
            win_rate = 0.0
            l_cnt = 0
            s_cnt = 0
            l_net = 0.0
            s_net = 0.0
            l_win = 0.0
            s_win = 0.0
            net_ci_lo = 0.0
            net_ci_hi = 0.0
            gross_ci_lo = 0.0
            gross_ci_hi = 0.0
            p_val = 1.0
            p_values_for_adjustment.append(p_val)
            t_stat = 0.0
            p_val_wilc = 1.0
            be_mult = 0.0
            be_spread = 0.0
            avg_bars = 0.0
            avg_hours = 0.0

        candidate_summaries[key] = {
            "candidate_key": key,
            "display_name": candidate_names[key],
            "trade_count": n_trades,
            "avg_holding_bars": avg_bars,
            "avg_holding_hours": avg_hours,
            "gross_pnl": tot_gross,
            "friction": tot_friction,
            "net_pnl_base": tot_net_base,
            "net_pnl_stress": tot_net_stress,
            "gross_expectancy": gross_exp,
            "friction_expectancy": fric_exp,
            "net_expectancy": net_exp,
            "net_win_rate": win_rate,
            "trade_profit_factor_gross": trade_pf_gross,
            "trade_profit_factor_net": trade_pf_net,
            "max_drawdown": max_dd,
            "fold_results": f_list,
            "long_breakdown": {"trades": l_cnt, "net_pnl": l_net, "win_rate": l_win},
            "short_breakdown": {"trades": s_cnt, "net_pnl": s_net, "win_rate": s_win},
            "ci_95_net_expectancy": [net_ci_lo, net_ci_hi],
            "ci_95_gross_expectancy": [gross_ci_lo, gross_ci_hi],
            "t_statistic": float(t_stat),
            "p_value_t": float(p_val),
            "p_value_wilcoxon": float(p_val_wilc),
            "break_even_cost_multiplier": be_mult,
            "break_even_base_spread_usd": be_spread,
        }

    # 7. Apply Holm-Bonferroni Correction
    holm_results = holm_bonferroni_correction(p_values_for_adjustment, alpha=0.05)
    for idx, key in enumerate(candidate_keys):
        candidate_summaries[key]["holm_bonferroni"] = holm_results[idx]

    # 8. Formal Decision Gate Evaluation
    gate_verdicts = {}
    for key, c in candidate_summaries.items():
        if key == "cand_0_notrade":
            gate_verdicts[key] = {"qualified": False, "reason": "Null Benchmark"}
            continue

        pos_net = c["net_pnl_base"] > 0.0
        pf_pass = c["trade_profit_factor_net"] > 1.00
        folds_positive = all(f["net_pnl_base"] > 0.0 for f in c["fold_results"])
        stress_pass = c["net_pnl_stress"] > 0.0
        sample_pass = c["trade_count"] >= 25

        qualified = pos_net and pf_pass and folds_positive and stress_pass and sample_pass

        reasons = []
        if not pos_net:
            reasons.append(f"Net PnL (${c['net_pnl_base']:.2f}) <= 0.00")
        if not pf_pass:
            reasons.append(f"Net Profit Factor ({c['trade_profit_factor_net']:.3f}) <= 1.00")
        if not folds_positive:
            reasons.append(f"Inconsistent across folds ({sum(1 for f in c['fold_results'] if f['net_pnl_base'] > 0)}/3 positive)")
        if not stress_pass:
            reasons.append(f"Stress Net PnL (${c['net_pnl_stress']:.2f}) <= 0.00")
        if not sample_pass:
            reasons.append(f"Insufficient trade count ({c['trade_count']} < 25)")

        gate_verdicts[key] = {
            "qualified": qualified,
            "decision": "QUALIFIED" if qualified else "REJECTED",
            "reasons": reasons if reasons else ["Meets all pre-registered criteria"],
        }

    experiment_report = {
        "experiment_name": "Phase 13 Higher Timeframe & Extended Horizon Research",
        "dataset": "2021-2024 Training Data Only",
        "total_rows": n_rows,
        "elapsed_seconds": time.time() - t0_start,
        "candidate_summaries": candidate_summaries,
        "gate_verdicts": gate_verdicts,
    }

    out_file = REPORTS_DIR / "phase13_htf_experiment_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(experiment_report, f, indent=2)

    logger.info("Saved complete Phase 13 experiment results to %s (Elapsed: %.2fs)", out_file, time.time() - t0_start)
    return experiment_report


if __name__ == "__main__":
    run_phase13_research()
