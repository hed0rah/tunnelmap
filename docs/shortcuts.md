# shortcuts

a single-page reference for every key, mouse, and modifier the editor
understands. it's also shown in compressed form inside the sidebar.

## modes

three modes only. most interaction is direct manipulation that works
regardless of mode.

| key | mode | what it changes |
|---|---|---|
| `e` | edit (default) | click selects, drag moves, drag-empty marquees |
| `d` | draw | click empty extends the active line |
| `l` | lift | two waypoint clicks (different planes) create a lift |

old `b`/`m`/`x`/`s` keys silently route to edit mode now — kept as
muscle-memory back-compat.

## core gestures (work in any mode)

| input | action |
|---|---|
| click waypoint | select + make line active |
| click tube | select that line + make active |
| click empty (different plane) | switch active plane to that one |
| click empty (same plane) | marquee on drag, deselect on no-drag |
| drag waypoint | move along grid with octolinear snap |
| shift+drag waypoint | move between planes (drag onto another plane mesh) |
| drag from empty | marquee select waypoints |
| double-click waypoint | open the station popover |
| double-click tube | insert a bend at cursor (was the old bend mode) |
| double-click empty | start a new line + drop into draw mode |
| right-click target | context menu for waypoint / line / lift |
| right-click empty | deselect everything (no menu) |
| delete / backspace | delete selected waypoints |

## draw mode modifiers

| input | action |
|---|---|
| `shift`+click | drop new waypoint without octolinear snap (raw cell) |
| `ctrl`/`cmd`+click | drop on whichever plane the cursor ray hits (also switches activePlane to that one) |
| double-click waypoint | activate the line that owns this waypoint and orient it so subsequent clicks extend from this point. flips the line array if the clicked wp was at index 0. never creates a new line; use the right-click "start new line from here" / "branch from here" for explicit branching |

## planes

| key | action |
|---|---|
| `1` … `6` | switch active plane to that index |
| `[` | switch to previous plane (wraps) |
| `]` | switch to next plane (wraps) |

## active-line operations

| key | action |
|---|---|
| `tab` | reverse the active line's waypoint order |
| `\` | straighten — re-snap every waypoint of the active line to octolinear axes |
| `esc` | priority cancel: pending lift → close popover → clear selection → pop last waypoint |

## selection transforms

these act on the current multi-selection, or fall back to the active
line's full waypoint list if nothing is selected.

| key | action |
|---|---|
| `r` | rotate 90° clockwise around centroid |
| `shift+r` | rotate 90° counter-clockwise |
| `h` | mirror horizontally |
| `v` | mirror vertically |
| `delete` / `backspace` | remove the selected waypoints |

## history

| keys | action |
|---|---|
| `cmd+z` / `ctrl+z` | undo last change |
| `cmd+shift+z` / `ctrl+shift+z` | redo |

undo snapshots are taken automatically every 350ms when anything
changes.

## mouse and camera

| input | action |
|---|---|
| left-click | mode-dependent action (draw, bend, move, etc.) |
| right-click | context menu — different items depending on what was clicked (waypoint, line body, lift, empty plane cell) |
| middle-click drag | pan |
| shift+drag | pan |
| alt+drag (left or right) | pan |
| wheel scroll | zoom |
| shift+click waypoint (select mode) | add/remove from selection without opening the popover |
| shift+marquee | union marquee hits with existing selection |

drag-to-move also works on existing waypoints while in draw or bend
mode — start the press on a sphere and the editor switches to drag once
you move more than four pixels. release without moving and the normal
mode click happens instead.

## right-click menu

the menu rebuilds on every right-click based on what's under the
cursor.

**on a waypoint:** open station info, set active line, flip line
direction, straighten line, mark next segment abandoned, mark next
segment as maintenance tunnel, cycle line service state, start new
line from here, branch from here (inherits color and style), delete
waypoint.

**on a line body (between waypoints):** set active, rename, change
color, cycle style, cycle curve mode, cycle service state, flip,
straighten, delete line.

**on a lift:** delete lift.

**on empty plane:** start new line here, switch active plane to this
one. if the click is near an existing segment, also "insert bend here
on \<line\>".

## sidebar shortcuts

a compressed version of this reference is in the bottom of the sidebar
under "shortcuts". the right-click menu lists are not duplicated there;
the menu items vary too much by context to fit.
