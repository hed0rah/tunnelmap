# tunnelmap internals

internal-records doc. dense, opinionated, written for future-you when
something breaks at 2am or you want to remember why a decision was made.

## why single-file html

every alternative shape was tried first or considered. a Python script
existed (`reference/transit_map.py`) — fine for batch generation, painful
for iterative design. a Svelte + Konva + Vite + TypeScript project was
scaffolded with `core/` algorithms and `editor/` components — clean
architecture, but every feature took 3x longer than the equivalent
inline change in a single HTML file. the single file pattern won not
because it's "the right answer" but because for an editor with ~200
features and 1 developer, the slope of feature velocity vs.
architectural overhead was wrong.

constraints that come with the single-file choice:
- file size: ~3300 lines, ~160 KB. fine in 2026 browsers. NOT fine if
  it grows past ~10k lines without modularization.
- no tests beyond a hand-rolled audit script (see "verification").
- no codesharing with anything else. Python reference stays
  authoritative spec for the projection geometry.
- editor and "library" are inseparable. someone wanting just the SVG
  renderer can't `npm install tunnelmap` and import a function — they
  have to copy code out of `index.html`. fine for v0.1.

## the projection

iso octolinear projection. world coords are `(gx, gy, plane)`. `gx, gy`
are arbitrary numbers in plane-local grid units (typically integer but
allowed to be fractional after corridor offsets). `plane` is an index
into `data.planes[]`, each carrying a `z` value.

the base projection is a 2x2 affine matrix from `(wx, wy) -> (screen_x,
screen_y)` plus a Y subtraction for plane height:

```
screen_x = wx * a + wy * b
screen_y = wx * c + wy * d - plane.z * PG_PX
```

default (iso NE) values: `a = cos30, b = -cos30, c = sin30, d = sin30`.

`VIEW_PRESETS` swaps these coefficients to give 8 different "view angles"
without modifying the 3D editor. the 4 iso corners are the same matrix
with a pre-applied 90deg integer rotation of the grid coords. flat,
flat-45, military, cabinet use different matrices entirely. all changes
are post-processing — the 3D editor stays in canonical iso NE so editing
remains consistent across preset changes.

GRID = 46 pixels per grid unit. PG_PX = 60 pixels per plane z-step.
both arbitrary; tuned to look good at the default zoom.

## corridor model

two lines that traverse the same edge get parallel-offset perpendicular
to the corridor. detected per-plane:

1. for every adjacent waypoint pair `(a, b)` on a line where both have
   the same plane, build a canonical edge key by sorting the endpoints
   so `(a, b)` and `(b, a)` collide.
2. group lines by edge key. each line gets a slot index `0..n-1`.
3. each waypoint's lateral offset is the mean of the offsets from the
   edges entering and leaving it (when both neighbors are same-plane).
   formula: `(slot - (n-1) / 2) * TRACK_SPACING` along the segment's
   perpendicular.

corner smoothing happens AFTER offset application, in 2D grid space.

`wp.offsetBias` is added on top of the auto-computed offset along the
local segment's perpendicular bisector. manual nudge knob; default 0.

## smoothing

three modes: `fillet`, `spline`, `sharp`.

**fillet** uses quadratic Bezier corner rounds. for each interior
waypoint with prev/cur/next, compute the angle, then a trim distance
`r / tan(angle/2)` (clamped to half the adjacent segment lengths).
emit `enter` at `cur - inDir * trim`, sample `segments` quadratic
Bezier points with `cur` as the control, then `exit` at
`cur + outDir * trim`. the original `cur` point is **NOT** in the
output — this is what bit us with cross-plane peaks until
`radiiForLine` was updated to force `r=0` at plane-change waypoints.

**spline** uses centripetal Catmull-Rom (alpha=0.5) through every
input. virtual endpoints are reflected across the first/last waypoint
to avoid t1==t0 division-by-zero (the bug that initially broke the
preview viewBox). passes through every input point by construction,
so multi-plane peaks survive automatically.

**sharp** returns input untouched. output length == input length.

## multi-plane line projection

the SVG export's `linePath()` smooths in 2D, then projects each output
point individually. each output gets the plane of its nearest input
waypoint (Euclidean distance in 2D grid space). this lets lines rise
and fall between planes correctly.

three caveats:
1. fillet smoothing eats the position of any cross-plane waypoint.
   workaround: `radiiForLine` returns 0 for any waypoint where either
   neighbor is on a different plane. sharp corner preserves the peak.
2. spline through cross-plane waypoints creates "diagonal rise" output
   points that map to whichever plane they're closest to. usually fine.
