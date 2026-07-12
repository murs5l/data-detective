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


def load_csv(file_path: str, optimize_memory: bool = True) -> pd.DataFrame:
    """
    Centralized data loader (future: support parquet, json, sql).
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError as e:
        raise DataLoadError(f"File not found: {file_path}") from e
    except pd.errors.EmptyDataError as e:
        raise EmptyDataError(f"File is empty: {file_path}") from e
    except Exception as e:
        raise DataLoadError(f"Failed to load data: {e}") from e

    if df.empty:
        raise EmptyDataError(f"File is empty: {file_path}")

    if optimize_memory:
        df = _downcast_numeric_dtypes(df)

    return df
