"""Check Docker resources before starting the full reference inversion."""

from __future__ import annotations

import subprocess


GIB = 1024**3
KIB_PER_GIB = 1024**2
MINIMUM_MEMORY_GIB = 14
MINIMUM_SWAP_GIB = 6
RECOMMENDED_MEMORY_GIB = 15.5
RECOMMENDED_SWAP_GIB = 8


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

    swap_result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "etas-challenge-reference",
            "cat",
            "/proc/swaps",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    swap_kib = sum(
        int(line.split()[2])
        for line in swap_result.stdout.splitlines()[1:]
        if line.split()
    )
    swap_gib = swap_kib / KIB_PER_GIB
    print(f"Docker swap: {swap_gib:.2f} GiB")

    if memory_gib < MINIMUM_MEMORY_GIB:
        raise SystemExit(
            f"full inversion requires at least {MINIMUM_MEMORY_GIB} GiB; "
            f"{RECOMMENDED_MEMORY_GIB} GiB is recommended"
        )
    if swap_gib < MINIMUM_SWAP_GIB:
        raise SystemExit(
            f"full inversion requires at least {MINIMUM_SWAP_GIB} GiB swap; "
            f"{RECOMMENDED_SWAP_GIB} GiB is recommended"
        )

    if memory_gib < RECOMMENDED_MEMORY_GIB or swap_gib < RECOMMENDED_SWAP_GIB:
        print("warning: Docker Desktop settings of 16 GiB memory and 8 GiB swap are recommended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
