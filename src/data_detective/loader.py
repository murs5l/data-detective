from __future__ import annotations

import pandas as pd

from data_detective.exceptions import DataLoadError, EmptyDataError


def _downcast_numeric_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downcasts int64/float64 columns to the smallest safe dtype.
    Meaningfully reduces memory (and speeds up profiling) on large files.
    """
    for col in df.select_dtypes(include=["int64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="integer")

    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="float")

    return df


# Tried in order. "utf-8-sig" covers both plain UTF-8 and UTF-8-with-BOM
# (common from Excel's "CSV UTF-8" export, which otherwise leaves a stray
# ﻿ prefixed onto the first column name). "latin-1" never raises
# UnicodeDecodeError (every byte value is a valid codepoint), so it's the
# catch-all for legacy/Windows-exported files with accented characters.
_ENCODINGS_TO_TRY = ("utf-8-sig", "latin-1")


def load_csv(file_path: str, optimize_memory: bool = True) -> pd.DataFrame:
    """
    Centralized data loader (future: support parquet, json, sql).
    """
    df: pd.DataFrame | None = None
    for encoding in _ENCODINGS_TO_TRY:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except FileNotFoundError as e:
            raise DataLoadError(f"File not found: {file_path}") from e
        except pd.errors.EmptyDataError as e:
            raise EmptyDataError(f"File is empty: {file_path}") from e
        except Exception as e:
            raise DataLoadError(f"Failed to load data: {e}") from e

    if df is None:
        # Unreachable today: "latin-1" never raises UnicodeDecodeError, so
        # the loop always breaks or raises first. Guards against a future
        # edit to _ENCODINGS_TO_TRY silently dropping that guarantee.
        raise DataLoadError(f"Failed to decode file with any of {_ENCODINGS_TO_TRY}: {file_path}")

    if df.empty:
        raise EmptyDataError(f"File is empty: {file_path}")

    if optimize_memory:
        df = _downcast_numeric_dtypes(df)

    return df
