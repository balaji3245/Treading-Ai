"""Storage engine for financial datasets using Apache Parquet and PyArrow.

Ensures strict schema validation, metadata preservation, and memory-conscious
chunked processing suitable for resource-constrained systems.
"""

import logging
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from treading_ai.config import (
    CHUNK_SIZE_ROWS,
    DEFAULT_PARQUET_COMPRESSION,
    PROCESSED_DATA_DIR,
    QUARANTINED_PERIODS,
)

logger = logging.getLogger(__name__)

# Canonical PyArrow Schema for Processed Financial Candlesticks
CANDLESTICK_ARROW_SCHEMA = pa.schema([
    ("timestamp", pa.timestamp("us", tz="UTC")),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("volume", pa.float64()),
    ("bar_count", pa.int32()),
    ("is_complete", pa.bool_()),
])


class ParquetStorageEngine:
    """Manages reading and writing of processed financial data in Parquet format."""

    def __init__(
        self,
        base_dir: Path = PROCESSED_DATA_DIR,
        compression: str = DEFAULT_PARQUET_COMPRESSION,
    ):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.compression = compression

    def get_partition_path(
        self,
        symbol: str,
        timeframe: str,
        identifier: str,
    ) -> Path:
        """Construct directory path and filename for a specific dataset partition."""
        target_dir = self.base_dir / symbol.upper() / timeframe.upper()
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{symbol.upper()}_{timeframe.upper()}_{identifier}.parquet"
        return target_dir / filename

    def write_candlesticks(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        identifier: str,
        custom_metadata: Optional[Dict[str, str]] = None,
    ) -> Path:
        """Write an OHLC DataFrame to a Parquet file with schema validation and metadata.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame containing candlestick data.
        symbol : str
            Symbol identifier (e.g., 'XAUUSD').
        timeframe : str
            Timeframe identifier (e.g., 'M1', 'H1').
        identifier : str
            Batch or period identifier (e.g., '2024' or '2026_01').
        custom_metadata : Optional[Dict[str, str]]
            Arbitrary key-value metadata to embed inside the Parquet footer.

        Returns
        -------
        Path
            Path to the written Parquet file.
        """
        output_path = self.get_partition_path(symbol, timeframe, identifier)

        # Prepare table
        # Ensure timestamp is UTC timestamp
        df_clean = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_clean["timestamp"]):
            df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"], utc=True)
        elif df_clean["timestamp"].dt.tz is None:
            df_clean["timestamp"] = df_clean["timestamp"].dt.tz_localize("UTC")
        else:
            df_clean["timestamp"] = df_clean["timestamp"].dt.tz_convert("UTC")

        # Cast to arrow table matching schema
        table = pa.Table.from_pandas(df_clean, schema=CANDLESTICK_ARROW_SCHEMA, preserve_index=False)

        # Append custom metadata to schema metadata if provided
        if custom_metadata:
            existing_meta = table.schema.metadata or {}
            encoded_custom = {k.encode("utf-8"): str(v).encode("utf-8") for k, v in custom_metadata.items()}
            new_meta = {**existing_meta, **encoded_custom}
            table = table.replace_schema_metadata(new_meta)

        pq.write_table(
            table,
            output_path,
            compression=self.compression,
            use_dictionary=True,
            write_statistics=True,
        )
        logger.info(
            "Wrote %d rows to Parquet: %s (size: %.2f KB)",
            len(df),
            output_path,
            output_path.stat().st_size / 1024.0,
        )
        return output_path

    def read_candlesticks(
        self,
        file_path: Union[str, Path],
        columns: Optional[List[str]] = None,
        filter_incomplete: bool = False,
    ) -> pd.DataFrame:
        """Read a Parquet file into a Pandas DataFrame.

        Parameters
        ----------
        file_path : Union[str, Path]
            Path to the Parquet file.
        columns : Optional[List[str]]
            Columns to read for memory projection.
        filter_incomplete : bool
            If True, filters out bars where is_complete == False to prevent partial
            boundary candles from leaking into training or signal engines.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")

        table = pq.read_table(file_path, columns=columns)
        df = table.to_pandas()
        if filter_incomplete and "is_complete" in df.columns:
            df = df[df["is_complete"]].reset_index(drop=True)
        return df

    def iter_candlestick_chunks(
        self,
        file_path: Union[str, Path],
        batch_size: int = CHUNK_SIZE_ROWS,
        columns: Optional[List[str]] = None,
        filter_incomplete: bool = False,
    ) -> Iterator[pd.DataFrame]:
        """Iterate through large Parquet files in streaming batches to limit RAM consumption."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")

        parquet_file = pq.ParquetFile(file_path)
        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=columns):
            df = batch.to_pandas()
            if filter_incomplete and "is_complete" in df.columns:
                df = df[df["is_complete"]].reset_index(drop=True)
            yield df

    def list_available_partitions(
        self,
        symbol: str,
        timeframe: str,
        excluded_identifiers: Optional[List[str]] = None,
    ) -> List[str]:
        """Return sorted list of verified partition identifiers for symbol and timeframe."""
        target_dir = self.base_dir / symbol.upper() / timeframe.upper()
        if not target_dir.exists():
            return []

        excluded = set(excluded_identifiers if excluded_identifiers is not None else QUARANTINED_PERIODS)
        files = sorted(list(target_dir.glob(f"{symbol.upper()}_{timeframe.upper()}_*.parquet")))
        
        identifiers = []
        prefix = f"{symbol.upper()}_{timeframe.upper()}_"
        for f in files:
            ident = f.stem[len(prefix):]
            if ident not in excluded:
                identifiers.append(ident)
        return identifiers

    def load_continuous_dataset(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[Union[str, pd.Timestamp]] = None,
        end_time: Optional[Union[str, pd.Timestamp]] = None,
        filter_incomplete: bool = True,
        excluded_identifiers: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Load and concatenate verified partitions into a continuous chronological DataFrame.

        Strict Safeguards:
        - Automatically excludes QUARANTINED_PERIODS (e.g. 2026_06 to 2026_10) to prevent
          accidental entry into feature engineering or training.
        - Defaults filter_incomplete=True to ensure incomplete boundary bars cannot silently
          become features, training labels, or trading signals.
        - Asserts chronological monotonicity and eliminates boundary duplicate timestamps.
        """
        partitions = self.list_available_partitions(
            symbol=symbol,
            timeframe=timeframe,
            excluded_identifiers=excluded_identifiers,
        )
        if not partitions:
            raise FileNotFoundError(f"No valid partitions found for {symbol} {timeframe} in {self.base_dir}")

        frames = []
        for ident in partitions:
            fpath = self.get_partition_path(symbol, timeframe, ident)
            df_part = self.read_candlesticks(fpath, filter_incomplete=filter_incomplete)
            frames.append(df_part)

        combined_df = pd.concat(frames, ignore_index=True)
        # Deduplicate and sort chronologically
        combined_df = combined_df.drop_duplicates(subset=["timestamp"], keep="first").sort_values("timestamp").reset_index(drop=True)

        if start_time is not None:
            t_start = pd.to_datetime(start_time, utc=True)
            combined_df = combined_df[combined_df["timestamp"] >= t_start]

        if end_time is not None:
            t_end = pd.to_datetime(end_time, utc=True)
            combined_df = combined_df[combined_df["timestamp"] <= t_end]

        return combined_df.reset_index(drop=True)
