import pandas as pd

from data import customer_frame, filter_customers, load_dashboard_data, update_full_population_aggregates


def test_load_dashboard_data_reads_aggregate_snapshot_without_customer_records():
    data = load_dashboard_data()

    assert data["meta"]["n_customers"] == 1_000_528
    assert data["customers"]["n_sample"] == 0
    assert not data["customers"]["rows"]
    assert data["fh"]["tier_profile"]["All"]["n"] == data["meta"]["n_customers"]
    assert data["eng"]["tier_profile"]["All"]["n"] == data["meta"]["n_customers"]
    assert sum(data["fh"]["tier_counts"].values()) == data["meta"]["n_customers"]
    assert len(customer_frame(data)) == 0


def test_customer_filter_supports_tiers_search_and_priority():
    data = {
        "customers": {
            "cols": ["id", "fhs", "fh", "eng", "et", "prio"],
            "rows": [[101, 90.0, 0, 70.0, 1, 1], [202, 30.0, 2, 20.0, 2, 0]],
        }
    }
    customers = customer_frame(data)

    result = filter_customers(
        customers,
        search="202",
        fh_tiers=["Low"],
        engagement_tiers=["Low"],
        priorities=[0],
    )

    assert result["id"].tolist() == [202]
    assert result["fh_tier"].tolist() == ["Low"]
    assert result["eng_tier"].tolist() == ["Low"]


def test_customer_frame_loads_full_local_output_csv(tmp_path):
    source = pd.DataFrame(
        {
            "SKP_CLIENT": [11, 22],
            "Financial_Health_Score": [91.0, 38.0],
            "Financial_Health_Tier": ["High Financial Health", "Financial Stress / Low Health"],
            "Engagement_Score": [84.0, 21.0],
            "Engagement_Tier": ["High Engagement", "Low / Dormant Engagement"],
            "Customer_Profile": ["Champion", "Support"],
            "Next_Best_Action": ["Review needs", "Repayment support"],
            "NBA_Channel": ["Service", "Digital"],
            "max_offer": [25_000_000, 0],
            "Action_Rationale": ["Suitable profile", "Stress signal"],
        }
    )
    source_path = tmp_path / "customers.csv"
    source.to_csv(source_path, index=False)

    loaded = customer_frame({"customers": {"cols": [], "rows": []}}, full_csv_path=source_path)

    assert len(loaded) == 2
    assert loaded["id"].tolist() == [11, 22]
    assert loaded["fh_tier"].tolist() == ["High", "Low"]
    assert loaded["eng_tier"].tolist() == ["High", "Low"]
    assert loaded["action"].tolist() == ["Review needs", "Repayment support"]


def test_full_output_refreshes_aggregate_charts_without_exporting_rows():
    data = {
        "meta": {"n_customers": 2},
        "kpi": {},
        "fh": {"hist": {"edges": [0, 50, 80], "counts": {}}, "tier_counts": {}, "tier_profile": {"All": {}, "High": {}, "Medium": {}, "Low": {}}},
        "eng": {"hist": {"edges": [0, 50, 80], "counts": {}}, "tier_counts": {}, "tier_profile": {"All": {}, "High": {}, "Medium": {}, "Low": {}}},
        "matrix": {"cells": [{"fh": "High", "eng": "High", "customers": 0}, {"fh": "Low", "eng": "Low", "customers": 0}], "nba": []},
        "customers": {"rows": [[999]], "n_sample": 1},
    }
    full_rows = pd.DataFrame(
        {
            "fhs": [90.0, 30.0], "fh_tier": ["High", "Low"],
            "eng": [85.0, 20.0], "eng_tier": ["High", "Low"],
            "expected_bad": [0.01, 0.08], "persona": ["Champion", "Support"],
            "action": ["Review needs", "Repayment support"], "thin_file": [False, True],
        }
    )

    updated = update_full_population_aggregates(data, full_rows)

    assert updated["fh"]["tier_counts"] == {"High": 1, "Medium": 0, "Low": 1}
    assert updated["fh"]["hist"]["counts"]["High"] == [0, 0, 1]
    assert updated["matrix"]["cells"][0]["customers"] == 1
    assert updated["kpi"]["top_nba"] in {"Review needs", "Repayment support"}
    assert updated["customers"]["rows"] == []
    assert data["fh"]["tier_counts"] == {}

def test_filter_returns_empty_when_no_customer_matches():
    customers = customer_frame(
        {"customers": {"cols": ["id", "fhs", "fh", "eng", "et", "prio"], "rows": [[7, 90, 0, 90, 0, 1]]}}
    )

    assert filter_customers(customers, search="missing").empty
