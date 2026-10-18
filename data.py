"""Data access and customer filtering for the BI10 dashboard."""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

DATA_PATH = Path(__file__).parent / "data" / "ci360.json"
TIERS = {0: "High", 1: "Medium", 2: "Low"}


@lru_cache(maxsize=1)
def load_dashboard_data() -> dict[str, Any]:
    """Load full-population aggregate metrics; public snapshot contains no customer records."""
    with DATA_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def _decode_lookup(values: pd.Series, labels: list[str] | dict[str, str]) -> pd.Series:
    if isinstance(labels, dict):
        return values.map(labels)
    return values.map(lambda index: labels[int(index)] if pd.notna(index) and 0 <= int(index) < len(labels) else None)
LOCAL_OUTPUT_COLUMNS = {
    "SKP_CLIENT": "id",
    "Financial_Health_Score": "fhs",
    "Financial_Health_Tier": "fh_tier",
    "Engagement_Score": "eng",
    "Engagement_Tier": "eng_tier",
    "Customer_Profile": "persona",
    "Next_Best_Action": "action",
    "NBA_Channel": "channel",
    "max_offer": "offer",
    "Action_Rationale": "rationale",
    "Opportunity_Type": "opportunity",
    "Matrix_Segment": "matrix_segment",
    "expected_bad_rate": "expected_bad",
    "fh_thin_file": "thin_file",
    "fh_policy_cap": "policy_cap",
    "n_open_delinquent": "n_open_delinquent",
    "any_default": "any_default",
    "dti": "dti",
    "dp_ratio": "dp_ratio",
    "history_months": "history_months",
    "income": "income",
    "days_since_last_activity": "days_since_last_activity",
    "active_months_12m": "active_months_12m",
    "app_sessions_wk": "app_sessions_wk",
    "pillar_Repayment History": "pillar_repayment",
    "pillar_Credit Standing": "pillar_credit",
    "pillar_Debt Burden (DTI)": "pillar_dti",
    "pillar_Down-payment Buffer": "pillar_down_payment",
    "pillar_Pre-approved Capacity": "pillar_capacity",
    "E1_digital": "E1_digital", "E2_recency": "E2_recency", "E3_frequency": "E3_frequency",
    "E4_responsiveness": "E4_responsiveness", "E5_breadth": "E5_breadth",
}
FH_TIER_LABELS = {
    "High Financial Health": "High",
    "Moderate Health": "Medium",
    "Financial Stress / Low Health": "Low",
}
ENG_TIER_LABELS = {
    "High Engagement": "High",
    "Medium Engagement": "Medium",
    "Low / Dormant Engagement": "Low",
}


