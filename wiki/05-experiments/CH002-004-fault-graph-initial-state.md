# CH002-004: Fault Graph and Initial-State Ensemble

## Question

Can CH-002 represent uncertain initial stress-minus-strength structure without
asserting one true stress map or reading forecast targets?

## Hypothesis

Nearby, similarly oriented sections that coexist in a UCERF3 fault model should
have a softer readiness-correlation prior than distant or incompatible
sections. Initial stress and effective strength are both unknown, so a particle
ensemble should represent their difference rather than selecting one ledger.

## Frozen Geometry Prior

For every pair of 350 UCERF3 sections, the graph stores minimum trace-segment
distance, length-weighted axial strike alignment, and fault-model compatibility.
The frozen edge weight is

```text
w_ab = shared_model_ab
       * exp(-0.5 * (distance_ab / 25 km)^2)
       * (0.25 + 0.75 * alignment_ab^2)
```

The alignment floor allows plausible bends, intersections, and stepovers to
remain weakly connected. Sections that share neither FM3.1 nor FM3.2 receive no
edge even when their alternative traces are spatially close.

## Initial State

The graph prior precision is

```text
Q = I + 4 * normalized_graph_laplacian
```

Using committed seed `20260822`, two independent 256-particle correlated fields
are drawn. Exactly 32 particles are assigned to each of the eight UCERF3
fault/deformation branches. They are named `stress_component` and
`effective_strength_component`; their difference is the criticality margin.
Each particle is zero outside its branch and is centered and scaled over its
active sections so that

```text
mean(margin) = 0
std(margin) = 1
margin = stress_component - effective_strength_component
```

This normalization is necessary: the background softmax cannot identify a
uniform offset, and its later sensitivity parameter absorbs the state scale.

## Scientific Boundary

The component names encode the structural hypothesis, not measurements. Stress
and effective strength are exchangeable latent uncertainties in this version;
only their difference is identified. Values are dimensionless and cannot be
reported as Coulomb stress, MPa, fault strength, or probability of rupture.

## Results

| Quantity | Value |
| --- | ---: |
| Sections | 350 |
| Fault pairs | 61,075 |
| Edge weights greater than `1e-6` | 11,561 |
| Particles | 256 |
| Particles per loading branch | 32 |
| Maximum absolute active particle mean | `4.25e-9` |
| Active particle standard-deviation range | `0.999999993–1.000000007` |
| Repeated output hash | Identical |

No earthquake catalog target, fit likelihood, validation result, or locked
retrospective result was read.

## Next Step

CH002-005 will define leakage-free daily state evolution. UCERF3 branch loading,
probabilistic event-to-section assignment, rupture depletion, and
ETAS-background-posterior assimilation will be implemented first on synthetic
replays. Directional transfer remains deferred.
