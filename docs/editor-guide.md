# Editor guide

ThermoDraw draws thermal networks and rectangular physical systems with the same Python renderer used by exports. Drawing, checking supplied values and solving selected unknowns are distinct operations.

## Quick start

Quick start is available through Help → Editor guide. Five short sections cover Add, Connect, Enter values, Solve and Export. Close or Escape dismisses it without changing the drawing. The separate Keyboard shortcuts dialog groups editing, navigation and connection shortcuts.

## Find and add components

Open **Components**. Search by name, symbol key or terms such as resistor, boundary and heat input. Search spans all categories; Clear search returns to the selected category. Network contains temperature nodes, thermal resistances, other connections and sources. Physical contains region rectangles, control-volume rectangles, edge surfaces and energy transfers. Annotations contains text, lines and arrows. The question-mark button expands a short definition directly below that component. Click it again to close the definition. Collapse hides the desktop panel; Components reopens it. On narrow screens the library opens in an overlay panel and closes when a tool is armed.

Click a network component, then click the canvas to place it; alternatively drag it onto the drawing. Enter or Space activates a focused component. Sources attach to highlighted nodes; resistance endpoints attach without body proximity silently merging anything. Drag endpoints, or click an endpoint and then its target. Double-click a node to start a connection. Ordinary empty-space dragging pans; an empty click deselects. Right-click or press `/` outside text fields for Quick add. On touch, hold empty space; movement or pinch cancels the hold.

## Physical geometry and annotations

A region is a material or spatial rectangle, not an energy balance. A control volume is an identified system with a rectangular boundary and explicit region membership. Select a control-volume edge to add a surface; select a surface to add an energy transfer. Missing prerequisites offer the required tool. Heat, work and mass-carried energy are distinct transfer kinds. An annotation arrow explains the picture and does not contribute energy.

Draw rectangles by dragging opposite corners or clicking both corners. Handles preserve rectangular geometry. Lines and arrows use two endpoints. Surface positions are fractions of their owning edge, so resizing or moving the volume keeps surfaces and transfers attached. Drawing width and height are page coordinates, never physical area. Region membership is explicit, not inferred from overlap.

## Edit in the Properties panel

Select an object to open the docked Properties panel. Network fields depend on kind: temperature for nodes, resistance for thermal resistances, capacitance for storage symbols, and mass flow plus heat capacity for streams. Endpoint choices show the actual endpoint’s readable name. Connections and Appearance have their own tabs; technical identifiers live in Advanced. Use Disconnect start/end/both to detach a component without deleting it. Reverse direction reverses endpoints and route points together. Symbol position offers Automatic/Manual and Reset position, preserving manual routing. A supplied resistance-branch heat rate is the **whole repeated group's rate**; resistance value remains per item.

Physical properties show applicable dimensions, owner, edge fractions and physical values. Included regions and descriptive network associations use searchable checkbox lists. Choosing an association to a branch or source without an ID assigns an ID in the same undoable edit. Associations never add balance terms. Energy transfers offer either an energy rate or heat flux times explicit surface area; selecting a new representation clears the old input. Blank values remain unspecified. Explicit zero is meaningful. Geometry validation retains invalid text with an inline explanation instead of changing the document.

Volume generation remains unknown until supplied, including explicit zero. Steady state means zero storage; otherwise enter a signed storage rate, positive for accumulation. The inspector displays supplied-rate balance status and missing terms. Review removed boundary terms before acknowledging an incomplete volume.

## Select, move and arrange

Shift-click adds to selection; Shift-drag empty space selects a group. Shift-select rectangles and drag an edge handle to change all widths or all heights. A region carries owned boundary geometry; associated network objects move only when selected. An isolated resistance moves with its endpoints; connected symbols slide or reroute.

Drag labels to set explicit offsets. Auto position label restores one label; Auto-position all labels clears offsets and forced sides in one undoable action. Deliberately positioned example labels remain editable. Alt bypasses grid/alignment snapping. `[` and `]` rotate selected network components outside text inputs; rectangles remain axis aligned. Escape, pointer cancellation and pinch cancel a drag. Each completed gesture is one undo step.

Ctrl+C/Ctrl+V copy and paste selected objects with fresh IDs and preserved internal relationships; text inputs retain normal clipboard behavior. Delete removes selected objects only. Deleting a junction preserves attached components, giving their ends separate detached nodes. Deleting an isolated resistance cleans its now-unused empty endpoints; meaningful nodes survive. Undo restores the entire operation.

