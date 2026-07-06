import pandas as pd


def load_csv(file_path: str) -> pd.DataFrame:
    """
    Centralized data loader (future: support parquet, json, sql).
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        raise Exception(f"Failed to load data: {str(e)}")