"""Extract the inlined CI360 snapshot from the source dashboard HTML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

MARKER = "window.CI360 = "


def extract_dashboard_data(source_html: Path) -> dict:
    source = source_html.read_text(encoding="utf-8")
    marker_position = source.find(MARKER)
    if marker_position < 0:
        raise ValueError(f"Could not find {MARKER.strip()!r} in {source_html}")
    payload_start = marker_position + len(MARKER)
    payload, _ = json.JSONDecoder().raw_decode(source[payload_start:])
    if not isinstance(payload, dict) or not {"meta", "kpi", "fh", "eng", "matrix", "customers"}.issubset(payload):
        raise ValueError("The CI360 snapshot is missing required dashboard sections")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Source dashboard.html")
    parser.add_argument("destination", type=Path, help="Destination JSON snapshot")
    parser.add_argument("--include-customer-sample", action="store_true", help="Include record-level rows; do not use for public deployment")
    args = parser.parse_args()
    payload = extract_dashboard_data(args.source)
    if not args.include_customer_sample:
        payload["customers"]["rows"] = []
        payload["customers"]["n_sample"] = 0
        payload["customers"]["customer_records_included"] = False
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    scope = "record-level sample included" if args.include_customer_sample else "aggregate-only; customer rows excluded"
    print(f"Wrote {args.destination}: {scope}")


if __name__ == "__main__":
    main()
