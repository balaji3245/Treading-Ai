# Treading-AI: Phase 1 — Development Environment & Historical XAUUSD Data Pipeline

A quantitative market data pipeline engineering foundation for high-precision historical Spot Gold (`XAU/USD`) analysis, automated validation, and multi-timeframe resampling (`M1`, `M5`, `M15`, `M30`, `H1`, `H4`).

---

## 1. System & Architecture Overview

### Target Hardware Environment
- **Machine**: Dell Latitude 5410 (Intel Core i7-10610U @ 1.80GHz, 4 cores / 8 threads)
- **RAM**: 16 GB DDR4
- **Storage**: 512 GB NVMe SSD
- **Operating System**: Linux (Ubuntu 24.04 / 26.04 LTS)
- **Execution Target**: CPU-only, low-memory footprint, chunked streaming

### Technology Stack
- **Python**: 3.14+ (Compatible with Python 3.10+)
- **Data Engineering**: `pandas`, `numpy`, `pyarrow`
- **Networking**: `requests` (streaming chunks, exponential backoff)
- **Validation & Testing**: `pytest` (offline deterministic synthetic test fixtures)
- **Visualization**: `matplotlib` (headless Agg backend)

---

## 2. Project Directory Structure

```text
Treading-AI/
├── .env.example              # Configuration environment template
├── .gitignore                # Git ignore rules (keeps data & caches out of git)
├── README.md                 # Complete system documentation
├── requirements.txt          # Python dependency specifications
├── data/
│   ├── raw/                  # Original raw archives, uncompressed CSVs & provenance metadata
│   ├── processed/            # Multi-timeframe Parquet datasets (M1, M5, M15, M30, H1, H4)
│   └── features/             # Reserved for ML feature engineering (Phase 2+)
├── src/
│   └── treading_ai/
│       ├── __init__.py
│       ├── config.py         # Timeframes, schedule definitions, schemas, constants
│       ├── data_collection/
│       │   ├── __init__.py
│       │   └── downloader.py # Resumable HistData M1 downloader with SHA-256 provenance
│       ├── preprocessing/
│       │   ├── __init__.py
│       │   ├── resampler.py  # Financial OHLC multi-timeframe resampling
│       │   └── storage.py    # Memory-efficient Parquet reader/writer with PyArrow
│       └── validation/
│           ├── __init__.py
│           └── validator.py  # Automated OHLC integrity & market gap classifier
├── tests/
│   ├── conftest.py           # Offline synthetic test fixtures
│   ├── test_downloader.py    # Offline mocked network tests
│   ├── test_resampler.py     # Aggregation and incomplete candle tests
│   ├── test_storage.py       # Parquet round-trip, projection, and chunking tests
│   └── test_validator.py     # Anomaly, price sanity, and gap classification tests
├── scripts/
│   ├── download_data.py      # CLI script for downloading historical data
│   ├── validate_data.py      # CLI script for dataset validation
│   ├── process_timeframes.py # CLI script for resampling M1 into higher timeframes
│   ├── run_pipeline.py       # End-to-end pipeline orchestrator
│   └── plot_sample.py        # Generates multi-timeframe alignment charts
└── reports/
    ├── validation_report_*.json   # Machine-readable validation reports
    ├── validation_summary_*.md    # Human-readable markdown summaries
    └── multi_timeframe_sample.png # Visual candlestick/range alignment plot
```

---

## 3. Linux Setup & Virtual Environment

Follow these steps on a Linux terminal to configure the environment:

### Step 3.1: Create Virtual Environment
```bash
# Navigate to the workspace root
cd /home/bhoot/project/Treading-Ai

# Create virtual environment (use --without-pip if ensurepip is not packaged)
python3 -m venv --without-pip .venv

# Bootstrap pip inside the venv if needed
wget -q https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py
.venv/bin/python /tmp/get-pip.py
rm -f /tmp/get-pip.py
```

### Step 3.2: Install Dependencies
```bash
# Install core dependencies into virtual environment
.venv/bin/pip install -r requirements.txt
```

### Step 3.3: Configure Environment Variables
```bash
cp .env.example .env
```

---

## 4. Running Unit Tests

All unit tests use deterministic synthetic fixtures. **No internet connection is required.**

```bash
PYTHONPATH=src .venv/bin/pytest -v tests/
```

Test coverage includes:
- **`test_validator.py`**: OHLC column integrity, non-positive price detection, high/low order logic, duplicate timestamps, chronological ordering, and gap classification (weekend, daily roll break, holiday, and unexplained intraday gaps).
- **`test_resampler.py`**: Resampling mathematics (Open: first, High: max, Low: min, Close: last, Volume: sum), multi-timeframe scaling, detection of incomplete boundary bars, and non-fabrication of empty periods.
- **`test_storage.py`**: Parquet read/write round trip, schema enforcement, column projection, and chunked streaming.
- **`test_downloader.py`**: Token extraction regex, URL formulation, and mocked HTTP streaming without network calls.

---

## 5. Historical Data Source Investigation & Provenance

