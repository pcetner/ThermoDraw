> Historical delivery snapshot. For current controls use [the editor guide](editor-guide.md) and the latest Unreleased changelog.

# Functional editor delivery

## Reliability

The editor keeps committed data separate from gesture previews. A completed drag makes one undo entry; cancellation, Escape, pinch, export and file switching restore committed state. Document generations and edit revisions reject late scene and solve responses, including after undo. Missing coordinates merge by node ID into their originating revision. Python supplies symbol geometry and label anchors for animation-frame previews, and the checker reuses the composed scene.

Alignment acquires within 12 screen pixels and releases beyond 20. Branch detours enter beyond 40 and return below 28. Thresholds use the SVG screen transform, including letterboxed views. Alt bypasses alignment and grid snapping. Unrelated labels stay at their existing anchors until release.

## Interaction

Palette items support drag/drop and click-to-place. Sources attach directly to highlighted nodes; paths attach at endpoints. Endpoint handles support dragging and clicking a target. Isolated paths move with their nodes. Shift-click and Shift-marquee select groups; group movement carries internal routes and source offsets. Labels have persistent offsets with an Auto position reset. Brackets remain normal text inside inputs.

Export → Preview for document shows a cropped light figure and offers SVG or PNG. The image isolates exported colors from editor styles. Sketch is available beside Components on desktop and in the overflow menu at narrow widths. Quick-add opens intentionally with right-click, `/`, or a cancellable touch hold. Ordinary empty clicks deselect. Ctrl+C/Ctrl+V duplicate selections, including dependent endpoint nodes and physical boundaries, with new IDs and a single undo step. Text fields retain native clipboard behavior. Help and the existing tour describe the workflows.

## Rectangular modeling

Regions and control-volume outlines are axis-aligned rectangles. Opposite-corner drawing works in all four directions, and corner handles preserve rectangular geometry. Edge-relative surfaces and their transfers follow volume movement and resizing. Explicit region membership and descriptive network links do not infer physical area or add energy terms.

The additive Python/JSON/builder model includes regions, control volumes, control surfaces, supplied energy transfers and independent text/line/arrow annotations. Physical-only drawings bypass network layout. Supplied-rate checks handle heat, work, mass-carried energy, flux times explicit area, generation and signed storage. Missing terms remain unchecked; deleting boundary terms marks the affected balance incomplete. See [schema](schema.md).

## Review and verification

Initial milestone verification: **1,022 tests passed**, with no skips. This includes the browser, compatibility, golden and font checks. `mypy --check-untyped-defs`, both generated-document checks, the site build, and wheel/source-package builds also passed.

The four [homework examples](../examples/homework/README.md) are available in the editor’s Example menu. Each round-trips and passes physics checking without findings. They cover the oven, frost/air, wall cross-section with its network, and hot plate.

Browser coverage includes delayed scene/solve responses, undo, cancellation, pinch interruption, stationary labels, zoom-dependent snapping, detour hysteresis, endpoint attachment, group translation, rectangular drawing/resizing and narrow export controls. Python coverage includes validation, references, serialization, rendering, balances, units and legacy semantics. Existing golden images were not changed.

The existing site CSS, thermal symbol definitions and typography are unchanged. The only added editor CSS sizes the new Sketch button inside the existing heading row. Desktop and narrow screenshots and example/export captures are available locally in `out/review/`. Site builds use isolated package build directories and content-addressed library assets to prevent stale wheels and build interference.

The locally reviewable site is `site/editor/index.html`, served at `http://127.0.0.1:8765/editor/` during this delivery. Publishing and deployment are separate actions.

Follow-up interaction verification: **30 browser tests passed**, covering intentional quick-add, native text clipboard behavior, diagram copy/paste, shared width/height resizing, minimum sizes and cancellation. The local site was rebuilt and refreshed.
