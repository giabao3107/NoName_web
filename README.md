# Customer Intelligence 360° — Streamlit dashboard

Interactive Streamlit + Plotly implementation of the BI10 Season 10 Round 2 financial-services dashboard. It presents the three challenge areas: explainable Financial Health Score, Engagement Score and validation, and customer segmentation with Next Best Actions.

## Run locally

Run from this dashboard directory:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

When this folder is copied to the root of its dedicated GitHub repository, the same commands apply.

## Data, privacy, and size

`data/ci360.json` is a small aggregate-only snapshot extracted from the source `dashboard.html`. It contains full-population analysis metrics, charts' supporting aggregates, and **no customer-level rows or identifiers**. The 1.23 GB customer-level output CSV and raw source data are not included. The hosted demo consequently disables the record-level explorer and calls this out in the UI. This keeps the public dashboard from publishing individual financial scores, customer identifiers, offer amounts, or personal action rationales.

Before copying this folder into the standalone dashboard repository, refresh the safe aggregate snapshot from the source project root after updating `dashboard.html`:

```bash
python dashboard_app/prepare_data.py dashboard.html dashboard_app/data/ci360.json
```

The deployed repository contains only the generated aggregate snapshot, not the source HTML or raw data.
The preparation script has an explicit `--include-customer-sample` option for authorized local analysis only. That file contains record-level financial attributes and must not be pushed to a public repository or deployed publicly without appropriate data authorization and privacy review:

```bash
python dashboard_app/prepare_data.py dashboard.html dashboard_app/data/ci360_local.json --include-customer-sample
```

## Deploy

Recommended host: Streamlit Community Cloud. Copy the contents of this `dashboard_app/` folder to the root of the new GitHub repository; create a Streamlit app pointing at `app.py` and specify `requirements.txt` as its dependency file. The checked-in data snapshot is aggregate-only; no secrets or backend database are required.

## Methodology notes

- Financial Health Score: repayment history 40%, credit standing 30%, debt-to-income 15%, down-payment 15%, followed by policy caps.
- Engagement Score: digital 20%, recency 20%, frequency 25%, responsiveness 20%, product breadth 15%.
- Tier boundaries: High ≥80, Medium 50–79, Low <50.
- Delinquency, conversion, and score-validation charts are observational. They support prioritization and calibration, not causal conclusions.
- Expected call value is modeled, not realized profit.

Run tests from this directory with `python -m pytest tests -q`. The aggregate snapshot is derived from the challenge analysis outputs and inlined summary payload in the source project's `dashboard.html`. See the source project's `BI10_ROUND02.md` brief and `output/Task{1,2,3}/report/` for supporting analyses.
