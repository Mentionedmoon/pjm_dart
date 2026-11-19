"""
clean_merge.py  -  Jeff (Data & Model Lead)

WHAT THIS SCRIPT DOES
---------------------
Takes the raw PJM files we downloaded and builds ONE clean table:
one row per hour, with the day-ahead price, the real-time price, the spread,
and total PJM load for that hour.

    raw CSVs  --->  [load]  --->  [filter to Western Hub]  --->  [fix timestamps]
              --->  [merge DA + RT + load on the same hour]  --->  [quality checks]
              --->  data/processed/hourly.parquet

Everyone else (Brendan's features, Daniel's backtest) builds on this table,
so if this is wrong, everything downstream is wrong. That's why it prints
a quality report at the end.

HOW TO RUN (from the repo root):
    python src/clean_merge.py
"""

from pathlib import Path
import glob
import pandas as pd

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
# Where the raw CSVs live. Right now they sit in the repo root.
# The glob patterns ("*") mean that if we later add day_ahead_2023.csv,
# day_ahead_2024.csv etc., the script picks them all up automatically.
RAW_DIR = Path(".")
DA_PATTERN = "day_ahead*.csv"
RT_PATTERN = "real_time*.csv"
LOAD_PATTERN = "hrl_load_metered*.csv"

OUT_DIR = Path("data/processed")

# PJM identifies every pricing location by a number (pnode_id).
# 51288 = WESTERN HUB (confirmed: it's in our files with that name).
HUB_ID = 51288

# PJM writes timestamps like "1/1/2025 5:00:00 AM".
# Telling pandas the exact format makes parsing fast and avoids silent guessing.
TIME_FMT = "%m/%d/%Y %I:%M:%S %p"


# ---------------------------------------------------------------------------
# STEP 1: read all files matching a pattern into one DataFrame
# ---------------------------------------------------------------------------
def read_all(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(str(RAW_DIR / pattern)))
    if not files:
        raise FileNotFoundError(f"No files match {pattern} in {RAW_DIR.resolve()}")
    print(f"  reading {len(files)} file(s) for {pattern}: {[Path(f).name for f in files]}")
    return pd.concat((pd.read_csv(f) for f in files), ignore_index=True)


# ---------------------------------------------------------------------------
# STEP 2: prices (used for both DA and RT - same file layout)
# ---------------------------------------------------------------------------
def load_prices(pattern: str, market: str) -> pd.DataFrame:
    """
    market is "da" or "rt". PJM names its columns e.g. total_lmp_da / total_lmp_rt,
    so we use the suffix to find the right ones.
    """
    df = read_all(pattern)

    # Keep only Western Hub (the files contain 12 hubs).
    df = df[df["pnode_id"] == HUB_ID]

    # PJM sometimes republishes corrected prices. row_is_current = True marks
    # the latest version of each row; older versions must be dropped.
    if "row_is_current" in df.columns:
        df = df[df["row_is_current"] == True]  # noqa: E712

    # Parse timestamps. We keep BOTH:
    #   UTC  -> used for joining (never skips or repeats an hour)
    #   EPT  -> Eastern time, used for humans and calendar features
    df = df.assign(
        datetime_utc=pd.to_datetime(df["datetime_beginning_utc"], format=TIME_FMT),
        datetime_ept=pd.to_datetime(df["datetime_beginning_ept"], format=TIME_FMT),
    )

    # Rename PJM's long column names to short, consistent ones.
    df = df.rename(columns={
        f"total_lmp_{market}": f"{market}_lmp",                 # the price we trade
        f"system_energy_price_{market}": f"{market}_energy",    # LMP part 1
        f"congestion_price_{market}": f"{market}_congestion",   # LMP part 2
        f"marginal_loss_price_{market}": f"{market}_loss",      # LMP part 3
    })
    cols = ["datetime_utc", "datetime_ept",
            f"{market}_lmp", f"{market}_energy", f"{market}_congestion", f"{market}_loss"]

    # If the same hour appears twice (e.g. overlapping downloads), keep one.
    df = df[cols].drop_duplicates(subset="datetime_utc", keep="last")
    return df.sort_values("datetime_utc")


