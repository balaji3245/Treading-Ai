# Phase 29 AWS Cloud Architecture & Cost Control Plan

**Phase:** 29 — Data Acquisition Plan, Provider Evaluation & Cost Architecture  
**Role:** Cloud Cost Auditor & Quantitative Infrastructure Engineer  
**Date:** October 2026  
**Status:** COMPLETE & INDEPENDENTLY AUDITED  

---

## Executive Summary

This report establishes a practical, cost-conscious cloud resource architecture for acquiring, storing, and preprocessing expanded market data for Treading-Ai. 

### Core Audit Principles:
1. **Zero Unnecessary Cloud Spend:** The project currently runs on local workstation compute. Before spending capital on AWS instances or managed services, local processing must be prioritized ($0.00 recurring cost).
2. **Strict Non-Creation Policy:** No AWS instances, S3 buckets, or paid cloud services were launched during this audit.
3. **No Assumed Free Credits:** Because no AWS budget or credit allocations are documented in the repository, this plan calculates raw on-demand and spot pricing, ensuring total financial transparency.

---

## 1. Existing AWS Footprint Verification

A forensic inspection of the repository confirmed the following:
- **`~/.aws` Directory:** **Does not exist** [VERIFIED FACT].
- **Environment Variables:** No AWS keys (`AWS_ACCESS_KEY_ID`, etc.) exist in the shell environment [VERIFIED FACT].
- **Python Libraries:** Neither `boto3` nor `s3fs` are installed in the Python environment [VERIFIED FACT].
- **Documented Budget:** There is **zero documented cloud budget** in repository records [VERIFIED FACT].
- **Current Monthly Spend:** **$0.00 / month** [VERIFIED FACT].

---

## 2. Market Data Storage & Compute Sizing Requirements

To evaluate whether cloud infrastructure is necessary, we calculate the exact storage and compute footprint for 10 years of multi-resolution historical data across spot and futures:

```
+-------------------------------------------------------------------------------------------------------------------+
|                                   DATASET STORAGE SIZING ESTIMATES (10 YEARS)                                     |
+---------------------+-------------+-------------------+--------------------+------------------+-------------------+
| Dataset Type        | Provider    | Raw Compressed    | Raw Decompressed   | Parquet (Snappy) | Annual Increment  |
+---------------------+-------------+-------------------+--------------------+------------------+-------------------+
| XAUUSD Tick (Bid/Ask| Dukascopy   | ~18.0 GB (.bi5)   | ~110.0 GB (CSV)    | ~28.0 GB (Pq)    | ~3.0 GB / year    |
| XAUUSD M1 OHLCV     | Dukascopy   | ~3.5 GB (CSV.gz)  | ~16.0 GB (CSV)     | ~4.2 GB (Pq)     | ~0.45 GB / year   |
| CME GC Futures M1   | Databento   | ~4.5 GB (DBN.zst) | ~22.0 GB (CSV)     | ~5.5 GB (Pq)     | ~0.55 GB / year   |
| CME GC Futures Tick | Databento   | ~65.0 GB (DBN.zst)| ~380.0 GB (CSV)    | ~95.0 GB (Pq)    | ~10.0 GB / year   |
| Macro Daily Series  | FRED        | ~1.2 MB (CSV)     | ~1.2 MB (CSV)      | ~0.5 MB (Pq)     | < 0.1 MB / year   |
+---------------------+-------------+-------------------+--------------------+------------------+-------------------+
```

### Key Engineering Takeaway:
The total storage requirement for 10 years of historical M1/H1/Daily data across both Spot and Futures is **less than 15 GB** in optimized Parquet format. Even full 10-year tick bid/ask data is only **~28 GB**. Modern local workstation SSDs (500 GB – 2 TB) can host this dataset with ease, eliminating the necessity of mandatory cloud storage.

---

## 3. AWS Resource Architecture & Cost Estimation

If off-site cloud storage and distributed processing are commissioned in future phases, the following minimal architecture is recommended:

```
+---------------------------------------------------------------------------------+
|                         PROPOSED AWS DATA PIPELINE                              |
+---------------------------------------------------------------------------------+
|                                                                                 |
|   1. External Feeds (Dukascopy / Databento / FRED)                              |
|           │                                                                     |
|           ▼                                                                     |
|   2. AWS S3 Standard Ingestion Bucket (`s3://treading-ai-market-data-raw/`)     |
|           │                                                                     |
|           ▼                                                                     |
|   3. Batch Processing Worker (EC2 `c6i.xlarge` Spot Instance - 4 vCPU, 8GB RAM) |
|           │                                                                     |
|           ▼                                                                     |
|   4. Processed Features Bucket (`s3://treading-ai-processed-parquet/`)          |
|           │                                                                     |
|           ▼                                                                     |
|   5. Local Workstation Sync (`aws s3 sync`)                                     |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

