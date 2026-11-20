# Data Dictionary

These are PJM Data Miner 2 exports for analyzing the **DART spread** (day-ahead LMP minus real-time LMP) at PJM trading hubs.

Regenerate the facts in this file with `.venv/Scripts/python scripts/profile_data.py` after every data refresh.

## Study window

| | |
|---|---|
| **Target window** | **2022-11-19 → 2026-11-19** (four years) |
| **On disk today** | 2025-01-01 → 2025-12-31 (CY2025 only) |
| **Gap to fill** | 2022-11-19 → 2024-12-31 and 2026-01-01 → 2026-11-19 |

Notes for the full pull:
- Pull and filter by `datetime_beginning_utc`. The window boundaries are defined in EPT (00:00 EPT = 05:00 UTC in November).
- The end date is the date of the most recent pull (2026-11-19). The newest days of RT and metered load will be preliminary or incomplete, so expect revisions (see `is_verified`, `version_nbr`).
- At four years, each price file will be about 420k rows (about 50 MB) and the load file about 1.05M rows (about 80 MB). These sizes are still fine to load whole with pandas.

## Files

| File | Data Miner 2 feed (likely) | Grain | Key | Rows (CY2025) |
|---|---|---|---|---|
| `day_ahead.csv` | `da_hrl_lmps` | hub × hour | (`datetime_beginning_utc`, `pnode_id`) | 104,844 |
| `real_time.csv` | `rt_hrl_lmps` | hub × hour | (`datetime_beginning_utc`, `pnode_id`) | 104,844 |
| `hrl_load_metered.csv` | `hrl_load_metered` | load area × hour | (`datetime_beginning_utc`, `load_area`) | 262,800 |

The key has no duplicates in any of the three files.

## Coverage (CY2025 extracts)

| File | First hour (EPT) | Last hour (EPT) | Distinct UTC hours |
|---|---|---|---|
| `day_ahead.csv` | 2025-01-01 00:00 | 2025-12-31 00:00 | 8,737 |
| `real_time.csv` | 2025-01-01 00:00 | 2025-12-31 00:00 | 8,737 |
| `hrl_load_metered.csv` | 2025-01-01 00:00 | 2025-12-31 23:00 | 8,760 |

**The price files are missing the last 23 hours of 2025** (12/31 01:00–23:00 EPT).

## Schemas

### `day_ahead.csv` / `real_time.csv`

The two files have identical layouts. Price columns end in `_da` or `_rt`. All prices are in **$/MWh**.

| Column | Type | Description | Example |
|---|---|---|---|
| `datetime_beginning_utc` | timestamp | Hour start in UTC. **Use this for joins.** | `1/1/2025 5:00:00 AM` |
| `datetime_beginning_ept` | timestamp | Hour start in Eastern Prevailing Time (DST-aware) | `1/1/2025 12:00:00 AM` |
| `pnode_id` | int | PJM pricing node ID | `51217` |
| `pnode_name` | str | Hub name | `EASTERN HUB` |
| `voltage`, `equipment`, `zone` | — | **Always empty** for hubs. Drop them. | |
| `type` | str | Always `HUB` | `HUB` |
| `system_energy_price_*` | float | System energy price, the same at every node in a given hour | `21.26` |
| `total_lmp_*` | float | Total LMP = energy + congestion + loss | `21.99` |
| `congestion_price_*` | float | Congestion component | `0.15` |
| `marginal_loss_price_*` | float | Marginal loss component | `0.58` |
| `row_is_current` | bool | Latest version of the row (all `True` today) | `True` |
| `version_nbr` | int | Revision number (all `1` today) | `1` |

**CY2025 price ranges ($/MWh):**

| | DA min | DA median | DA mean | DA max | RT min | RT median | RT mean | RT max |
|---|---|---|---|---|---|---|---|---|
| `total_lmp` | -52.92 | 36.48 | 43.71 | 578.37 | -83.43 | 33.79 | 42.91 | 1,989.05 |
| `congestion_price` | -170.60 | 0.09 | -2.49 | 193.86 | -405.90 | 0.11 | -3.01 | 673.19 |
| `marginal_loss_price` | -32.06 | -0.48 | -0.82 | 35.25 | -203.46 | -0.48 | -0.87 | 149.60 |

RT has much fatter tails than DA, so expect heavy-tailed DART values.

### `hrl_load_metered.csv`

