#!/usr/bin/env python3
"""Validate the committed Challenge V1 contract and all available inputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.challenge_contract import (  # noqa: E402
    load_challenge_contract,
    verify_locked_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=ROOT / "configs" / "challenge" / "challenge-v1.json",
    )
    args = parser.parse_args()

    payload = load_challenge_contract(args.contract)
    verify_locked_inputs(payload, ROOT)
    print(
        f"valid frozen challenge: {payload['challenge_id']} "
        f"({len(payload['locked_inputs'])} locked inputs)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
