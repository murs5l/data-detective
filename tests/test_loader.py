from pathlib import Path

import pandas as pd
import pytest

from data_detective.exceptions import DataLoadError, EmptyDataError
from data_detective.loader import _downcast_numeric_dtypes, load_csv


def test_load_csv_success(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

    df = load_csv(str(csv_path))

    assert list(df.columns) == ["a", "b"]
    assert len(df) == 2


def test_load_csv_file_not_found():
    with pytest.raises(DataLoadError, match="File not found"):
        load_csv("/does/not/exist.csv")


def test_load_csv_empty_file(tmp_path: Path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    with pytest.raises(EmptyDataError, match="File is empty"):
        load_csv(str(csv_path))


def test_load_csv_headers_only_is_empty_dataset(tmp_path: Path):
    csv_path = tmp_path / "headers_only.csv"
    csv_path.write_text("a,b\n", encoding="utf-8")

    with pytest.raises(EmptyDataError, match="File is empty"):
        load_csv(str(csv_path))


def test_downcast_numeric_dtypes():
    df = pd.DataFrame({
        "i": pd.Series([1, 2, 3], dtype="int64"),
        "f": pd.Series([1.0, 2.5, 3.25], dtype="float64"),
    })

    out = _downcast_numeric_dtypes(df.copy())

    assert out["i"].dtype != df["i"].dtype
    assert out["f"].dtype != df["f"].dtype
