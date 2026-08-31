#!/usr/bin/env python3
"""Verify future adapter freezes against a server-timestamped proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


def git(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *arguments], text=True, capture_output=True, check=False
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--result-commit", required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--result-path", action="append", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.freeze_commit == args.result_commit:
        raise SystemExit("freeze and result commits must differ")
    ancestry = git("merge-base", "--is-ancestor", args.freeze_commit, args.result_commit)
    if ancestry.returncode:
        raise SystemExit("result commit is not a descendant of freeze commit")
    for path in args.result_path:
        if git("cat-file", "-e", f"{args.freeze_commit}:{path}").returncode == 0:
            raise SystemExit(f"result path already exists in freeze tree: {path}")
        if git("cat-file", "-e", f"{args.result_commit}:{path}").returncode:
            raise SystemExit(f"result path is missing from result tree: {path}")
    proof = json.loads(args.proof.read_text(encoding="utf-8"))
    if proof.get("freeze_commit") != args.freeze_commit:
        raise SystemExit("external proof does not match freeze commit")
    if proof.get("provider") not in {"github-actions", "opentimestamps", "rfc3161"}:
        raise SystemExit("external proof provider is not admitted")
    if not proof.get("timestamp_utc") or not proof.get("proof_id"):
        raise SystemExit("external proof is incomplete")
    print(json.dumps({
        "status": "ok",
        "freeze_commit": args.freeze_commit,
        "result_commit": args.result_commit,
        "result_paths": args.result_path,
        "proof_provider": proof["provider"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
