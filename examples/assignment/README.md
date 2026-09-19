# HW3 regression examples

These minimal, repository-owned cases reproduce the assignment workflows. They
are regression inputs, not material-property recommendations. Every coefficient
is explicit; no test reads a school folder or queries a property website.
The existing four HW2 examples remain in the editor homework picker.

| File | Independent expected result |
| --- | --- |
| `wall-sign.json` (2.6) | 70 + 8,000 × 0.007 = 126 °C. The negative outward source must warn and prevent unqualified Apply. |
| `windows.json` (2.11) | 90 / 0.078125 = 1,152 W. The supplied 1,000 W passes the legacy 15% checker but fails the 1% checker and solver. Temperatures are rises. |
| `storage.json` (2.16) | 1,000 × 4,200 × 1 = 4,200,000 J/K; heating 1 K in 3,600 s needs 1,166.666… W. No network steady assumption is needed to evaluate storage. |
| `dorm-wall.json` (3.4) | Original: 22 / (0.2 + 0.3 + 1/30) = 41.25 W/m². Retrofit: 22 / (0.2 + 2.3 + 1/30) = 8.684210526… W/m². Total powers use the declared 2 m² reference. |
| `composite-wall.json` (3.20) | q″ = 2,300 / (0.04 + 0.000652 + 0.05 + 0.001455 + 0.001) W/m². The contact derivation describes 2 m² and returns 0.025 K/W total. |
| `wire.json` (3.44) | Power = 7.373 × 3 = 22.119 W total. Wire temperature = 20 + 7.373 × (0.03183 + 1.0373 + 3.0315) °C. |
| `sphere.json` (3.60) | q = 80 / [(1/2 − 1/2.25)/(4π × 0.06) + 1/(6 × 4π × 2.25²)] W. The split radius is explicitly supplied as 2.2 m; it is not solved. |

All seven opt into compact layout. Export at 6.5 inches wide; do not use font
scaling to hide a width-limit finding. `tests/test_assignment_examples.py`
checks the calculations independently, serialization, fit and orientation.

```console
python -m thermodraw check examples/assignment/windows.json --physics --check-policy analysis
python -m thermodraw solve-physics examples/assignment/sphere.json --json
python -m thermodraw render examples/assignment/composite-wall.json -o composite-wall.svg
```

The first command intentionally reports the wrong glass assertion. The
negative-source example also intentionally fails verification until corrected.
