# CH002-003: UCERF3 Fault Sections and RELM Geometry

## Question

Can the admitted UCERF3 fault geometry and loading alternatives be parsed and
mapped reproducibly to the frozen California RELM grid without fitting a model?

## Inputs

- USGS OFR 2013-1165 `FaultSectionData.xlsx`, 821,878 bytes, locked by SHA-256.
- Frozen 7,682-cell California RELM grid.
- No earthquake target, validation outcome, or legacy Automata state.

## Method

A dependency-free OOXML reader extracts cached worksheet values. Geometry and
loading rows are joined by UCERF3 section ID. All eight combinations of fault
model and deformation model remain separate:

```text
FM3.1 or FM3.2 x Zeng, NeoKinema, Geologic, or ABM
```

The clean export contains 350 sections and 2,407 fault-trace vertices. Raw and
generated data stay outside Git; their source, parser, and output hashes are
committed in the manifests.

For each RELM cell center, CH002-003 computes the four nearest UCERF3 trace
sections and point-to-polyline distances. It does not choose a kernel bandwidth,
cutoff, fault-model branch, or deterministic earthquake-to-fault assignment.

## Results

| Quantity | Value |
| --- | ---: |
| Fault sections | 350 |
| FM3.1 sections | 313 |
| FM3.2 sections | 320 |
| RELM cells | 7,682 |
| Median nearest-trace distance | 22.910 km |
| Cells within 50 km | 5,536 |
| Maximum nearest-trace distance | 213.351 km |

Two independent grid exports produced the same SHA-256. Unit tests cover OOXML
cell types, geometry/loading joins, absent branches, segment distance, stable
nearest ordering, normalized projection, and neutral off-fault cells.

## Interpretation

The geometry gate is complete, but this is not a forecast result. The large
maximum distance confirms that a nearest-fault assignment without an off-fault
state would be scientifically indefensible. Later projection must retain a
neutral off-fault option and report bandwidth/cutoff ablations.

## Next Step

CH002-004 will construct the fault-section graph and a seeded correlated initial
state ensemble. It will freeze graph adjacency and ensemble priors before any
fit or validation score is read.
