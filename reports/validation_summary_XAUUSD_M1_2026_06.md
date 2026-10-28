# Validation Summary: XAUUSD_M1_2026_06

**Overall Status**: FAILED (Integrity violations)
- **Total Records**: 30,144
- **Valid Records**: 30,092
- **Date Range**: 2026-06-01 05:00:00+00:00 to 2026-07-01 04:58:00+00:00
- **Errors**: 53
- **Warnings**: 0

## Data Integrity Checks
| Check | Result | Details |
| :--- | :---: | :--- |
| Missing / Null Values | PASS | {'timestamp': 0, 'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0} |
| Duplicate Timestamps | FAIL | 52 duplicates (0 identical, 26 conflicting) |
| Non-positive Prices (<= 0) | PASS | 0 invalid prices |
| High/Low Logic Violations | PASS | 0 candles violated High/Low logic |
| Chronological Ordering | FAIL | 13 out-of-order records |

## Market Gap & Session Analysis
- **Total Gaps Detected (> 1 min)**: 0
- **Weekend Closures (Legitimate)**: 0
- **Daily Session Roll Breaks (~1h Legitimate)**: 0
- **Holiday Closures (Legitimate)**: 0
- **Unexplained Gaps**: 0

### Suspicious Records Sample (Showing 5 of 20):
- **Index 27007** (2026-06-28 23:08:00+00:00): Duplicate timestamp | Values: Open=4082.505, High=None, Low=None, Close=4077.085
- **Index 27008** (2026-06-28 23:09:00+00:00): Duplicate timestamp | Values: Open=4076.885, High=None, Low=None, Close=4076.885
- **Index 27009** (2026-06-28 23:08:00+00:00): Duplicate timestamp | Values: Open=4077.005, High=None, Low=None, Close=4077.075
- **Index 27010** (2026-06-28 23:09:00+00:00): Duplicate timestamp | Values: Open=4077.085, High=None, Low=None, Close=4075.675
- **Index 27244** (2026-06-29 03:03:00+00:00): Duplicate timestamp | Values: Open=4066.695, High=None, Low=None, Close=4065.785
