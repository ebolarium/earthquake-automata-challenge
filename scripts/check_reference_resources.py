"""Check Docker resources before starting the full reference inversion."""

from __future__ import annotations

import subprocess


GIB = 1024**3
MINIMUM_MEMORY_GIB = 12
RECOMMENDED_MEMORY_GIB = 14


def main() -> int:
    result = subprocess.run(
        ["docker", "info", "--format", "{{.MemTotal}}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    memory_bytes = int(result.stdout.strip())
    memory_gib = memory_bytes / GIB
    print(f"Docker memory: {memory_gib:.2f} GiB")

    if memory_gib < MINIMUM_MEMORY_GIB:
        raise SystemExit(
            f"full inversion requires at least {MINIMUM_MEMORY_GIB} GiB; "
            f"{RECOMMENDED_MEMORY_GIB} GiB is recommended"
        )

    if memory_gib < RECOMMENDED_MEMORY_GIB:
        print(
            f"warning: {RECOMMENDED_MEMORY_GIB} GiB is recommended for "
            "headroom during distance preparation"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