# ---------------------------------------------------------------------------
# STEP 3: load (electricity demand)
# ---------------------------------------------------------------------------
def load_rto_load() -> pd.DataFrame:
    """
    The load file has one row per zone per hour, PLUS a row with zone == "RTO"
    that is already the total for all of PJM.

    TRAP: if you sum every row you DOUBLE-COUNT (zones + their total).
    We checked: summing everything gives ~189 GW average, but PJM's real
    average load is ~95 GW. The RTO row alone gives ~95 GW and equals the
    sum of the zones exactly. So we keep only the RTO row.
    """
    df = read_all(LOAD_PATTERN)
    df = df[df["zone"] == "RTO"]
    df = df.assign(datetime_utc=pd.to_datetime(df["datetime_beginning_utc"], format=TIME_FMT))
    df = df.rename(columns={"mw": "load_mw", "is_verified": "load_is_verified"})
    df = df[["datetime_utc", "load_mw", "load_is_verified"]]
    return df.drop_duplicates(subset="datetime_utc", keep="last").sort_values("datetime_utc")


# ---------------------------------------------------------------------------
# STEP 4: merge everything on the UTC hour
# ---------------------------------------------------------------------------
def build_hourly() -> pd.DataFrame:
    print("Loading day-ahead prices...")
    da = load_prices(DA_PATTERN, "da")
    print("Loading real-time prices...")
    rt = load_prices(RT_PATTERN, "rt").drop(columns="datetime_ept")
    print("Loading load...")
    load = load_rto_load()

    # "inner" join = keep only hours that have BOTH a DA and an RT price.
    # An hour without both can't be traded or scored, so it's useless to us.
    hourly = da.merge(rt, on="datetime_utc", how="inner")

    # "left" join = keep every price hour, attach load where we have it.
    # Missing load shows up as NaN, which the quality report will flag.
    hourly = hourly.merge(load, on="datetime_utc", how="left")

    # THE TARGET. Positive spread = DA above RT = an INC would have made money.
    hourly["spread"] = hourly["da_lmp"] - hourly["rt_lmp"]

    # Handy columns for grouping later (Eastern time, since PJM's day is EPT).
    hourly["date_ept"] = hourly["datetime_ept"].dt.date
    hourly["hour_ept"] = hourly["datetime_ept"].dt.hour   # 0 = midnight-1am, 17 = 5-6pm

    return hourly.sort_values("datetime_utc").reset_index(drop=True)


# ---------------------------------------------------------------------------
# STEP 5: quality report - never trust data you haven't checked
# ---------------------------------------------------------------------------
def quality_report(h: pd.DataFrame) -> None:
    print("\n" + "=" * 60 + "\nDATA QUALITY REPORT\n" + "=" * 60)
    print(f"Rows: {len(h):,}")
    print(f"From {h.datetime_ept.min()} to {h.datetime_ept.max()} (EPT)")

    # Every hour in UTC should exist exactly once. Compare against a full calendar.
    expected = pd.date_range(h.datetime_utc.min(), h.datetime_utc.max(), freq="h")
    missing = expected.difference(h.datetime_utc)
    print(f"Missing hours inside that range: {len(missing)}")
    if len(missing):
        print("  first few:", list(missing[:5]))

    print(f"Duplicate hours: {h.datetime_utc.duplicated().sum()}")

    # Daylight saving time check (EPT only - UTC is unaffected):
    # spring forward = a 23-hour day, fall back = a 25-hour day. Both are normal.
    per_day = h.groupby("date_ept").size()
    odd = per_day[per_day != 24]
    print(f"Days without exactly 24 hours: {len(odd)}")
    for d, n in odd.items():
        note = "spring DST (normal)" if n == 23 else "fall DST (normal)" if n == 25 else "CHECK THIS"
        print(f"  {d}: {n} hours  <- {note}")

    print("\nMissing values per column:")
    nulls = h.isna().sum()
    print(nulls[nulls > 0].to_string() if nulls.any() else "  none")

    print("\nSpread (DA - RT) summary, $/MWh:")
    print(h["spread"].describe().round(2).to_string())
    print(f"Share of hours where DA > RT (INC would win): {(h.spread > 0).mean():.1%}")
    print(f"Average spread: ${h.spread.mean():.2f}  (positive = DA premium, like Longstaff & Wang)")

    print("\n5 biggest spreads each way:")
    cols = ["datetime_ept", "da_lmp", "rt_lmp", "spread", "load_mw"]
    print(h.nlargest(5, "spread")[cols].to_string(index=False))
    print(h.nsmallest(5, "spread")[cols].to_string(index=False))


if __name__ == "__main__":
    hourly = build_hourly()
    quality_report(hourly)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "hourly.parquet"
    hourly.to_parquet(out, index=False)
    print(f"\nSaved {len(hourly):,} rows to {out}")
