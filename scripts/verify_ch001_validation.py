#!/usr/bin/env python3
"""Verify CH001-003 validation totals from the committed daily-score contract."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.training_matrix import sha256_file  # noqa: E402


MANIFEST = Path("data/manifests/ch001-linear-v1-validation.json")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != "development_validation_completed":
        raise ValueError("validation manifest is not complete")
    if manifest["protocol"].get("locked_retrospective_opened") is not False:
        raise ValueError("locked retrospective gate was not preserved")
    invariants = manifest["count_and_magnitude_invariants"]
    if invariants["maximum_daily_expected_count_difference"] != 0.0:
        raise ValueError("challenger changed ETAS expected counts")
    if invariants["etas_expected_count_sum"] != invariants["challenger_expected_count_sum"]:
        raise ValueError("challenger and ETAS count totals differ")

    output = manifest["outputs"]
    daily_path = Path(output["daily_paired_scores"])
    if sha256_file(daily_path) != output["daily_paired_scores_sha256"]:
        raise ValueError("daily paired-score hash mismatch")
    rows = list(csv.DictReader(daily_path.open(encoding="utf-8", newline="")))
    if len(rows) != manifest["period"]["issue_days"]:
        raise ValueError("daily paired-score row count changed")
    if rows[0]["issue_date"] != manifest["period"]["start"]:
        raise ValueError("validation first issue date changed")
    expected_last = np.datetime_as_string(
        np.datetime64(manifest["period"]["end_exclusive"], "D")
        - np.timedelta64(1, "D")
    )
    if rows[-1]["issue_date"] != expected_last:
        raise ValueError("validation last issue date changed")

    for result_key, label in (
        ("m_gte_2.5", "m2_5"),
        ("m_gte_3.5", "m3_5"),
        ("m_gte_4.0", "m4_0"),
    ):
        result = manifest["results"][result_key]
        count = sum(int(row[f"target_count_{label}"]) for row in rows)
        gain = sum(float(row[f"paired_gain_{label}"]) for row in rows)
        if count != result["target_events"]:
            raise ValueError(f"target total changed for {result_key}")
        if not np.isclose(gain, result["information_gain"], rtol=0, atol=1e-8):
            raise ValueError(f"information gain changed for {result_key}")
    low = manifest["results"]["low_etas_intensity"]
    low_count = sum(int(row["low_etas_target_count"]) for row in rows)
    low_gain = sum(float(row["low_etas_paired_gain"]) for row in rows)
    if low_count != low["target_events"] or not np.isclose(
        low_gain, low["information_gain"], rtol=0, atol=1e-8
    ):
        raise ValueError("low-ETAS validation totals changed")
    for result in manifest["results"].values():
        for bootstrap in result["bootstrap"].values():
            if bootstrap["valid_replicates"] != 10_000:
                raise ValueError("bootstrap replicate count changed")
            if not bootstrap["lower"] <= bootstrap["median"] <= bootstrap["upper"]:
                raise ValueError("bootstrap interval is not ordered")
    print(
        f"verified {len(rows)} validation days, "
        f"{manifest['results']['m_gte_2.5']['target_events']} primary events"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
