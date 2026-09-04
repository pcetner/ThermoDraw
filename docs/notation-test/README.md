# The notation test

The library draws resistances as textured boxes rather than circuit zigzags.
That is its most load-bearing choice, and the reason recorded for it is a
claim about readers that no reader has been asked about: at the size a
diagram has on a slide or in a printed appendix, a hatched box still says
*solid* and streamlines still say *fluid*, while a zigzag with an unreadable
`R_conv` subscript says only "some resistance".

This directory is the test. It takes one person and two minutes.

## What is here

- `boxes.svg` — the README's hero diagram, as the library draws it.
- `zigzags.svg` — the same network with the four resistance boxes replaced by
  circuit-notation zigzags, and **nothing else changed**: same coordinates,
  same label solver, same text in the same places, same embedded font. The
  glyph is the only variable.
- `make.py` — regenerates both from `examples/hero.json`.

## How to run it

1. Find one thermal engineer who has never seen this library.
2. Show them **one** of the two files at slide size — about 320 px wide on a
   screen, or printed at a third of a page. Do not let them zoom.
3. Ask: *"Which path is convection? Which is radiation? Which is a contact?"*
   Note whether they answer from the picture or have to read the labels, and
   roughly how long each answer takes.
4. Show them the other file and ask the same three questions.
5. Alternate which file goes first if you can find a second person.

## What the answers mean

If the boxes are read from the picture and the zigzags are read from the
labels, the bet holds: the texture buys legibility where the subscript fails,
and the notation stays. Write the result into `docs/design-record.md` under
*Boxes, not zigzags*, and change the word **bet** in `CLAUDE.md` to what it
turned out to be.

If both are read from the labels — or the zigzags are read faster because the
reader already knew them — the recorded reason for the notation is gone, and
what is left is that boxes have room for a texture, which is an argument about
drawing. That does not mean the notation changes tomorrow; it means the
decision is recorded as a preference, and the record says so.

Either answer is worth more than the current one, which is a guess.

## Since 1.0

Zigzags are an option in the library itself — `render(...,
notation="zigzags")`, `Diagram.svg(notation="zigzags")`, `thermodraw render
--notation zigzags` — drawn with the glyph `make.py` uses here, so a reader
who prefers circuit notation is not waiting on this test. What the test
still decides is the *default*. Boxes are the default on the reader's reason
above, and nobody has asked a reader.