3. the 3D editor uses `wpToWorld(wp)` which honors each waypoint's
   plane directly, so 3D and SVG agree on multi-plane geometry as long
   as the radiiForLine guard is in place.

## station shape system

12 kinds and 11 shapes — orthogonal axes.

- **kind** describes function: regular, terminal, interchange, bend,
  depot, maintenance, abandoned, construction, signal_yard,
  control_tower, platform, junction. depot through junction override
  the shape entirely with bespoke glyphs.
- **shape** describes geometry: circle, square, diamond, triangle,
  plus, ring, pill, pill_v, stadium, hex, cluster. used for the four
  "normal" kinds.

oriented shapes (pill, stadium, hex, cluster, depot, signal_yard,
platform, junction) read each station's dominant incoming-line angle
via `stationDominantAngle(k)`. the angle is the bidirectional mean
computed via the doubled-angle trick:

```
mean_angle = atan2(sum(sin 2*a), sum(cos 2*a)) / 2
```

doubled-angle is necessary because direction is bidirectional — exits
toward east and west should reinforce each other, not cancel.

`station.size` multiplies the marker radius. interchanges also auto-bump
size by `1 + 0.10 * max(0, line_count - 2)` so 4-line interchanges
draw larger than 3-line interchanges.

## label placement

for each labeled station, examine 8 candidate positions: E, W, N, S +
four diagonals. each candidate has:
- a label bounding box approximated by `label.length * 6.5 px × 12 px`
- a text-anchor (start, end, middle) so text reads outward

score each candidate by the minimum clearance from its bbox samples
(corners + center) to every line segment and every already-placed
label. pick the candidate with the highest score. tiny bias toward
east breaks ties consistently with the legacy default.

algorithmically dumb — pure greedy descent, no annealing. works
acceptably for ~30 station maps. would need real annealing past ~80
stations (`reference/transit_map.py` does this).

## grey-mode hatching

11 SVG `<pattern>` defs, each used as a stroke paint server. line
rendering becomes a sandwich:

1. paper-colored casing (wide, draws background "punch through")
2. solid grey-shade stroke (`GREY_STYLES[i].shade`) — the line's identity
3. hatch pattern overlay at slightly narrower width — texture

each line in grey mode rotates through `GREY_STYLES`, indexed by
line position unless `line.greyStyle` overrides. tonal range is 12
shades from `#1a1a1a` to `#5a5a5a` so adjacent lines never read as
"the same darkness."

patterns themselves have transparent backgrounds (or solid neutral
backgrounds in a few cases). that lets the grey shade show through
the hatch's negative space, so the line keeps visual mass.

## service-state pipeline

`line.serviceState`: `active` | `reduced` | `maintenance` | `abandoned`.
`wp.segOut` / `wp.segMaint`: per-waypoint flags marking the segment
LEAVING that waypoint as abandoned or maintenance. mutually exclusive.

rendering splits each line into RUNS of consecutive waypoints sharing
the same out-state, then renders each run as its own polyline. the
line-level state composes with per-segment: line `abandoned` OR
`segOut` → abandoned render. line `maintenance` OR `segMaint` →
maintenance render (when not already abandoned). line `reduced` only
when neither segment flag is set.

abandoned: 55% opacity, 55% width, 6,5 long-dash, no casing, no
pattern overlay, forced grey `#7a7a7a`.
maintenance: 78% opacity, 42% width, 8,3,2,3 dash-dot, no casing,
forced warm grey `#7a6440`.
reduced: 75% opacity, 75% width, hatch overlay still shows.

## undo/redo

`JSON.stringify(data)` polled every 350ms. if it changed, push the
PREVIOUS snapshot onto the undo stack and update last-known. brutally
simple. cost is `O(data)` stringification per poll; cheap enough not
to matter at editor scale. cap is 80 snapshots.

`cmd+z` pops, `cmd+shift+z` redoes. selections cleared on each undo
to avoid pointing at deleted waypoints.

## cross-monitor canvas saga

four-layer defense built up incrementally as bugs surfaced:

1. **CSS lock.** `#canvas-container canvas { width: 100% !important;
   height: 100% !important }`. forces the canvas's CSS dimensions to
   always match the container regardless of what Three.js writes.
2. **setSize updateStyle=true.** the original code passed `false`,
   which updated only the WebGL drawing buffer and left canvas style
   stale. on monitor change with different DPR, drawing buffer
   resized but canvas displayed at old size, shrinking the map.
3. **DPR media query watcher.** `matchMedia('(resolution: Xdppx)')`
   fires `change` event when the value changes. recursive re-arm
   pattern (each handler is `{once: true}` and registers a new
   listener for the current DPR) so it survives any number of
   monitor swaps.
