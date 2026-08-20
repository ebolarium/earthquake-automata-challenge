"""Export the locked local earthquake snapshot into the clean catalog schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from etas_challenge.catalog_export import export_catalog


LOCKED_SOURCE_SHA256 = "8d7a4faf6082f42490c48979881b7017a7d7d05a778a5062f411e64fc520d3d7"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("../earthquake.db"))
    parser.add_argument(
        "--region-shape",
        type=Path,
        default=Path(
            "artifacts/reference-comcat25/workspace/Datasets/ComCat/"
            "california_shape.npy"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/local/california-earthquakes-v1.sqlite"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/manifests/local-california-catalog-v1.json"),
    )
    parser.add_argument(
        "--snapshot-id", default="local-california-2026-08-19-v1"
    )
    parser.add_argument("--expected-source-sha256", default=LOCKED_SOURCE_SHA256)
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = export_catalog(
        source_path=args.source,
        region_path=args.region_shape,
        output_path=args.output,
        manifest_path=args.manifest,
        snapshot_id=args.snapshot_id,
        expected_source_sha256=args.expected_source_sha256,
        output_label="California earthquake observations without Mc filtering",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
