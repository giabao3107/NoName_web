"""Data access and customer filtering for the BI10 dashboard."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

DATA_PATH = Path(__file__).parent / "data" / "ci360.json"
TIERS = {0: "High", 1: "Medium", 2: "Low"}


@lru_cache(maxsize=1)
def load_dashboard_data() -> dict[str, Any]:
    """Load the checked-in aggregate snapshot and 10,521-row explorer sample."""
    with DATA_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def _decode_lookup(values: pd.Series, labels: list[str] | dict[str, str]) -> pd.Series:
    if isinstance(labels, dict):
        return values.map(labels)
    return values.map(lambda index: labels[int(index)] if pd.notna(index) and 0 <= int(index) < len(labels) else None)


def customer_frame(data: dict[str, Any]) -> pd.DataFrame:
    """Decode the compact positional customer representation into named columns."""
    customers = data["customers"]
    frame = pd.DataFrame.from_records(customers["rows"], columns=customers["cols"])
    if "fh" in frame:
        frame["fh_tier"] = frame["fh"].map(TIERS)
    if "et" in frame:
        frame["eng_tier"] = frame["et"].map(TIERS)
    for column, lookup_key, output_column in (
        ("seg", "personas", "persona"),
        ("nba", "actions", "action"),
        ("ch", "channels", "channel"),
        ("cap", "caps", "offer_cap_label"),
    ):
        if column in frame and lookup_key in customers:
            frame[output_column] = _decode_lookup(frame[column], customers[lookup_key])
    return frame


def filter_customers(
    frame: pd.DataFrame,
    *,
    search: str = "",
    fh_tiers: list[str] | None = None,
    engagement_tiers: list[str] | None = None,
    priorities: list[int] | None = None,
) -> pd.DataFrame:
    """Filter explorer rows; empty or absent selections mean no restriction."""
    result = frame
    if search.strip():
        result = result[result["id"].astype(str).str.contains(search.strip(), regex=False)]
    if fh_tiers:
        result = result[result["fh_tier"].isin(fh_tiers)]
    if engagement_tiers:
        result = result[result["eng_tier"].isin(engagement_tiers)]
    if priorities:
        result = result[result["prio"].isin(priorities)]
    return result