## Check and solve

Solve → Check supplied values evaluates supplied network and volume balances. Warnings in the fixed-height bottom strip select and reveal their targets; details overlay the canvas without resizing it. Solve physics opens a temporary scenario; numeric drawing values start Known. Badges and the separate Values navigator identify Known, Unknown, Override, Missing and Calculated values. Click a badge to cycle supported states, or select a value to edit beside it. Blue means unknown, purple means override, red means invalid or missing, and green means ready or balanced; text also identifies each state.

With zero unknowns, Solve is disabled and Check supplied values remains available. Choose an eligible unknown to calculate. Supported cases include steady-state network temperatures, identifiable positive constant resistances and one energy-balance unknown per control volume. Multiple network unknowns require enough independent equations. Mass flow alone is not an energy rate. No transient integration, material-law derivation or general nonlinear solver is implied.

Temporary inputs and answers appear on the schematic only in Solve mode. Review changes before Apply changes; applying the complete successful scenario is one undo step. Clicking Solve physics again uses the same close action as Close. Closing a changed calculation asks whether to discard it. Ideal-connected nodes share one temperature control; conflicting values remain explicit errors. Solve settings contain selected systems and time assumptions. A steady-state calculation setting is not automatically a drawn annotation: use Text when the exported figure must state that assumption.

## Files, homework and exports

Files are stored in this browser. Opening an example creates a copy; updating the library never replaces existing saved drawings. The Examples section at the bottom of Files contains only HW2 1.44, 1.51, 1.57a and 1.60a. See [homework guide](example-guide.md) for supplied values, rounding and limitations.

File → Export opens a centered dialog with Image for documents, HTML page with controls, and JSON, the raw diagram data. Image options separate SVG/PNG format, theme and resolution; the preview uses the exported presentation settings. Export excludes selection, solve badges and temporary values; apply a reviewed scenario first if it should become the drawing. Share links carry diagram data. Present hides editor controls; Escape returns. Fit to screen includes the complete drawing.

## Related references

- [Schema](schema.md): fields, units, validation and serialization.
- [Physics analysis](physics-analysis.md): equations, unknowns, tolerances, Python and CLI APIs.
- [Stability](stability.md): compatibility guarantees.


## Junctions and insertion

Dropping an empty, unlabeled free node exactly onto another node removes the
empty node and transfers its connections. The target keeps its identity and
properties. Near overlap alone does not merge. Alt bypasses snapping, but an
actual exact overlap still merges. Temperatures, subscripts and metadata are
meaningful: conflicting information requires explicit review. A merge that
short-circuits a physical resistance is refused. Compatible exact overlaps are
normalized once on import or first opening a legacy file; Undo retains the
original imported topology.

Drop a free node onto a connection lead, or choose Add junction and click a
lead, to split the ideal connection while retaining the original resistance.
A degree-two ideal junction can serve as a corner without a separate temperature
unknown. Drag a line or its square route handles to shape geometry. Crossings
alone never create connections.

Drop a resistance onto a lead to insert in series; drop onto a resistance body
to add a separate parallel branch with the same external nodes. Dropping on a
parallel group's shared terminal lead inserts one resistance in series with
the whole group, expanding space for it. The preview identifies the shared
lead; unrelated crossing lines still require choosing a connection. A new palette
resistance has no invented value. Moving an isolated resistance retains its
value. Thus 10 K/W and 20 K/W remain separate values and together present
approximately 6.667 K/W in parallel. Insertion can expand the drawing; Undo
restores both insertion and moved coordinates. Removing a part does not compact
it automatically.

## Count and Arrangement

Count means identical components sharing one per-component value. A counted
group has only two external endpoints; independently valued or tapped parts
must be separate branches. Count starts at 1. Changing 1 to a larger integer
requires choosing Series or Parallel. Subsequent count edits retain the chosen
arrangement. Count and Arrangement change a draft preview, never the document
per keystroke. Apply or Enter validates and commits one Undo transaction.
Escape or Cancel discards it. Switching selection or files offers Apply,
Discard, or Keep editing. Invalid input cannot commit. Repeated preview changes
always start from the committed drawing, avoiding cumulative movement.

Returning to 1 removes stored Count/Arrangement fields and preserves the
per-component value. Series resistance is N×R and parallel resistance is R/N;
capacitance uses C/N and N×C respectively. Missing or symbolic values do not
produce invented numeric equivalents. An unchanged draft adds no Undo entry.

