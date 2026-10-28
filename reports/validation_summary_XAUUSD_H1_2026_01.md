# Validation Summary: XAUUSD_H1_2026_01

**Overall Status**: WARNING (Non-critical anomalies / Unexplained gaps)
- **Total Records**: 481
- **Valid Records**: 481
- **Date Range**: 2026-01-01 23:00:00+00:00 to 2026-01-30 21:00:00+00:00
- **Errors**: 0
- **Warnings**: 1

## Data Integrity Checks
| Check | Result | Details |
| :--- | :---: | :--- |
| Missing / Null Values | PASS | {'timestamp': 0, 'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0} |
| Duplicate Timestamps | PASS | 0 duplicates (0 identical, 0 conflicting) |
| Non-positive Prices (<= 0) | PASS | 0 invalid prices |
| High/Low Logic Violations | PASS | 0 candles violated High/Low logic |
| Chronological Ordering | PASS | 0 out-of-order records |

## Market Gap & Session Analysis
- **Total Gaps Detected (> 1 min)**: 20
- **Weekend Closures (Legitimate)**: 4
- **Daily Session Roll Breaks (~1h Legitimate)**: 15
- **Holiday Closures (Legitimate)**: 0
- **Unexplained Gaps**: 1

### Unexplained Gaps Details (Top 10):
| Start (UTC) | End (UTC) | Duration (min) | Start Day | End Day |
| :--- | :--- | :---: | :---: | :---: |
| 2026-01-19 19:00:00+00:00 | 2026-01-19 23:00:00+00:00 | 240.0 | Monday | Monday |
