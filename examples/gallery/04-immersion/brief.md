# Two-phase immersion-cooled rack with a condenser loop

Draw this thermal network as a ThermoDraw diagram.

## The system

A data-centre rack of servers immersed in a dielectric fluid that boils, with
the vapour condensed and the heat carried out to ambient air.

- A **server board** carries eight processors dissipating **400 W** each,
  **3.2 kW** total. The processor junctions sit at **72 C**.
- Each processor's integrated heat spreader is at **61 C**; junction to
  spreader is **0.0275 K/W** by conduction.
- The spreader is **immersed in a dielectric fluid** which boils on its surface
  at **49 C**. Pool boiling is a very effective convection path:
  **0.00375 K/W**.
- The **vapour rises and condenses** on a water-cooled condenser coil. The
  condensation itself happens at constant temperature - this is the latent heat
  of the fluid being given up, **3.2 kW** of it, with no temperature drop
  across the phase change at all.
- The **condenser coil surface** is at **40 C**; the condensing film resistance
  is **0.0028 K/W**.
- Inside the coil runs **technical water**, entering at **30 C** and leaving at
  **38 C**. It carries the heat away by flowing, not by conducting: the water
  physically transports **3.2 kW** from the rack to the coolant distribution
  unit.
- The **coolant distribution unit** is a plate heat exchanger coupling that
  technical water loop to the **facility water** loop. The exchanger has an
  overall resistance of **0.0019 K/W** between the two streams. Facility water
  is at **26 C**.
- The **pump** driving the technical water loop adds **800 W** of its own work
  to the fluid as heat.
- A **dry cooler** finally rejects everything to **ambient air at 24 C**,
  **0.0058 K/W**.
- The fluid inventory in the tank has a thermal mass of **240 kJ/K**.


## How to work

Your only documentation is `docs/schema.md` in this repository. Read that, and
this brief, and nothing else.

Do **not** read anything under `src/`, and do not read `CLAUDE.md`,
`README.md`, `CHANGELOG.md`, anything under `tests/`, or any other file under
`examples/`. Do not open an existing `.json` diagram. If you find yourself
wanting to, that is exactly the gap this exercise is measuring - write it down
in your findings and carry on from the schema alone.

Work from the repository root, and use the **Bash** tool (Git Bash), not
PowerShell, for these:

```
cd "C:/Users/Peter Cetner/Documents/GitHub/ThermoDraw"
PYTHONPATH=src python -m thermodraw check    examples/gallery/04-immersion/rack.json
PYTHONPATH=src python -m thermodraw describe examples/gallery/04-immersion/rack.json
PYTHONPATH=src python -m thermodraw render   examples/gallery/04-immersion/rack.json -o examples/gallery/04-immersion/rack.svg
```

Write the diagram to `examples/gallery/04-immersion/rack.json`.

Iterate until `check` exits 0 with no errors and no warnings. Notes are advice
and need not be cleared, but say why if you leave one standing. **Apply the
remedy each finding names, literally, before trying anything else** - whether
those remedies actually work is one of the things being measured. Do not open
a browser, and do not render an image in order to look at it.

Render the SVG once it is clean.

## What to record

Append to `examples/gallery/04-immersion/rounds.md` **as you go**, one section per round: the exact
`check` output, and for each finding whether the remedy it named cleared it
when applied literally. Do not write this up at the end from memory.

Write `examples/gallery/04-immersion/findings.md` at the end, covering:

1. **Anything you could not express.** This matters most. Where the schema had
   no way to say something, record what you wanted, what you did instead, and
   how misleading the result is. Do **not** silently substitute something that
   looks similar - if you approximated, say so and say how badly.
2. **Where the documentation failed you** - missing, ambiguous, or wrong.
   Quote the sentence.
3. **What you had to guess at**, and whether the guess turned out right.
4. **Whether `describe` let you confirm the drawing was the one you meant**,
   and what it should have said that it did not.
5. **Features the library lacks**, ranked by what they cost you here.

Be blunt and specific. This is a test of the documentation and the library,
not of you. A clean diagram with an honest list of what it could not say is a
better result than a clean diagram alone.
