"""Extract a safe, aggregate-only snapshot from dashboard HTML and optional full output CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from data import customer_frame, update_full_population_aggregates

MARKER = "window.CI360 = "


def extract_dashboard_data(source_html: Path) -> dict:
    source = source_html.read_text(encoding="utf-8")
    marker_position = source.find(MARKER)
    if marker_position < 0:
        raise ValueError(f"Could not find {MARKER.strip()!r} in {source_html}")
    payload_start = marker_position + len(MARKER)
    payload, _ = json.JSONDecoder().raw_decode(source[payload_start:])
    required = {"meta", "kpi", "fh", "eng", "matrix", "customers"}
    if not isinstance(payload, dict) or not required.issubset(payload):
        raise ValueError("The CI360 snapshot is missing required dashboard sections")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Source dashboard.html")
    parser.add_argument("destination", type=Path, help="Destination JSON snapshot")
    parser.add_argument("--customer-output", type=Path, help="Full customer output CSV used to refresh all population summaries")
    parser.add_argument("--include-customer-sample", action="store_true", help="Include embedded record-level rows; do not use for public deployment")
    args = parser.parse_args()

    payload = extract_dashboard_data(args.source)
    if args.customer_output:
        full_rows = customer_frame(payload, args.customer_output)
        expected = payload["meta"]["n_customers"]
        if len(full_rows) != expected:
            raise ValueError(f"Output CSV has {len(full_rows):,} rows; expected {expected:,}")
        payload = update_full_population_aggregates(payload, full_rows)
    if not args.include_customer_sample:
        payload["customers"]["rows"] = []
        payload["customers"]["n_sample"] = 0
        payload["customers"]["customer_records_included"] = False

    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {args.destination}: {payload['meta']['n_customers']:,} customers; record-level rows excluded")


if __name__ == "__main__":
    main()
