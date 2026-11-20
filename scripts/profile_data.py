"""Profile the PJM CSV extracts and print facts for DATA.md.

Usage:  .venv/Scripts/python scripts/profile_data.py
Re-run after every data refresh and update DATA.md with the output.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TS_FMT = "%m/%d/%Y %I:%M:%S %p"
FILES = {
    "day_ahead.csv": ["datetime_beginning_utc", "pnode_id"],
    "real_time.csv": ["datetime_beginning_utc", "pnode_id"],
    "hrl_load_metered.csv": ["datetime_beginning_utc", "load_area"],
}


def profile(name: str, key: list[str]) -> pd.DataFrame:
    df = pd.read_csv(ROOT / name)
    for col in ("datetime_beginning_utc", "datetime_beginning_ept"):
        df[col] = pd.to_datetime(df[col], format=TS_FMT)

    print(f"\n## {name}")
    print(f"rows: {len(df):,}   columns: {df.shape[1]}")
    for col in ("datetime_beginning_utc", "datetime_beginning_ept"):
        print(f"{col}: {df[col].min()} -> {df[col].max()}")
    n_hours = df["datetime_beginning_utc"].nunique()
    print(f"distinct UTC hours: {n_hours:,}")
    dupes = df.duplicated(key).sum()
    print(f"duplicate rows on key {key}: {dupes}")

    print("\n| column | dtype | nulls | distinct | example |")
    print("|---|---|---|---|---|")
    for col in df.columns:
        s = df[col]
        ex = s.dropna().iloc[0] if s.notna().any() else ""
        print(f"| `{col}` | {s.dtype} | {s.isna().sum():,} | {s.nunique():,} | {ex} |")

    num = df.select_dtypes("number").drop(columns=["pnode_id", "version_nbr"], errors="ignore")
    if not num.empty:
        print("\nnumeric summary:")
        print(num.describe().T[["min", "50%", "mean", "max"]].round(2).to_markdown())
    return df


def main() -> None:
    dfs = {name: profile(name, key) for name, key in FILES.items()}

    da = dfs["day_ahead.csv"]
    print("\n## Hubs (pnode_id -> pnode_name)")
    hubs = da[["pnode_id", "pnode_name"]].drop_duplicates().sort_values("pnode_name")
    print(hubs.to_markdown(index=False))

    load = dfs["hrl_load_metered.csv"]
    print("\n## Load areas")
    areas = (
        load.groupby(["nerc_region", "mkt_region", "zone", "load_area"])
        .size().rename("rows").reset_index()
    )
    print(areas.to_markdown(index=False))
    print("\nis_verified counts:")
    print(load["is_verified"].value_counts().to_string())

    rt = dfs["real_time.csv"]
    m = da.merge(rt, on=["datetime_beginning_utc", "pnode_id"], how="outer", indicator=True)
    print("\n## DA/RT join check")
    print(m["_merge"].value_counts().to_string())


if __name__ == "__main__":
    main()
