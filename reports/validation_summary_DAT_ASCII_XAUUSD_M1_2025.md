# Validation Summary: DAT_ASCII_XAUUSD_M1_2025

**Overall Status**: FAILED (Integrity violations)
- **Total Records**: 354,011
- **Valid Records**: 353,891
- **Date Range**: 2025-01-01 23:00:00+00:00 to 2025-12-31 21:57:00+00:00
- **Errors**: 121
- **Warnings**: 0

## Data Integrity Checks
| Check | Result | Details |
| :--- | :---: | :--- |
| Missing / Null Values | PASS | {'timestamp': 0, 'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0} |
| Duplicate Timestamps | FAIL | 120 duplicates found |
| Non-positive Prices (<= 0) | PASS | 0 invalid prices |
| High/Low Logic Violations | PASS | 0 candles violated High/Low logic |
| Chronological Ordering | FAIL | 1 out-of-order records |

## Market Gap & Session Analysis
- **Total Gaps Detected (> 1 min)**: 0
- **Weekend Closures (Legitimate)**: 0
- **Daily Session Roll Breaks (~1h Legitimate)**: 0
- **Holiday Closures (Legitimate)**: 0
- **Unexplained Gaps**: 0

### Suspicious Records Sample (Showing 5 of 11):
- **Index 290113** (2025-10-27 00:00:00+00:00): Duplicate timestamp | Values: Open=4064.275, High=None, Low=None, Close=4067.235
- **Index 290114** (2025-10-27 00:01:00+00:00): Duplicate timestamp | Values: Open=4067.155, High=None, Low=None, Close=4062.355
- **Index 290115** (2025-10-27 00:02:00+00:00): Duplicate timestamp | Values: Open=4062.365, High=None, Low=None, Close=4059.465
- **Index 290116** (2025-10-27 00:03:00+00:00): Duplicate timestamp | Values: Open=4059.335, High=None, Low=None, Close=4063.815
- **Index 290117** (2025-10-27 00:04:00+00:00): Duplicate timestamp | Values: Open=4063.775, High=None, Low=None, Close=4064.045
