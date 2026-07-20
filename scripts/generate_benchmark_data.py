"""Generates a synthetic CSV for reproducing the README's benchmark numbers.

Fixed seed, so the same row count always produces byte-identical data:
mixed types (int/float/string/date/bool), ~4% missing values in one column,
a small tail of injected outliers, and a handful of duplicate rows, matching
the kind of messy real-world data the profiler is designed for.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd


def generate(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    df = pd.DataFrame(
        {
            "id": np.arange(n),
            "age": rng.integers(18, 90, n).astype(float),
            "income": rng.normal(55000, 20000, n).round(2),
            "score": rng.exponential(50, n).round(2),
            "signup_date": pd.date_range("2020-01-01", periods=n, freq="min").astype(str),
            "category": rng.choice(["A", "B", "C", "D"], n),
            "region": rng.choice(["north", "south", "east", "west"], n, p=[0.7, 0.1, 0.1, 0.1]),
            "notes": rng.choice(["", "flagged", "reviewed"], n, p=[0.85, 0.1, 0.05]),
            "email": [f"user{i}@example.com" for i in range(n)],
            "active": rng.choice([True, False], n),
        }
    )

    missing_mask = rng.random(n) < 0.04
    df.loc[missing_mask, "income"] = np.nan

    outlier_idx = rng.choice(n, size=max(1, n // 500), replace=False)
    df.loc[outlier_idx, "income"] = df["income"].max() * rng.uniform(5, 10, len(outlier_idx))

    half = max(1, n // 400)
    dup_idx = rng.choice(n, size=half * 2, replace=False)
    df.iloc[dup_idx[:half]] = df.iloc[dup_idx[half : half * 2]].values

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=int, help="Number of rows to generate")
    parser.add_argument("output", help="Output CSV path")
    args = parser.parse_args()

    df = generate(args.rows)
    df.to_csv(args.output, index=False)
    print(f"Wrote {args.output}: {len(df)} rows, {len(df.columns)} columns")


if __name__ == "__main__":
    main()
