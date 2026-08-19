# Native ETAS Mathematical Contract

## Scope

The native implementation follows the spatial-temporal ETAS parameterization
in Mizrahi, Nandan, and Wiemer (2021). It is implemented from the published
equations, independently of the locked reference source code.

For catalog events `i` before target time `t`, the conditional intensity is

```text
lambda(t, x, y) = mu + sum_i g(m_i, t-t_i, x-x_i, y-y_i).
```

The triggering contribution is

```text
g(m, dt, dx, dy)
  = k0 exp(a (m-m_ref))
    exp(-dt/tau) / (dt+c)^(1+omega)
    / (dx^2 + dy^2 + d exp(gamma (m-m_ref)))^(1+rho).
```

Time is measured in the catalog time unit and projected spatial coordinates
must use the corresponding reference distance unit. A source contributes only
when `dt > 0`.

## Closed-Form Integrals

With `D(m) = d exp(gamma (m-m_ref))`, the spatial integral over a disk of
radius `R` is

```text
pi/rho * (D^(-rho) - (R^2 + D)^(-rho)).
```

The whole-plane limit sets the second term to zero. For `omega < 0`, the
temporal integral from `t0` to `t1` is

```text
exp(c/tau) tau^(-omega)
* [Gamma(-omega, (t0+c)/tau) - Gamma(-omega, (t1+c)/tau)].
```

The `t1 = infinity` term is zero. The `omega = 0` limit uses the exponential
integral `E1`.

Magnitudes follow the exponential Gutenberg-Richter density

```text
f(m) = beta exp(-beta (m-m_ref)),  m >= m_ref.
```

The effective productivity exponent is `alpha = a - rho*gamma`. Integrating
direct offspring over time, the infinite plane, and magnitude gives

```text
eta = beta k0 pi d^(-rho) T
      / [rho (beta - alpha)],
```

where `T` is the full temporal integral. The branching ratio is finite only
when `beta > alpha`.

## Event Likelihood

For an event interval `(s, t]`, the native compensator is

```text
C(s, t) = mu A (t-s)
  + sum_i K(m_i) S(m_i)
    integral[max(0, s-t_i), t-t_i] T(u) du,
```

where the sum includes sources with `t_i < t`, `A` is region area, and `S(m)`
is the whole-plane spatial integral. Event-level scores follow

```text
LL  = log(lambda(t, x, y)) - C(s, t)
TLL = log(lambda_star(t))  - C(s, t)
SLL = LL - TLL.
```

Geographic event distances use the same spherical haversine calculation and
Earth radius (`6378.1 km`) as the locked reference.

## Verification Boundary

Closed forms are tested against independent adaptive quadrature. Event-level
intensities and likelihood terms are tested against the synthetic
`NATIVE-ALIGN-001` oracle at `1e-12` absolute tolerance. Reference software is
used only by the fixture generator and is not imported by native modules.

The locked reference omits the triggered compensator before the first event in
the test window. The native implementation retains the published interval
integral instead of reproducing this behavior. The fixture records both values
so later full-catalog comparisons cannot hide the discrepancy.

## Sources

- Ogata (1988), *Statistical Models for Earthquake Occurrences and Residual
  Analysis for Point Processes*, DOI `10.1080/01621459.1988.10478560`.
- Mizrahi, Nandan, and Wiemer (2021), *Embracing Data Incompleteness for Better
  Earthquake Forecasting*, DOI `10.1029/2021JB022379`, especially Equations
  2, 3, 28, and 29.
