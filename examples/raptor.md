# The README hero: a Raptor-class throat wall

`raptor.json` is one square centimetre of a regeneratively cooled methalox
combustion-chamber wall at the throat, at the conditions publicly stated for
SpaceX's Raptor 3, drawn from combustion gas to methane coolant. It is the
diagram at the top of the README.

**Nothing in it is SpaceX data.** SpaceX has published a chamber pressure and
a cooling architecture, and nothing else that a thermal network needs. Every
temperature, resistance and heat rate below is an engineering estimate for
this class of engine, assembled from the public record and from the
open literature on high-pressure liquid engines, and labelled as such in the
diagram's title. The file exists to show what the library draws and checks,
not to describe a real engine.

The file carries no coordinates. The ladder solver places it, and
`thermodraw check --physics examples/raptor.json` reports nothing: the
numbers agree with each other, which is the one thing the diagram promises.

## What is public and what is estimated

| figure | value | status | source |
|---|---|---|---|
| Chamber pressure | 350 bar reached on test (2023); ~330 bar operational | public statement about Raptor | [Musk, May 2023](https://x.com/elonmusk/status/1657249739925258240); [Wikipedia, SpaceX Raptor](https://en.wikipedia.org/wiki/SpaceX_Raptor) |
| Propellants and cycle | liquid methane and liquid oxygen, full-flow staged combustion | public | [Wikipedia, SpaceX Raptor](https://en.wikipedia.org/wiki/SpaceX_Raptor) |
| Cooling | regenerative; Raptor 3 needs no external heat shield | public statement about Raptor | [Musk, August 2024](https://x.com/elonmusk/status/1819597689283121225) |
| Liner and jacket materials | copper-alloy liner, superalloy jacket | **assumed**: standard construction for the class, not confirmed by SpaceX | engine class |
| Copper-alloy liner limit | GRCop-84 rated to about 700 °C (973 K) as a chamber liner | engine class | [NASA GRC, GRCop-84](https://ntrs.nasa.gov/citations/20050196725) |
| Liner conductivity | GRCop-42 about 85 % IACS, roughly 320 W/m·K | material class | [NASA GRC, GRCop-42](https://ntrs.nasa.gov/citations/20190030433) |
| Throat heat flux | RD-180 at 257 bar: about 70 BTU/in²·s, which is 115 MW/m²; 100 BTU/in²·s (164 MW/m²) described as reachable | engine class | [DTIC ADA624807](https://apps.dtic.mil/sti/citations/ADA624807); [Wikipedia, RD-180](https://en.wikipedia.org/wiki/RD-180) |
| Throat heat flux, SSME | about 160 MW/m² | engine class | [Chinese J. Aeronautics, 2017](https://www.sciencedirect.com/science/article/pii/S1000936117301024) |
| Radiative share of wall load, CH₄/O₂ | under 10 % at the throat | engine class | [Goebel et al., CEAS Space Journal 6, 2014](https://doi.org/10.1007/s12567-014-0060-2) |
| Methalox combustion temperature | about 3500 K at high pressure | estimate | [Braeunig, combustion](http://braeunig.us/space/comb.htm) |
| Methane critical point | 190.6 K, 46.0 bar; the coolant is supercritical | physical constant | [NIST WebBook](https://webbook.nist.gov/) |
| Methane coolant temperatures | 120 to 140 K in, 300 to 500 K out, in subscale regen tests | engine class | [EUCASS 2017-381](https://www.eucass.eu/doi/EUCASS2017-381.pdf) |

## The design point

| quantity | value | why |
|---|---|---|
| through-flux | 10 kW per cm² (100 MW/m²) | rounded down from the 115 to 164 MW/m² range above |
| combustion gas | 3500 K | the estimate above |
| liner hot face | 900 K | margin under the 973 K liner limit |
| liner | 0.8 mm GRCop at 320 W/m·K | a thin hot wall over the cooling channels |
| coolant bulk | 300 K | midway between inlet and outlet |
| radiation | 8 % of the gas-side load | under the 10 % figure above |

## The arithmetic

Basis 1 cm², so `q = 10 000 W` through every series element.

- Gas side: ΔT = 3500 − 900 = 2600 K. Radiation carries 800 W and convection
  9200 W. `R_rad = 2600 / 800 = 3.25 K/W`;
  `R_conv = 2600 / 9200 = 0.283 K/W`.
- Liner: `R_cond = t / (k A) = 0.0008 / (320 × 0.0001) = 0.0250 K/W`, so the
  liner drops 250 K and the channel wall sits at 650 K.
- Coolant side: ΔT = 650 − 300 = 350 K. `R_conv = 350 / 10 000 = 0.0350 K/W`.

There is no thermal mass in the picture. The title says steady state, and a
liner at 0.28 J/K per cm² (0.8 mm of copper alloy) would settle in well under
a second in any case.

Balance at the two free nodes, as `--physics` computes it from the values as
typed:

| node | arrives | leaves | mismatch |
|---|---|---|---|
| liner hot face | 2600/0.283 + 2600/3.25 = 9987 W | 250/0.0250 = 10 000 W | 0.13 % |
| channel wall | 10 000 W | 350/0.0350 = 10 000 W | 0 |

The checker allows 15 %. Change the gas-side convection to 0.20 K/W and it
reports the imbalance at the hot face and the rate that no longer matches,
which is the example the README shows.