4. **800ms polling fallback.** key = `width × height @ dpr` string;
   poll every 800ms, call `applyResize` if changed. catches the
   pathological case where no event fires at all.

probably one or two layers more than strictly needed, but each was
added in response to a real bug report. removing any one of them is
asking for a regression.

## the ctxmenu refactor saga

four iterations:

1. cycle pattern: "service: active → reduced". confusing — required
   multiple right-clicks to land on target state.
2. direct picks: list current state as label, then offer "→ <state>"
   for each non-current state. clearer.
3. bounds check: menu was clipping at viewport edges. added `openCtx()`
   helper that measures `getBoundingClientRect()` AFTER population
   and flips the menu inward if it overflows.
4. critical bug: an initial `replace_all` of `classList.add('open')`
   to `openCtx()` accidentally replaced the SAME string INSIDE the
   `openCtx` function body itself, making it recursively call itself.
   infinite loop, menu broken. fix: revert that one line. lesson:
   replace_all on common substrings inside the function that
   produces them is dangerous.

## theme system

10 themes total, two layers:

- **CSS variables** drive the editor chrome. each `:root[data-theme]`
  block overrides the defaults set on `:root`. swapping themes is
  just `document.documentElement.setAttribute('data-theme', name)`.
- **JS `THEMES` table** drives the SVG export's paper color, plane
  tints, and ink. the export reads `data.theme` to look up its row.

plane tints are ordered bottom-dark → top-light. plane 0 (lowest z,
displays at bottom of stack) gets the darkest tint. lets upper planes
not occlude lower ones in iso view.

back-compat: `applyTheme('cyberpunk')` is aliased to `'outrun'` so
old saves load correctly.

## file truncation problem

an annoying recurring issue during development: the Edit tool would
occasionally truncate the file's tail after a large replacement,
leaving partial code at the end. the fix pattern was always:

1. detect via `node --check` failure or `tail` showing partial line
2. append the missing tail via heredoc, watching for dupes

if you're modifying this codebase, after any large Edit, always:

```
tail -3 index.html
grep -c "function updateHud" index.html  # should be 1
grep -c "^rebuildAll();" index.html  # should be 1
awk '/<script type="module">/,/<\/script>/' index.html | node --check -
```

## performance characteristics

- `rebuildLines()` rebuilds ALL line meshes every call. ~3ms for 12
  lines, ~30ms for 100 lines. could be incremental but isn't.
- `buildCorridors()` is O(L*W^2) where L=lines, W=avg waypoints per
  line. typically irrelevant.
- `exportSvg()` is O(P) where P=total plotted points. fast.
- undo polling is O(D) per 350ms where D=data size. ~2ms typically.
- the polling fallback is the only background cost. 800ms interval
  doing trivial string compare. negligible.

bottleneck is the 3D scene rebuild on data change. fine for now but
if line count goes past ~200 you'll want to memoize.

## known fragile areas

things to be careful around when modifying:

- the `replace_all` issue (see above). avoid global replacements of
  short strings.
- `linePath()` plane assignment via nearest-input. works because
  smoothing keeps output near input. could break under exotic curve
  modes or extreme corner-rounds.
- `controls.target.setY()` ONLY. setting X/Z would clobber user pan.
- the contextmenu `openCtx()` helper. inside its body, never use
  `openCtx()` recursively. always `ctxmenu.classList.add('open')` for
  the actual open.
- `updateStyle=true` on setSize. don't switch back to false.
- station marker Y-lift (0.25). below this, lines occlude stations
  visually in iso view.

## file map

high-level layout of `index.html`:

```
1..150     style block including theme CSS variables
150..400   HTML layout: sidebar, main, preview pane, popover, ctxmenu,
           help modal
400..500   importmap + three.js loader (closes first <script>)
500..900   constants, data model, plane/line/station builders
900..1100  rebuildLines, rebuildStations, rebuildLifts
1100..1200 rebuildSelection, rebuildHover, rebuildGuides
1200..1450 picking helpers, octolinearSnap, straightenLine,
           transformSelection
1450..1700 ctxmenu handler (waypoint, line, lift, plane branches)
1700..1900 keyboard handler, sidebar UI builders
1900..2100 popover wiring, theme + view picker init
2100..2400 exportSvg + projection math + style tables
2400..2700 line rendering (run-splitting, service states)
2700..3000 station markers (kinds + shape variants)
3000..3100 legend, terminus tabs, title block
3100..3200 file IO (export/save/load/reset)
3200..3300 preview pane, applyResize, animate loop
```

approximate; will drift as features land.
