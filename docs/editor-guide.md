# Editor guide

ThermoDraw draws thermal networks and rectangular physical systems with the same Python renderer used by exports. Drawing, checking supplied values and solving selected unknowns are distinct operations.

## Quick start

Quick start is optional, available on an empty drawing or in Help. Back and Next move through four pages: build, edit, check or solve, and export. Close or Escape dismisses it. It does not create a practice file, change your drawing or advance automatically when you edit.

## Find and add components

Open **Components**. Search by name, symbol key or terms such as resistor, boundary and heat input. Search spans all categories; Clear search returns to the selected category. Network contains temperature nodes, thermal resistances, other connections and sources. Physical contains region rectangles, control-volume rectangles, edge surfaces and energy transfers. Annotations contains text, lines and arrows. The question-mark button expands a short definition directly below that component. Click it again to close the definition. Collapse hides the desktop panel; Components reopens it. On narrow screens the library opens in a bottom drawer and closes when a tool is armed.

Click a network component, then click the canvas to place it; alternatively drag it onto the drawing. Enter or Space activates a focused component. Sources attach to highlighted nodes; resistance endpoints attach without body proximity silently merging anything. Drag endpoints, or click an endpoint and then its target. Double-click a node to start a connection. Ordinary empty-space dragging pans; an empty click deselects. Right-click or press `/` outside text fields for Quick add. On touch, hold empty space; movement or pinch cancels the hold.

## Physical geometry and annotations

A region is a material or spatial rectangle, not an energy balance. A control volume is an identified system with a rectangular boundary and explicit region membership. Select a control-volume edge to add a surface; select a surface to add an energy transfer. Missing prerequisites offer the required tool. Heat, work and mass-carried energy are distinct transfer kinds. An annotation arrow explains the picture and does not contribute energy.

Draw rectangles by dragging opposite corners or clicking both corners. Handles preserve rectangular geometry. Lines and arrows use two endpoints. Surface positions are fractions of their owning edge, so resizing or moving the volume keeps surfaces and transfers attached. Drawing width and height are page coordinates, never physical area. Region membership is explicit, not inferred from overlap.

## Edit beside the object

Select an object to open floating properties. Network fields depend on kind: temperature for nodes, resistance for thermal resistances, capacitance for storage symbols, and mass flow plus heat capacity for streams. Endpoint choices show labels and IDs. Connections & presentation contains reference IDs, counts, arrangements, orientation, label sides and route controls where applicable. A supplied resistance-branch heat rate is the **whole repeated group's rate**; resistance value remains per item.

Physical properties show applicable dimensions, owner, edge fractions and physical values. Included regions and descriptive network associations use searchable checkbox lists. Choosing an association to a branch or source without an ID assigns an ID in the same undoable edit. Associations never add balance terms. Energy transfers offer either an energy rate or heat flux times explicit surface area; selecting a new representation clears the old input. Blank values remain unspecified. Explicit zero is meaningful. Geometry validation retains invalid text with an inline explanation instead of changing the document.

Volume generation remains unknown until supplied, including explicit zero. Steady state means zero storage; otherwise enter a signed storage rate, positive for accumulation. The inspector displays supplied-rate balance status and missing terms. Review removed boundary terms before acknowledging an incomplete volume.

## Select, move and arrange

Shift-click adds to selection; Shift-drag empty space selects a group. Shift-select rectangles and drag an edge handle to change all widths or all heights. A region carries owned boundary geometry; associated network objects move only when selected. An isolated resistance moves with its endpoints; connected symbols slide or reroute.

Drag labels to set explicit offsets. Auto position label restores one label; Auto-position all labels clears offsets and forced sides in one undoable action. Deliberately positioned example labels remain editable. Alt bypasses grid/alignment snapping. `[` and `]` rotate selected network components outside text inputs; rectangles remain axis aligned. Escape, pointer cancellation and pinch cancel a drag. Each completed gesture is one undo step.

Ctrl+C/Ctrl+V copy and paste selected objects with fresh IDs and preserved internal relationships; text inputs retain normal clipboard behavior. Deletion removes owned geometry and clears dependent links together. Undo restores the operation.

## Check and solve

Check the numbers evaluates supplied network and volume balances. Solve physics opens a temporary scenario; numeric drawing values start Known. Badges and the separate Values navigator identify Known, Unknown, Override, Missing and Calculated values. Click a badge to cycle supported states, or select a value to edit beside it. Blue means unknown, purple means override, red means invalid or missing, and green means ready or balanced; text also identifies each state.

With zero unknowns, Solve is disabled and Check supplied values remains available. Choose an eligible unknown to calculate. Supported cases include steady-state network temperatures, identifiable positive constant resistances and one energy-balance unknown per control volume. Multiple network unknowns require enough independent equations. Mass flow alone is not an energy rate. No transient integration, material-law derivation or general nonlinear solver is implied.

Temporary inputs and answers appear on the schematic only in Solve mode. Review changes before Apply changes; applying the complete successful scenario is one undo step. Closing a changed calculation asks whether to discard it. Solve settings contain selected systems and time assumptions. A steady-state calculation setting is not automatically a drawn annotation: use Text when the exported figure must state that assumption.

## Files, homework and exports

Files are stored in this browser. Opening an example creates a copy; updating the library never replaces existing saved drawings. The Example menu contains only HW2 1.44, 1.51, 1.57a and 1.60a. See [homework guide](example-guide.md) for supplied values, rounding and limitations.

Export offers tightly cropped light SVG and PNG for documents, JSON for an editable copy, and interactive HTML. Export excludes selection, solve badges and temporary values; apply a reviewed scenario first if it should become the drawing. Share links carry diagram data. Present hides editor controls; Escape returns. Fit to screen includes the complete drawing.

## Related references

- [Schema](schema.md): fields, units, validation and serialization.
- [Physics analysis](physics-analysis.md): equations, unknowns, tolerances, Python and CLI APIs.
- [Stability](stability.md): compatibility guarantees.
