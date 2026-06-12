# TunnelMap

an isometric octolinear transit map editor for zines, ttrpg world-building,
and anyone who likes the harry beck / maxwell roberts approach to drawing
underground systems.

it's a single html file. open it in any modern browser. no build, no install,
no server. draw lines, stack planes, export print-ready svg.

<img width="2047" height="988" alt="image" src="https://github.com/user-attachments/assets/07f05c32-2d2d-45f5-b935-e4f1a8476b02" />

## try it

[hed0rah.github.io/tunnelmap](https://hed0rah.github.io/tunnelmap)

or clone this repo and double-click `index.html`.

## what it does

- **octolinear drawing** with eight-direction snap and shared-corridor
  parallel offsetting so two lines running side-by-side don't overlap
- **stacked planes** (up to six) with smooth z-stagger and lifts between them
- **station markers** in twelve kinds — regular, terminal, interchange, bend,
  depot, maintenance bay, abandoned, under-construction, signal yard,
  control tower, platform, junction switch — plus eleven shape variants
  including merged interchange pills that auto-orient to the dominant
  flow direction
- **four service states** per line or per segment: active, reduced,
  maintenance tunnel, abandoned. mark a single segment as maintenance and
  it renders thin and dash-dotted while the rest of the line stays normal
- **three render modes** in svg export:
  - **color** — your chosen line colors with per-line style (solid, dashed,
    dotted, double, thin, thick)
  - **mono** — pure black on white, lines differentiated by dash patterns
    only. for one-color zine print
  - **grey** — varied grey shades with hatch patterns (45° diagonals,
    bayer dither, brick, checker, stipple, dots) on each line. for
    two-tone zine print
- **ten color themes** — cool grey (default), paper, bone, beige, sepia,
  blueprint, dark, Outrun (80s neon), Kill ENGN (deep teal), Grivt
  (industrial weathered)
- **eight view angle presets** — four isometric corners (NE/NW/SE/SW), flat
  top-down, flat 45°, military projection, cabinet projection
- **three curve modes** per line — fillet (quadratic bezier corners),
  spline (catmull-rom through all waypoints), sharp (no smoothing)
- **legend block** auto-generated from line styles, opt-in, four-corner
  placement
- **auto-quadrant station labels** — places each name in the freest of
  eight directions around its marker, with collision avoidance against
  lines and other labels
- **map notes** — free-floating italic annotations pinned to grid cells.
  right-click an empty cell to add one; click edits, drag moves,
  right-click sizes or deletes. exported in the theme's soft ink
- **walking transfers** — lift mode also connects two same-plane
  stations with a dashed transfer link
- **multi-select** waypoints with marquee or shift-click. rotate 90°,
  mirror horizontally/vertically, straighten — operates on selection or
  active line
- **right-click context menus** on waypoints, lines, lifts, and empty
  plane cells. all line-level options reachable by right-clicking the
  line itself
- **live svg preview** pane with view-angle and color-mode pickers
- **json save/load** round-trips the full map state, the legend config,
  the theme, and the camera
- **autosave** — the working map is kept in localStorage and restored
  on next open. save json is still the durable path
- **png export** — the current color mode rasterized at 2x, for places
  svg won't paste

## drawing controls

| action | keys / mouse |
|---|---|
| switch mode | `e` edit (default), `d` draw, `l` lift |
| switch active plane | `1`–`6` or `[` / `]` for prev/next |
| flip line direction | `tab` |
| undo / redo | `cmd+z` / `cmd+shift+z` |
| pan | shift+drag, alt+drag, or middle-click drag |
| zoom | wheel |
| context menu | right-click |
| rotate selection 90° | `r` (shift+r for ccw) |
| mirror selection | `h` (horizontal), `v` (vertical) |
| straighten active line | `\` |
| add waypoint to selection | shift+click |

## what to draw

the editor is opinionated toward subway-style transit diagrams: clean
straight lines at 45° increments, stacked underground tiers, marked
interchanges. it works fine for:

- fictional cy city undergrounds
- ttrpg dungeon transit / metro hubs
- abstracted museum or campus wayfinding
- punk-zine maps of imaginary places
- the actual stockholm metro

it works less well for:

- street-level road maps with organic curves (use the spline curve mode
  but expect to wrestle)
- truly geographic / scaled maps — coordinates here are grid units, not
  meters

## architecture

the entire editor lives in `index.html`. three.js handles the 2.5d
canvas and orbit camera; everything else is vanilla js with no
dependencies beyond the cdn import of three.

the svg export uses the same projection math as the python reference in
`reference/transit_map.py`. that file is the authoritative spec for the
projection geometry and was the original generator before the browser
editor existed. if anything ever diverges, the python is correct.

the data model is described in `docs/data-model.md`. it's small and
should round-trip through any saved json regardless of editor version.

## origin

the project started as a python script for generating cyberpunk-zine
metro diagrams of fictional cities. the python is in
`reference/transit_map.py`. the browser editor grew out of wanting to
draw maps interactively instead of editing the python's data tables and
re-running.

it's named tunnelmap because every map worth drawing in this style is
about what's under the surface.

## license

MIT. do whatever, but a credit is nice if you build something on it.
