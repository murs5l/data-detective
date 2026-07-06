import pandas as pd


def load_csv(file_path: str) -> pd.DataFrame:
    """
    Centralized data loader (future: support parquet, json, sql).
    """
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {file_path}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to load data: {e}") from e