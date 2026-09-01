# Rounds — 05-laser-diode

Worked from `docs/schema.md` and the brief only.

## Round 1

First draft. Main chain left to right at y=150 (junction, AuSn solder, CuW
submount, submount base, cooler body, coolant water), TEC hot face and ambient
on a second row at y=460. No rail — the model is steady state and has no
capacitances, so the `rail` key was omitted entirely.

```
examples/gallery/05-laser-diode/diode.json: 19 labels placed, 1 error, 2 warnings, 0 notes
error: [symbols-overlap] source 3 -> tech and source 4 -> tech overlap by 2  -> move one of them with `at`
warning: [label-adrift] node 'j': its label was pushed 36 past its own clearance to get around source 0 -> j and now sits nearer that than the thing it names  -> move source 0 -> j further from its node with `at`, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
warning: [label-adrift] node 'tech': its label was pushed 56 past its own clearance to get around source 3 -> tech and now sits nearer that than the thing it names  -> move source 3 -> tech further from its node with `at`, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
EXIT=1
```

Label count 19 matched what I could count from the file (8 nodes + 6 branches
+ 5 sources), so nothing was dropped.

Remedies applied literally:

- `symbols-overlap` — "move one of them with `at`": gave source 3 (`flow` into
  `tech`) `at: [1240, 300]` and source 4 (`diss` into `tech`) `at: [1010, 460]`.
- `label-adrift` on `j` — "move source 0 -> j further from its node with `at`":
  gave source 0 `at: [40, 150]`.
- `label-adrift` on `tech` — "move source 3 -> tech further from its node with
  `at`": same edit as the overlap fix above.

## Round 2

```
examples/gallery/05-laser-diode/diode.json: 19 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

All three remedies cleared their finding on the first try, applied literally
and with no other change:

| finding | remedy as given | worked literally? |
|---|---|---|
| `symbols-overlap` source 3 / source 4 | "move one of them with `at`" | yes — moved both, cleared |
| `label-adrift` node `j` | "move source 0 -> j further from its node with `at`" | yes — `at: [40, 150]`, cleared |
| `label-adrift` node `tech` | "move source 3 -> tech further from its node with `at`" | yes — `at: [1240, 300]`, cleared |

`check` was clean here, but `describe` was not what I meant. The intermediate
node between the spreading resistance and the indium layer has no temperature
in the brief, so I gave it a `label` and no `sub`/`value`. `describe` showed:

```
  node 'smb'             node            (980, 150)        above          83x33   Submount base | T
```

A bare, dangling `T` with no subscript and no value. `check` does not consider
that a finding — it is a well-formed label, it just says nothing. Removing the
`label` as well does not help; the node still prints a lone `T`, 7x17:

```
  node 'smb'             node            (980, 150)        above           7x17   T
```

There is no way in the schema to have an interior `free` node that is named
but carries no temperature. Only a `break` node gets "the label alone drawn",
and a `break` draws a boundary wall, which this is not.

## Round 3

Changed `smb` to `"kind": "corner"`, which draws nothing and routes the wire.
That drops the name "Submount base" from the drawing but avoids printing a
stray `T` and avoids inventing a temperature the brief does not give.
(Computing one from the brief's own numbers gives 51 - 80x0.15 = 39 degC,
which is *below* the cooler body at 41 degC, so the brief's numbers do not
close and inventing the value would have been worse than omitting it.)

```
examples/gallery/05-laser-diode/diode.json: 18 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

18 = 7 non-corner nodes + 6 branches + 5 sources. Matches the file.

No notes left standing. `describe` confirms every label reads as intended and
that there is no wire between the cooler body and the TEC hot face, which is
the point of drawing the TEC as two `flow` annotations rather than a branch.

Rendered:

```
PYTHONPATH=src python -m thermodraw render examples/gallery/05-laser-diode/diode.json -o examples/gallery/05-laser-diode/diode.svg
```