| Property | Details |
| :--- | :--- |
| **Data Provider** | [HistData.com](https://www.histdata.com) |
| **Instrument** | Spot Gold vs US Dollar (`XAU/USD`, `XAUUSD`) |
| **Asset Class** | Spot Commodity / Precious Metal Forex Quote |
| **Provenance Distinctions** | This is **true spot gold**, NOT COMEX futures (`GC=F`) and NOT an ETF (`GLD`). |
| **Base Resolution** | 1-Minute (`M1`) bar quotes |
| **Available Date Range** | Full annual archives from 2021 to 2025; monthly archives for current year (2026). |
| **Timezone** | **European DST interbank feeder server (`Europe/London - 5h`)**. Proven through NFP releases and session rollover breaks: UTC-5 in European winter, UTC-4 in European summer. |
| **Volume Semantics** | In Spot FX/Gold, trading volume is broker-specific and decentralized; HistData sets volume to `0` in ASCII bar archives. |
| **Market Closure Schedule** | Gold spot closes Friday 17:00 NY time and reopens Sunday 18:00 NY time: Winter close ~22:00 UTC / open ~23:00 UTC; Summer close ~21:00 UTC / open ~22:00 UTC. Daily roll breaks occur Mon-Thu for 1 hour at NY 17:00. |
| **Redistribution & License** | Free for research, backtesting, and development. Unauthenticated public HTTP download. |

---

## 6. Pipeline Execution Guide

### Option A: Run the Full End-to-End Pipeline
The pipeline runner downloads M1 raw data, verifies SHA-256 provenance, validates data integrity, resamples to `M1`, `M5`, `M15`, `M30`, `H1`, and `H4`, exports to Parquet, and writes validation reports:

```bash
# Default session-aligned H4 (anchored at 22:00 UTC / NY 17:00 close):
.venv/bin/python scripts/run_pipeline.py --year 2026 --month 1 --h4-alignment session

# Alternatively, standard UTC 0-aligned H4 (00:00, 04:00, ..., 20:00 UTC):
.venv/bin/python scripts/run_pipeline.py --year 2026 --month 1 --h4-alignment utc
```

### Option B: Modular Step-by-Step Execution

#### 1. Download Historical M1 Data
```bash
# Monthly archive (for current year 2026):
.venv/bin/python scripts/download_data.py --year 2026 --month 1 --symbol XAUUSD

# Annual archive (for completed years 2021-2025, do not pass --month):
.venv/bin/python scripts/download_data.py --year 2024 --symbol XAUUSD
```
- Raw ZIP and uncompressed CSV are placed into `data/raw/`.
- Provenance metadata is stored in `data/raw/HISTDATA_COM_ASCII_XAUUSD_M1{period}_metadata.json`.

#### 2. Validate Raw or Processed Data
```bash
# Validate raw CSV
.venv/bin/python scripts/validate_data.py data/raw/DAT_ASCII_XAUUSD_M1_202601.csv --timeframe-minutes 1

# Validate processed Parquet file (timeframe-aware gap classification)
.venv/bin/python scripts/validate_data.py data/processed/XAUUSD/H1/XAUUSD_H1_2026_01.parquet --timeframe-minutes 60
```
- Outputs machine-readable report to `reports/validation_report_<name>.json`.
- Outputs markdown summary to `reports/validation_summary_<name>.md`.

#### 3. Resample into Higher Timeframes
```bash
# Resample M1 to M5, M15, M30, H1, H4 (session-aligned H4 by default):
.venv/bin/python scripts/process_timeframes.py data/raw/DAT_ASCII_XAUUSD_M1_202601.csv --identifier 2026_01 --h4-alignment session
```
- Generates `data/processed/XAUUSD/{M1,M5,M15,M30,H1,H4}/XAUUSD_{TF}_2026_01.parquet`.

#### 4. Generate Visual Verification Charts
```bash
.venv/bin/python scripts/plot_sample.py --symbol XAUUSD --identifier 2026_01
```
- Saves a 3-panel multi-timeframe alignment chart (M1, M15, H1) to `reports/multi_timeframe_sample.png`.

---

## 7. Storage, Compression & Disk Usage

Measured disk consumption on Dell Latitude 5410:

| Artifact | Format | Record Count | Disk Size |
| :--- | :--- | :---: | :---: |
| Raw CSV (Jan 2026 M1) | CSV (Semicolon) | 28,827 | **1.81 MB** |
| Raw ZIP Archive | Compressed ZIP | 28,827 | **0.38 MB** |
| Processed M1 | Parquet (Snappy) | 28,827 | **0.83 MB** |
| Processed M5 | Parquet (Snappy) | 5,766 | **0.18 MB** |
| Processed M15 | Parquet (Snappy) | 1,922 | **0.07 MB** |
| Processed M30 | Parquet (Snappy) | 961 | **0.04 MB** |
| Processed H1 | Parquet (Snappy) | 481 | **0.02 MB** |
| Processed H4 | Parquet (Snappy) | 131 | **0.01 MB** |
| **Total Processed Dataset** | **Parquet** | **37,088 total bars** | **1.14 MB** |

**Total disk usage for 1 month of multi-timeframe gold data**: ~3.3 MB (raw + processed).
Expected 1 full year: ~40 MB.
5 full years: ~200 MB (well within 512 GB SSD capacity).

---

## 8. Data Quality Findings & Known Limitations

1. **Volume Semantics**: In spot retail and institutional gold feeds, aggregated tick volume does not exist due to OTC market structure. HistData explicitly sets volume to `0`. Downstream ML models must rely on price action, volatility, and multi-timeframe range features rather than trading volume.
2. **Session Closures**: Legitimate market closures occur on weekends (~48 hours) and daily maintenance rolls (1 hour between 22:00 and 23:00 UTC). The validator classifies these as legitimate market behavior.
3. **Holiday Exceptions**: Special sessions (e.g., US Martin Luther King Jr. Day early closing on Jan 19) produce early closure gaps that are documented as warnings in the validation report.
4. **Resampling Boundaries**: Higher timeframe bars (e.g. H4) that cross weekend or session breaks have fewer constituent M1 bars. The pipeline explicitly annotates every bar with `bar_count` and `is_complete` so subsequent feature engineering can handle or filter edge bars cleanly.
