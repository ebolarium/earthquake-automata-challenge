"""Verify downloaded EarthquakeNPP artifacts against the locked manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "manifests" / "reference-comcat25.json"
REFERENCE_ROOT = ROOT / "reference" / "upstream" / "EarthquakeNPP"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    checked = 0
    for artifact in manifest["reference_artifacts"]:
        path = REFERENCE_ROOT / artifact["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(
                f"checksum mismatch for {artifact['path']}: "
                f"expected {artifact['sha256']}, got {actual}"
            )
        if "lines" in artifact:
            with path.open("rb") as handle:
                lines = sum(1 for _ in handle)
            if lines != artifact["lines"]:
                raise ValueError(
                    f"line-count mismatch for {artifact['path']}: "
                    f"expected {artifact['lines']}, got {lines}"
                )
        checked += 1
        print(f"ok  {artifact['path']}")
    print(f"verified {checked} locked reference artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

