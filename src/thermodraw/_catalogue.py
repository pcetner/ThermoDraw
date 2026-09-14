"""Shared scientific notation and interaction help used by the editor and guide."""
import unicodedata
from ._units import catalogue as unit_catalogue

SCIENTIFIC_CHARS = ('ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'
                    'αβγδεζηθικλμνξοπρστυφχψω'
                    '°′″‴·×÷±−≤≥≠≈∞←→↑↓↔'
                    '₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺₋₊')
NAMES = {'·':'multiplication dot','×':'multiplication sign','÷':'division sign',
         '°':'degree','′':'prime','″':'double prime','‴':'triple prime'}
INTERACTIONS = {
    'connection': ('Unconnected endpoint', 'An empty free endpoint has at most one attached path.',
                   'Drag to another node to connect, or click and choose the target.', 'Connectivity'),
    'junction': ('Junction', 'A node joins connection leads.',
                 'Drag to move; drop an empty node exactly onto another node to merge.', 'Geometry and connectivity'),
    'route': ('Route handle', 'A selected path has a geometric waypoint.',
              'Drag to shape the line. A crossing does not connect lines.', 'Geometry'),
    'selection': ('Selection outline', 'One or more components are selected.',
                  'Drag to move the selected objects. Delete removes only the selected objects.', 'Geometry or document contents'),
    'drop': ('Drop preview', 'A palette component or isolated resistance is being dragged onto a target.',
             'Release to commit the shown connection and movement.', 'Geometry and connectivity'),
    'warning': ('Warning', 'A drawing or physics check identifies an issue.',
                'Activate to reveal its component or explanation.', 'Selection only'),
    'group': ('Identical component group', 'Count is greater than one.',
              'Edit Count and Arrangement in a draft, then Apply. Values are per component.', 'Geometry and equivalent physics'),
    'quantity': ('Quantity state', 'Solve physics is open.',
                 'Known is supplied; Unknown is requested; Override is temporary; Calculated is a proposal; Missing needs input.', 'Temporary solve values until explicitly applied'),
}
CONTROLS = {
    'count':'Number of identical components sharing one per-component value. Edit a draft, choose an arrangement, then Apply or Enter. Escape cancels.',
    'arrangement':'Series adds resistances and divides capacitance; parallel divides resistance and adds capacitance. Changes remain a draft until Apply.',
    'symbol-position':'Automatic places the symbol on its route. Manual retains its chosen position. Reset removes the position constraint while preserving authored route points.',
    'angle':'Rotates the symbol and routes its leads to its actual terminal tips. Connectivity and physical values stay unchanged. Undo restores the turn.',
    'from':'The actual start node of this path. Choosing another node changes connectivity; a nearby label does not identify a connection.',
    'to':'The actual end node of this path. Choosing another node changes connectivity. Undo restores the previous end.',
    'id':'Stable technical identifier used by references and physical associations. Renaming remaps supported references.',
    'sub':'A notation subscript that names a place or medium. It is meaningful data and is preserved during a compatible merge.',
    'side':'Preferred side for the label. Automatic lets the label solver choose a clear position. This changes presentation only.',
    'scale':'Actual temperatures use an absolute offset; differences do not. Unspecified retains legacy meaning. For example, 32 °F is 273.15 K, while an 18 °F difference is 10 K.',
    'disconnect-from':'Detach only the start endpoint onto a separate free node. The component survives. Undo restores the connection.',
    'disconnect-to':'Detach only the end endpoint onto a separate free node. The component survives. Undo restores the connection.',
    'disconnect-both':'Detach both ends of this component. Values remain unchanged. Undo restores both connections together.',
    'swap':'Reverse direction by reversing endpoint order and route-point order together. Reversing twice restores the original route.',
    'via-add':'Add a connected junction on a lead. The resistance is retained and the ideal lead is split. Escape cancels; Undo restores the edit.',
    'via-del':'Remove this geometric route point. Connectivity and values remain unchanged. Undo restores the point.',
    'unpin':'Reset symbol position to Automatic without deleting manually authored route points. Undo restores the placement.',
    'delete':'Delete the displayed object. Attached components survive a junction deletion with separate detached ends. Undo restores the operation.',
    'connect':'Choose another node to add a plain ideal connection. No resistance value is introduced. Escape cancels.',
}

def catalogue():
    result=unit_catalogue()
    result['controls']=CONTROLS
    result['symbols']=[{'symbol':c,'name':NAMES.get(c,unicodedata.name(c).lower().replace('greek small letter ','').replace('greek capital letter ','capital ')),
                        'contexts':['label','subscript'],
                        'help':'Insert at the caret or replace selected text. Changes notation only. Undo restores the previous text.'}
                       for c in SCIENTIFIC_CHARS]
    result['interactions']=[{'id':key,'name':v[0],'when':v[1],'action':v[2],'changes':v[3],
                             'cancel':'Escape cancels a gesture or draft; Undo restores a committed edit.'}
                            for key,v in INTERACTIONS.items()]
    return result
