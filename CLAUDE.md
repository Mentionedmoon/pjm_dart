# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

Early-stage data analysis project on PJM electricity market data. "DART" refers to the day-ahead minus real-time (DA − RT) LMP spread. The **target study window is 2022-11-19 → 2026-11-19**. The CSVs currently on disk cover only CY2025.

- `data_sources.ipynb` exists but is an empty (0-byte) file, so it is not valid notebook JSON until it is written.
- **Environment:** use `.venv` (Python 3.13 + pandas). Run scripts with `.venv/Scripts/python`. Dependencies are listed in `requirements.txt`.
- `scripts/profile_data.py` profiles the CSVs. Re-run it after any data refresh and update `DATA.md` with the output.

## Data

**See `DATA.md`** for file schemas, coverage, hub IDs, load areas, known issues, and join recipes. It is the single source of truth for data facts. Update it rather than duplicating details here.

The most important gotchas:
- Join on `datetime_beginning_utc`, never EPT, because of DST.
- Join DA to RT on (`datetime_beginning_utc`, `pnode_id`).
- Exclude the `RTO` aggregate row in the load file before summing.