## Units and scientific notation

Units remains directly visible in the toolbar. Choose °C, °F or K for
temperature and use the contextual picker for compound units, symbols and all
SI prefixes. Prefix explanations include the name and power of ten. Picker
insertion replaces the selection or inserts at the caret; prefix application
targets one unit token. Inputs still accept Unicode and supported typed aliases.
The shared catalogue defines supported scientific symbols; it does not claim
to enumerate Unicode.

Automatic prefixes uses engineering powers of three and preserves the selected
temperature unit. SI units + scientific notation displays Kelvin and unprefixed
SI units. Drawings show six significant digits; editing retains full precision.
Changing display mode never parses a rounded label back into saved data.
Advanced temperature settings distinguish actual temperature from a difference.
View → Advanced layout contains the reference rail and Place unplaced nodes.
The rail is a shared reference-temperature line using its reference node.

## Menus and panels

File contains New, Import JSON, Rename, Duplicate, Export and Copy share link.
Examples appear at the bottom of the Files panel and open as independent copies.
Copy, Paste, Delete selection and Merge selected nodes are toolbar icons beside
Undo/Redo, with accessible names and shortcut tooltips. View contains Fit, Present,
Theme, Resistance notation, Auto-position labels, panel visibility and Advanced
layout. Components, Properties and Solve are permanent views of the right panel;
Solve includes Check supplied values. Help contains a five-step Quick start and a separate Keyboard shortcuts dialog.
The Quick start links to this full guide.
Diagram name, Undo, Redo and Units remain visible, including narrow layouts.

Files automatically measures title widths using the rendered font. Its width
is capped by 640 pixels, 40% of the viewport, and the space remaining for the
right panel and a 480-pixel canvas. Longer names wrap fully. Manual resizing
persists until Reset to automatic. When space is insufficient, Files opens as
an overlay. Each side panel has its own collapse control and labeled reopening
control in the reserved canvas header. Rename accepts Enter; Escape cancels and blank names show an inline error.
Fit cancels the current gesture and residual wheel events until 150 ms of wheel
inactivity. Present uses the full viewport and restores the editing state.

The maintained [interaction legend](editor-interactions.md) is generated from
the same catalogue used for in-editor help and accessibility descriptions.

## Properties panel

Selecting an object opens Properties in the right panel. Components returns to the
library without clearing selection; Close properties clears selection. When a
Solve session is open, Solve, Properties and Components share that panel without
applying or discarding the session. At narrow widths, properties use a bottom sheet.

Properties contains values and Count/Arrangement; Connections contains endpoints,
disconnection and Add junction; Appearance contains rotation and label placement.
Legacy route coordinates and technical identifiers are under Advanced. Count edits
remain a draft across tabs. Apply commits once, Cancel restores the document, and
leaving the object offers Apply, Discard or Keep editing. Each tab has concise Help;
field labels also provide focus and hover explanations.

## Reading issues

The fixed status strip separates Errors, Warnings and Suggestions from physics-check
status. Click its sentence to select the affected objects and open the explanation
in one action. All issues opens the complete list without resizing the drawing.
Issue explanations name the affected objects; raw checker text is under Technical
details. Background updates preserve the selected issue while it still exists.

Sharing a label side is not itself a collision, so the editor omits that stylistic
checker suggestion. Actual collisions and clearance problems remain actionable.
The Python checker retains its existing output.

## Menu navigation

Theme, notation and panel settings stay open while you adjust them. Commands close
their menu. Arrow keys navigate menu rows and categories; Enter or Space activates,
and Escape dismisses the menu and returns focus. Undo and Redo use arrow icons with
accessible names and platform-specific shortcut tooltips. Keyboard shortcuts lists
the same maintained bindings used by the editor; typing in fields remains protected.

Dragging a horizontal or vertical resistance lane keeps square corners by default.
The lane moves between its existing risers while endpoint nodes and their straight
connection leads remain in place. Sliding along the lane preserves terminal clearance;
explicitly diagonal routes retain their existing direction. Undo restores the full route.

The Components panel scrolls independently to expose the full catalogue. Preview
images use a larger 104-by-58-pixel area. Keyboard shortcuts closes with the X
in its upper-right corner or Escape. Pointer actions do not add a focus border
to the drawing; keyboard navigation retains a subtle focus indicator.
