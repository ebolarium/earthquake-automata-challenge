#!/bin/sh
set -eu

url="https://pubs.usgs.gov/of/2013/1165/data/ofr2013-1165_FaultSectionData.xlsx"
expected="aa3d8ee48acb0887efa79921eccfde0f1a227b53688db8fa2d63f289096eb589"
output="${1:-data/raw/ucerf3/ofr2013-1165_FaultSectionData.xlsx}"

mkdir -p "$(dirname "$output")"
temporary="${output}.tmp"
trap 'rm -f "$temporary"' EXIT HUP INT TERM
curl -fsSL "$url" -o "$temporary"
actual="$(shasum -a 256 "$temporary" | awk '{print $1}')"
if [ "$actual" != "$expected" ]; then
  echo "UCERF3 source checksum mismatch: $actual" >&2
  exit 1
fi
mv "$temporary" "$output"
trap - EXIT HUP INT TERM
echo "verified UCERF3 source: $output ($actual)"
