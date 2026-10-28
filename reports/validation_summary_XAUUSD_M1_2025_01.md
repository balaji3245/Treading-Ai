# Validation Summary: XAUUSD_M1_2025_01

**Overall Status**: WARNING (Non-critical anomalies / Unexplained gaps)
- **Total Records**: 30,196
- **Valid Records**: 30,196
- **Date Range**: 2025-01-01 23:00:00+00:00 to 2025-01-31 21:58:00+00:00
- **Errors**: 0
- **Warnings**: 3

## Data Integrity Checks
| Check | Result | Details |
| :--- | :---: | :--- |
| Missing / Null Values | PASS | {'timestamp': 0, 'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0} |
| Duplicate Timestamps | PASS | 0 duplicates found |
| Non-positive Prices (<= 0) | PASS | 0 invalid prices |
| High/Low Logic Violations | PASS | 0 candles violated High/Low logic |
| Chronological Ordering | PASS | 0 out-of-order records |

## Market Gap & Session Analysis
- **Total Gaps Detected (> 1 min)**: 23
- **Weekend Closures (Legitimate)**: 4
- **Daily Session Roll Breaks (~1h Legitimate)**: 16
- **Holiday Closures (Legitimate)**: 0
- **Unexplained Gaps**: 3

### Unexplained Gaps Details (Top 10):
| Start (UTC) | End (UTC) | Duration (min) | Start Day | End Day |
| :--- | :--- | :---: | :---: | :---: |
| 2025-01-12 23:01:00+00:00 | 2025-01-12 23:03:00+00:00 | 2.0 | Sunday | Sunday |
| 2025-01-20 19:28:00+00:00 | 2025-01-20 23:00:00+00:00 | 212.0 | Monday | Monday |
| 2025-01-30 23:02:00+00:00 | 2025-01-30 23:05:00+00:00 | 3.0 | Thursday | Thursday |