### Component Cost Breakdown (AWS US-East-1 / US-East-2 Rates)

#### A. Amazon S3 Storage
- **S3 Standard Tier:** $0.023 per GB / month for the first 50 TB.
  - Storing 35 GB of processed Parquet data:
    $$\text{Monthly Cost} = 35 \text{ GB} \times \$0.023 = \mathbf{\$0.805 / \text{month}}$$
- **S3 Glacier Instant Retrieval Tier (for Raw Archives):** $0.004 per GB / month.
  - Storing 20 GB of raw `.bi5` archives:
    $$\text{Monthly Cost} = 20 \text{ GB} \times \$0.004 = \mathbf{\$0.080 / \text{month}}$$
- **Total S3 Storage Cost:** $\approx \mathbf{\$0.89 / \text{month}}$ ($~\$10.68 / \text{year}$).

#### B. Compute & Processing (EC2)
- To decompress, validate, and resample 10 years of tick data requires approximately **3 to 5 hours** of multi-threaded CPU execution.
- Recommended Instance: **`c6i.xlarge`** (Compute Optimized, 4 vCPUs, 8 GB RAM, Intel Xeon Scalable).
  - On-Demand Price: $0.1700 per hour.
  - Spot Instance Price (typical 65% discount): **~$0.0595 per hour**.
  - One-Off Ingestion Cost (5 hours on Spot):
    $$\text{Compute Cost} = 5 \times \$0.0595 = \mathbf{\$0.30 \text{ one-off}}$$

#### C. Data Transfer & Networking
- Ingress (upload to S3 from internet): **$0.00 (Free)**.
- Internal transfer (S3 to EC2 within same AWS region): **$0.00 (Free)**.
- Egress (download from S3 to local workstation):
  - First 100 GB per month is **$0.00 (Free AWS tier)**.
  - Syncing 35 GB of Parquet files to local SSD costs **$0.00**.

### Total Cloud Financial Projection:

```
+---------------------------------------------------------------------------------+
|                            MONTHLY CLOUD BUDGET ESTIMATE                        |
+-------------------------------------+--------------------+----------------------+
| Resource Component                  | Monthly Estimate   | Annual Projected     |
+-------------------------------------+--------------------+----------------------+
| S3 Storage (Processed Parquet)      | $0.81              | $9.72                |
| S3 Storage (Raw Archive Glacier)    | $0.08              | $0.96                |
| EC2 Spot Batch Ingestion (Quarterly)| $0.10              | $1.20                |
| Data Egress (< 100 GB/month)        | $0.00              | $0.00                |
| TOTAL AWS ESTIMATED COST            | **$0.99 / month**  | **$11.88 / year**    |
+-------------------------------------+--------------------+----------------------+
```

---

## 4. Rigorous Cloud Cost Controls & Guardrails

To prevent accidental runaway billing or forgotten compute instances, any future AWS deployment must enforce the following four mandatory controls:

### Guardrail 1: AWS Budgets & Alarm Thresholds
- Deploy an **AWS Budget** set to a hard ceiling of **$5.00 / month**.
- Configure automated email/SNS alerts when forecasted spend reaches **80% ($4.00)** and actual spend reaches **100% ($5.00)**.

### Guardrail 2: Ephemeral Spot Compute (Zero Running Instances)
- Long-running EC2 instances are **strictly prohibited**.
- All compute must run via ephemeral Spot Instances or Docker containers that execute the pipeline and immediately issue an OS shutdown (`sudo shutdown -h now`).
- Attach an AWS CloudWatch Alarm that terminates any EC2 instance where CPU utilization remains below $5\%$ for more than 15 consecutive minutes.

### Guardrail 3: S3 Lifecycle Rules
- Implement S3 lifecycle policies on raw ingestion buckets:
  - Transition raw archives from S3 Standard to S3 Glacier Instant Retrieval after 14 days.
  - Automatically expire and delete temporary extraction scratch directories after 7 days.

### Guardrail 4: Local Workstation Priority (Default Choice)
- Cloud compute is **optional**. Because the local workstation has 8+ CPU cores, 16+ GB RAM, and fast NVMe storage, all batch parsing, tick aggregation, and Parquet serialization can be executed locally for **$0.00**.

---

## 5. Formal Cloud Audit Directive

> [!IMPORTANT]
> **Definitive Directive on Cloud Spend:**  
> 1. No AWS account or cloud resources shall be created during Phase 29.  
> 2. For Phase 30, **local processing and storage is the primary recommendation**. AWS S3/EC2 should only be introduced if dataset sizes exceed local disk capacity or offsite redundancy is formally mandated.  
> 3. Total cloud spend shall not exceed **$5.00 / month** under any circumstances.
