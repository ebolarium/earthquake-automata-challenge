#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST="$ROOT/reference/upstream/EarthquakeNPP"
REPOSITORY=https://github.com/ss15859/EarthquakeNPP.git
COMMIT=26d18048e1ca8ff2b02c7016b993de48ed0760f5

fresh_checkout=0
if [ ! -d "$DEST/.git" ]; then
  git clone --filter=blob:none --no-checkout "$REPOSITORY" "$DEST"
  fresh_checkout=1
fi

if [ "$fresh_checkout" -eq 0 ] && [ -n "$(git -C "$DEST" status --short)" ]; then
  echo "reference checkout has local changes: $DEST" >&2
  exit 1
fi

git -C "$DEST" fetch --depth 1 origin "$COMMIT"
git -C "$DEST" checkout --detach "$COMMIT"

actual=$(git -C "$DEST" rev-parse HEAD)
if [ "$actual" != "$COMMIT" ]; then
  echo "reference checkout mismatch: expected $COMMIT, got $actual" >&2
  exit 1
fi

echo "EarthquakeNPP reference ready at $actual"
