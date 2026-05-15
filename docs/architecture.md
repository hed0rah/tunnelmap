# architecture

a brief on how the editor is put together. for anyone wanting to hack
on `index.html` directly.

## one file, three layers

everything is in `index.html`. the file is conceptually three layers
stacked:

```
+-----------------------------+
|  ui chrome (sidebar, popover, contextmenu, preview pane)
|  vanilla js manipulating dom
+-----------------------------+
|  scene / interaction (three.js, raycaster, orbit camera)
|  picks waypoints and lines from screen coords
+-----------------------------+
|  data + math (vanilla js)
|  the projection, octolinear snap, corridor offsets, smoothing,
|  catmull-rom, label placement, svg export
+-----------------------------+
```

state lives in a single top-level `data` object. mutations flow
through helper functions that call `rebuildAll()` (or a more targeted
`rebuildLines()` / `rebuildStations()` / `refreshPreview()`). there is
no command pattern or store — undo/redo works by polling
`JSON.stringify(data)` every 350ms and pushing changes onto a stack.
brutally simple, works fine for editor scale.

## projection

the iso math is a 2x2 matrix and an integer grid rotation. the default
"isometric NE" preset uses:

```
screen_x = (gx - gy) * cos(30°) * GRID
screen_y = (gx + gy) * sin(30°) * GRID - plane.z * PG_PX
```

each view preset declares its own matrix in
`VIEW_PRESETS` inside the `exportSvg` function. they are pure
post-processing on grid coords — the underlying data is identical
regardless of which view the user picks. only the svg export and the
live preview honor `data.viewPreset`; the 3d editor stays in canonical
iso NE so editing stays consistent.

## corridor model

two lines that travel the same edge get parallel-offset perpendicular
to the corridor. `buildCorridors()` walks every consecutive waypoint
pair, canonicalizes the endpoints (sorts them so two lines going
opposite directions still share a corridor), and assigns each line a
slot index. `waypointOffset(line, i, corridors)` averages the offsets
of the two adjacent segments at each waypoint so the parallel tracks
turn smoothly at corners.

`wp.offsetBias` is added on top of the auto-offset — a manual nudge
when the auto-router crowds too tight in a specific spot.

## smoothing

three curve modes, all implemented in 2d on the projected screen
coordinates:

- **fillet** — quadratic-bezier corner fillets via
  `smoothCorners` (3d) and `smoothCornersFlat` (2d). per-waypoint
  radius via `wp.cornerRadius`, falls back to the line's `smoothRadius`,
  falls back to a constant.
- **spline** — centripetal catmull-rom (alpha=0.5) through every
  waypoint. virtual endpoints are reflected across the first/last
  waypoints to avoid the t1==t0 division-by-zero that coincident
  endpoints produce.
- **sharp** — no smoothing, raw straight segments.

## hatch patterns (grey mode)

grey mode emits `<pattern>` defs in the svg and uses them as the stroke
paint server. the line is rendered as a layered sandwich:
1. paper-colored casing (wide)
2. solid grey shade (the line's identity color in grey mode)
3. hatch pattern overlay at slightly narrower width

eleven patterns are defined: diag45, diag135, cross-hatch, dense dots,
sparse stipple, bayer-50 ordered dither, brick, checker, vertical
stripes, horizontal stripes, plus a "solid" entry for completeness.
each line in grey mode rotates through them, indexed by line position
unless `line.greyStyle` overrides.

## station shapes

twelve `kind` values, but rendering branches on either `kind` (special
function-indicating glyphs like depot / maintenance / abandoned /
construction / signal_yard / control_tower / platform / junction) or
`shape` (decorative glyph for normal/terminal/interchange/bend stations:
circle, square, diamond, triangle, plus, ring, pill, pill_v, stadium,
hex, cluster).

oriented shapes (pill, stadium, hex, cluster, depot, signal_yard,
platform, junction) read each station's dominant incoming-line angle
via `stationDominantAngle(k)` and rotate to match. the angle is the
bidirectional mean of all adjacent line tangents, computed via the
doubled-angle trick (`atan2(Σ sin 2a, Σ cos 2a) / 2`) so opposing exits
don't cancel.

## label placement

for each named station, `placeLabel` examines eight candidate
positions (N, S, E, W, four diagonals) around the marker. each
candidate's approximate bounding box is sampled against every line
segment and every already-placed label, and the candidate with the
largest minimum clearance wins. a small bias toward east preserves the
old default when scores tie.

## undo

a snapshot of `JSON.stringify(data)` is pushed every 350ms when the
serialization changes. `cmd+z` pops the most recent snapshot back. the
redo stack grows when undo pops, clears on the next mutation. memory
overhead is trivial for editor-scale data.

## save / load

`save json` button stuffs the current state (plus camera) into a blob
download. `load json` reads the file and replaces `data`. theme and
view-preset round-trip through the json. there's also an automatic
`localStorage` autosave that's commented out / not implemented in this
version — could be added in 20 lines.

## the python reference

`reference/transit_map.py` was the original generator. it's still the
authoritative spec for the projection. the editor's svg export was
written to produce visually-equivalent output. if anything ever
diverges, the python is correct. that file also has features the
editor doesn't yet, like more sophisticated label placement annealing,
that could be ported back over time.