@lru_cache(maxsize=1)
def _read_local_output(path: str, modified_ns: int, size: int) -> pd.DataFrame:
    del modified_ns, size  # metadata is part of the cache key to invalidate changed files
    frame = pd.read_csv(path, usecols=lambda column: column in LOCAL_OUTPUT_COLUMNS, low_memory=False)
    required = {"SKP_CLIENT", "Financial_Health_Score", "Financial_Health_Tier", "Engagement_Score", "Engagement_Tier", "Next_Best_Action"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Full output CSV is missing required columns: {sorted(missing)}")
    return frame


def customer_frame(data: dict[str, Any], full_csv_path: str | Path | None = None) -> pd.DataFrame:
    """Decode the safe snapshot, or an explicitly configured full local output CSV."""
    if full_csv_path:
        path = Path(full_csv_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Customer output CSV not found: {path}")
        stat = path.stat()
        frame = _read_local_output(str(path), stat.st_mtime_ns, stat.st_size).rename(columns=LOCAL_OUTPUT_COLUMNS).copy()
        if frame["id"].isna().any() or frame["id"].duplicated().any():
            raise ValueError("Full output CSV must contain one row per non-null customer ID")
        frame["fh_tier"] = frame["fh_tier"].map(FH_TIER_LABELS).fillna(frame["fh_tier"])
        frame["eng_tier"] = frame["eng_tier"].map(ENG_TIER_LABELS).fillna(frame["eng_tier"])
        return frame

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


def update_full_population_aggregates(data: dict[str, Any], customers: pd.DataFrame) -> dict[str, Any]:
    """Refresh score, segment, and action aggregates from every loaded customer row."""
    result = deepcopy(data)
    if customers.empty:
        raise ValueError("Cannot refresh dashboard aggregates from an empty customer output")
    tiers = ("High", "Medium", "Low")
    population = len(customers)

    for key, score_column, tier_column, mean_key, component_map in (
        ("fh", "fhs", "fh_tier", "mean_fhs", {
            "Repayment History": "pillar_repayment", "Credit Standing": "pillar_credit",
            "Debt Burden (DTI)": "pillar_dti", "Down-payment Buffer": "pillar_down_payment",
            "Pre-approved Capacity": "pillar_capacity",
        }),
        ("eng", "eng", "eng_tier", "mean_eng", {
            "E1_digital": "E1_digital", "E2_recency": "E2_recency", "E3_frequency": "E3_frequency",
            "E4_responsiveness": "E4_responsiveness", "E5_breadth": "E5_breadth",
        }),
    ):
        section = result[key]
        counts = customers[tier_column].value_counts().reindex(tiers, fill_value=0)
        section["tier_counts"] = {tier: int(counts[tier]) for tier in tiers}
        edges = section["hist"]["edges"]
        score_bins = pd.cut(customers[score_column], bins=[*edges, max(100, edges[-1] + 2)], labels=edges, right=False, include_lowest=True)
        histogram = pd.crosstab(customers[tier_column], score_bins).reindex(index=tiers, columns=edges, fill_value=0)
        section["hist"]["counts"] = {tier: [int(value) for value in histogram.loc[tier].tolist()] for tier in tiers}

        for tier in ("All", *tiers):
            rows = customers if tier == "All" else customers[customers[tier_column] == tier]
            profile = section["tier_profile"].setdefault(tier, {})
            profile["n"] = len(rows)
            profile[mean_key] = float(rows[score_column].mean()) if len(rows) else 0.0
            component_key = "pillars" if key == "fh" else "components"
            profile[component_key] = {
                label: float(rows[column].mean())
                for label, column in component_map.items()
                if column in rows and rows[column].notna().any()
            }
            if key == "fh":
                if "expected_bad" in rows:
                    profile["expected_bad"] = float(rows["expected_bad"].mean())
                if "thin_file" in rows:
                    profile["thin_file"] = float(rows["thin_file"].fillna(False).astype(bool).mean())
                if "policy_cap" in rows:
                    profile["policy_capped"] = float(rows["policy_cap"].notna().mean())
                if "n_open_delinquent" in rows:
                    delinquent = rows["n_open_delinquent"].fillna(0).gt(0)
                    profile["open_delinquent"] = float(delinquent.mean())
                    defaulted = rows["any_default"].fillna(False).astype(bool) if "any_default" in rows else False
                    profile["ever_delinquent"] = float((delinquent | defaulted).mean())
                for column, label, reducer in (("dti", "median_dti", "median"), ("dp_ratio", "mean_dp", "mean"),
                                               ("history_months", "median_history", "median"), ("income", "median_income", "median")):
                    if column in rows:
                        value = rows[column].median() if reducer == "median" else rows[column].mean()
                        profile[label] = None if pd.isna(value) else float(value)
                if "dti" in rows:
                    profile["dti_over_tip"] = float(rows["dti"].gt(0.225).mean())
                    profile["dti_over_ceiling"] = float(rows["dti"].gt(0.325).mean())
                if "eng_tier" in rows:
                    profile["eng_mix"] = {name: float(rows["eng_tier"].eq(name).mean()) for name in tiers}
            else:
                for column, label, operation in (("app_sessions_wk", "app_users", "positive"),
                                                 ("days_since_last_activity", "active_90d", "active"),
                                                 ("days_since_last_activity", "median_days", "median"),
                                                 ("active_months_12m", "mean_active_months", "mean")):
                    if column not in rows:
                        continue
                    values = rows[column]
                    value = values.fillna(0).gt(0).mean() if operation == "positive" else values.le(90).mean() if operation == "active" else values.median() if operation == "median" else values.mean()
                    profile[label] = None if pd.isna(value) else float(value)
                if "fh_tier" in rows:
                    profile["fh_mix"] = {name: float(rows["fh_tier"].eq(name).mean()) for name in tiers}

    result["meta"]["n_customers"] = population
    kpi = result["kpi"]
    kpi.update({"n_customers": population, "avg_fhs": float(customers["fhs"].mean()),
                "avg_eng": float(customers["eng"].mean()), "low_fh": int(customers["fh_tier"].eq("Low").sum())})
    for column, name, transform in (("expected_bad", "avg_expected_bad", "mean"), ("thin_file", "thin_file", "sum"),
                                    ("policy_cap", "policy_capped", "notna"), ("days_since_last_activity", "active_90d", "active"),
                                    ("app_sessions_wk", "app_users", "positive")):
        if column not in customers:
            continue
        values = customers[column]
        value = values.mean() if transform == "mean" else values.fillna(False).astype(bool).sum() if transform == "sum" else values.notna().sum() if transform == "notna" else values.le(90).mean() if transform == "active" else values.fillna(0).gt(0).mean()
        kpi[name] = float(value) if transform in {"mean", "active", "positive"} else int(value)

    for cell in result["matrix"]["cells"]:
        rows = customers[customers["fh_tier"].eq(cell["fh"]) & customers["eng_tier"].eq(cell["eng"])]
        cell["customers"] = len(rows)
        cell["share"] = len(rows) / population
        if len(rows):
            cell["avg_fhs"] = float(rows["fhs"].mean())
            cell["avg_eng"] = float(rows["eng"].mean())
            if "expected_bad" in rows:
                cell["expected_bad"] = float(rows["expected_bad"].mean())
            if "thin_file" in rows:
                cell["thin_file"] = float(rows["thin_file"].fillna(False).astype(bool).mean())
            if "offer" in rows:
                cell["median_offer"] = float(rows["offer"].median())
                cell["total_max_offer"] = float(rows["offer"].fillna(0).sum())

    if {"persona", "action"}.issubset(customers.columns):
        work = customers.copy()
        work["low_variant"] = work["thin_file"].fillna(False).map({True: "thin", False: ""}) if "thin_file" in work else ""
        grouped = work.groupby(["persona", "low_variant", "action"], dropna=False).size().reset_index(name="n").sort_values("n", ascending=False)
        result["matrix"]["nba"] = [{"persona": row.persona, "low_variant": row.low_variant, "Next_Best_Action": row.action, "n": int(row.n)} for row in grouped.itertuples(index=False)]
        if len(grouped):
            kpi["top_nba"] = grouped.iloc[0]["action"]
            kpi["top_nba_count"] = int(grouped.iloc[0]["n"])

    result["customers"]["rows"] = []
    result["customers"]["n_sample"] = 0
    result["customers"]["customer_records_included"] = False
    return result


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
    if priorities and "prio" in result:
        result = result[result["prio"].isin(priorities)]
    return result
