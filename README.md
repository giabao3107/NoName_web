# Customer Intelligence 360° — Streamlit dashboard

Interactive Streamlit + Plotly dashboard for the BI10 Season 10 Round 2 financial-services challenges: Financial Health Score, Engagement Score, and segmentation / Next Best Actions. It uses the team's palette from `Code/config/utils.py` on a white app canvas matching the chart backgrounds.

## Public demo and full-population analysis

`data/ci360.json` contains refreshed aggregates calculated against the complete **1,000,528-customer** output file. It has no customer IDs or row-level financial records. The hosted dashboard shows portfolio-wide score distributions, profiles, segment counts, action counts, and the other aggregate analyses without exposing individual customers.

The final customer-level CSV is about 1.23 GB and contains customer identifiers, scores, offer values, and action rationales. Do not copy it into the public GitHub repository or set the local-data environment variable on a public deployment.

## Analyze all customer records locally

From the source project root, install dependencies and point the app at the complete Task 3 output:

```powershell
python -m pip install -r dashboard_app/requirements.txt
$env:BI10_CUSTOMER_OUTPUT_CSV = "output/Task3/scores/final_customer_intelligence_output.csv"
streamlit run dashboard_app/app.py
```

The app loads the complete file (not a sample), validates that it has one row per scored customer, and refreshes the dashboard's customer-tier, score-histogram, profile, matrix, and Next Best Action aggregates from those rows. Search, tier filters, and sorting in the local drilldown apply across the full loaded population; the table displays up to 100 matching rows at a time. The CSV stays on the local machine.

To run the public aggregate-only version locally, omit `BI10_CUSTOMER_OUTPUT_CSV`:

```powershell
Remove-Item Env:BI10_CUSTOMER_OUTPUT_CSV -ErrorAction SilentlyContinue
streamlit run dashboard_app/app.py
```

## Refresh the safe snapshot before publishing

From the source project root, regenerate the aggregate JSON using the current full output. The customer file is read to calculate aggregates but its records are not written into the JSON:

```powershell
python dashboard_app/prepare_data.py dashboard.html dashboard_app/data/ci360.json --customer-output output/Task3/scores/final_customer_intelligence_output.csv
```

Copy only the contents of `dashboard_app/` to the root of the dedicated dashboard repository. The full CSV, raw tables, and record-level local snapshots are excluded from the published app.

## Deploy

For Streamlit Community Cloud, point the app to `app.py` on branch `main` and use `requirements.txt`. The repository's `data/ci360.json` is aggregate-only; do not configure `BI10_CUSTOMER_OUTPUT_CSV` in the hosted app.

## Methodology notes

- Financial Health Score: repayment history 40%, credit standing 30%, debt-to-income 15%, down-payment 15%, followed by policy caps.
- Engagement Score: digital 20%, recency 20%, frequency 25%, responsiveness 20%, product breadth 15%.
- Tier boundaries: High ≥80, Medium 50–79, Low <50.
- Delinquency, conversion, and score-validation charts are observational; they do not establish causality.
- Expected call value is modeled, not realized profit.

Run tests from this directory with `python -m pytest tests -q`. The analysis context is in the source project's `BI10_ROUND02.md` and `output/Task{1,2,3}/report/`.
