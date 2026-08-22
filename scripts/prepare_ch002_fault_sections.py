#!/usr/bin/env python3
"""Export the hash-locked UCERF3 fault-section data into clean JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.training_matrix import sha256_file
from etas_challenge.ucerf3_faults import load_ucerf3_fault_sections


SOURCE_URL = (
    "https://pubs.usgs.gov/of/2013/1165/data/"
    "ofr2013-1165_FaultSectionData.xlsx"
)
SOURCE_SHA256 = "aa3d8ee48acb0887efa79921eccfde0f1a227b53688db8fa2d63f289096eb589"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/ucerf3/ofr2013-1165_FaultSectionData.xlsx"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/local/ch002-ucerf3-fault-sections-v1.json"),
    )
    args = parser.parse_args()

    actual_hash = sha256_file(args.input)
    if actual_hash != SOURCE_SHA256:
        raise ValueError("UCERF3 source SHA-256 does not match the admitted file")
    sections = load_ucerf3_fault_sections(args.input)
    payload = {
        "schema_version": 1,
        "dataset_id": "ch002-ucerf3-fault-sections-v1",
        "source": {
            "url": SOURCE_URL,
            "sha256": SOURCE_SHA256,
            "publication": "USGS Open-File Report 2013-1165",
            "first_admitted_issue_date": "2014-01-07",
        },
        "coordinate_order": "latitude,longitude",
        "slip_rate_units": "millimeters_per_year",
        "section_count": len(sections),
        "sections": [section.to_payload() for section in sections],
        "claim_boundary": (
            "UCERF3 geometry and branch inputs; no observed stress, strength, "
            "readiness state, forecast, or performance result."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(
        f"exported {len(sections)} UCERF3 sections to {args.output} "
        f"(sha256={sha256_file(args.output)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