| Column | Type | Description | Example |
|---|---|---|---|
| `datetime_beginning_utc` | timestamp | Hour start in UTC | `1/1/2025 5:00:00 AM` |
| `datetime_beginning_ept` | timestamp | Hour start in EPT | `1/1/2025 12:00:00 AM` |
| `nerc_region` | str | `RFC`, `SERC`, or `RTO` | `RFC` |
| `mkt_region` | str | `MIDATL`, `WEST`, `SOUTH`, or `RTO` | `MIDATL` |
| `zone` | str | Transmission zone (21 zones + `RTO`) | `AE` |
| `load_area` | str | Load area (29 areas + `RTO`) | `AECO` |
| `mw` | float | Hourly metered load, MW | `870.261` |
| `is_verified` | bool | `False` = preliminary, may be revised | `False` |

## Hubs

| `pnode_id` | `pnode_name` |
|---|---|
| 34497125 | AEP GEN HUB |
| 34497127 | AEP-DAYTON HUB |
| 116013751 | ATSI GEN HUB |
| 33092311 | CHICAGO GEN HUB |
| 33092313 | CHICAGO HUB |
| 35010337 | DOMINION HUB |
| 51217 | EASTERN HUB |
| 33092315 | N ILLINOIS HUB |
| 4669664 | NEW JERSEY HUB |
| 34497151 | OHIO HUB |
| 51287 | WEST INT HUB |
| 51288 | WESTERN HUB |

## Load zones → load areas

| NERC / mkt region | Zone → load areas |
|---|---|
| RFC / MIDATL | AE → AECO, VMEU · BC → BC · DPL → DPLCO, EASTON · JC → JC · ME → ME · PE → PE · PEP → PEPCO, SMECO · PL → PLCO, UGI · PN → PN · PS → PS · RECO → RECO |
| RFC / WEST | AEP → AEPAPT, AEPIMP, AEPKPT, AEPOPT · AP → AP · ATSI → OE, PAPWR · CE → CE · DAY → DAY · DEOK → DEOK · DUQ → DUQ · OVEC → OVEC |
| SERC / SOUTH | DOM → DOM |
| SERC / WEST | EKPC → EKPC |
| RTO / RTO | RTO → RTO (aggregate) |

## Known issues and gotchas

1. **Timestamps** use the `M/D/YYYY h:mm:ss AM/PM` format. Parse them with `format="%m/%d/%Y %I:%M:%S %p"`.
2. **Join on UTC, not EPT.** EPT repeats 01:00 at the November fall-back and skips 02:00 at the March spring-forward. In CY2025 there are 8,737 distinct UTC hours but only 8,736 distinct EPT hours in the price files.
3. **The `RTO` row in the load file is an aggregate.** It equals the sum of the 29 load areas exactly. Exclude it before you sum anything, or the total is doubled.
4. **`is_verified=False`** applies to 13 of 30 load areas across the *entire* year, not only recent hours. Treat those values as preliminary.
5. **Zero-MW rows:** there is one hour each in AECO, DPLCO, and PEPCO with `mw == 0`. These are probably bad meter data. Treat them as missing.
6. **Price/load coverage mismatch:** joining prices to load leaves the last 23 load hours of 2025 unmatched.
7. **DA ↔ RT join is clean:** all 104,844 rows match on (`datetime_beginning_utc`, `pnode_id`), with no orphans on either side.

## Recipes

```python
import pandas as pd

FMT = "%m/%d/%Y %I:%M:%S %p"
KEY = ["datetime_beginning_utc", "pnode_id"]
DROP = ["voltage", "equipment", "zone", "type", "row_is_current", "version_nbr"]

def load_prices(path):
    df = pd.read_csv(path).drop(columns=DROP)
    for c in ("datetime_beginning_utc", "datetime_beginning_ept"):
        df[c] = pd.to_datetime(df[c], format=FMT)
    return df

da = load_prices("day_ahead.csv")
rt = load_prices("real_time.csv").drop(columns=["datetime_beginning_ept", "pnode_name"])
px = da.merge(rt, on=KEY, how="inner", validate="one_to_one")
px["dart"] = px["total_lmp_da"] - px["total_lmp_rt"]   # $/MWh; positive = DA above RT

load = pd.read_csv("hrl_load_metered.csv")
load = load[load["load_area"] != "RTO"]                  # avoid double-counting
load["datetime_beginning_utc"] = pd.to_datetime(load["datetime_beginning_utc"], format=FMT)
rto_load = load.groupby("datetime_beginning_utc")["mw"].sum().rename("rto_mw")
```

## Changelog

| Date | Change |
|---|---|
| 2026-11-12 | Initial CY2025 extracts pulled (DA LMP, RT LMP, metered load) |
| 2026-11-19 | DATA.md created. Target window set to 2022-11-19 → 2026-11-19 |
