from data import customer_frame, filter_customers, load_dashboard_data


def test_load_dashboard_data_reads_aggregate_snapshot_without_customer_records():
    data = load_dashboard_data()

    assert data["meta"]["n_customers"] == 1_000_528
    assert data["customers"]["n_sample"] == 0
    assert not data["customers"]["rows"]
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


def test_filter_returns_empty_when_no_customer_matches():
    customers = customer_frame(
        {"customers": {"cols": ["id", "fhs", "fh", "eng", "et", "prio"], "rows": [[7, 90, 0, 90, 0, 1]]}}
    )

    assert filter_customers(customers, search="missing").empty
