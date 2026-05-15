# data model

a saved map is a single json object. the editor reads and writes the
same shape, and the python reference renderer consumes the same shape.

## top-level

```ts
{
  planes:    Plane[],         // up to 6 horizontal layers, bottom to top
  lines:     Line[],          // each line is an ordered list of waypoints
  stations:  Station[],       // optional named markers
  lifts:     Lift[],          // inter-plane connectors between two waypoints
  title?:    string,          // big title rendered in svg top-left
  subtitle?: string,          // smaller subtitle under the title
  theme?:    string,          // 'cool' (default) | 'paper' | 'bone' |
                              // 'beige' | 'sepia' | 'blueprint' | 'dark' |
                              // 'outrun' | 'killengn' | 'grivt'
  viewPreset?: string,        // 'iso-ne' (default) | 'iso-nw' | 'iso-sw' |
                              // 'iso-se' | 'flat' | 'flat-45' | 'military' |
                              // 'cabinet'
  legend?: {
    show: boolean,
    corner: 'tl' | 'tr' | 'bl' | 'br',
    endpoints: boolean,
  },
  camera?: {                  // last orbit-camera state, restored on load
    pos:    [number, number, number],
    target: [number, number, number],
    zoom:   number,
  },
}
```

## Plane

```ts
{
  name: string,    // sidebar label, e.g. 'Surface', 'Mid Level'
  z:    number,    // vertical offset in grid units; sets stacking distance
  tint: string,    // hex color of the plane fill
}
```

## Line

```ts
{
  id:           string,          // unique, e.g. 'vco', 'lfo', 'l<timestamp>'
  name:         string,          // shown in terminus tabs and legend
  color:        string,          // hex; used in color mode only
  style?:       'solid' | 'dashed' | 'dotted' | 'double' | 'thin' | 'thick',
  curveMode?:   'fillet' | 'spline' | 'sharp',
  serviceState?: 'active' | 'reduced' | 'maintenance' | 'abandoned',
  smoothRadius?: number,         // fillet corner radius for this line
  bwStyle?:     number,          // index into BW_STYLES for mono mode
  greyStyle?:   number,          // index into GREY_STYLES for grey mode
  smooth?:      boolean,         // legacy: true ≡ curveMode 'fillet'
  waypoints:    Waypoint[],
}
```

## Waypoint

```ts
{
  gx:    number,    // grid x, integer or fractional, can be negative
  gy:    number,    // grid y
  plane: number,    // index into planes[]
  cornerRadius?: number,  // override the line's fillet radius at this corner
  offsetBias?:   number,  // perpendicular shift in grid units, ±1.5
  segOut?:       boolean, // segment from this wp to the next is abandoned
  segMaint?:     boolean, // segment from this wp to the next is a maintenance tunnel
}
```

`segOut` and `segMaint` are mutually exclusive — setting one clears the
other in the ui. they only apply to the segment *leaving* this
waypoint, not the one arriving.

## Station

```ts
{
  id:    string,           // 's_<gx>_<gy>_<plane>' by convention
  gx:    number,           // must match a waypoint position to be rendered
  gy:    number,
  plane: number,
  name:  string,
  kind:  'regular' | 'terminal' | 'interchange' | 'bend' |
         'depot' | 'maintenance' | 'abandoned' |
         'construction' | 'signal_yard' | 'control_tower' |
         'platform' | 'junction',
  shape: 'circle' | 'square' | 'diamond' | 'triangle' | 'plus' | 'ring' |
         'pill' | 'pill_v' | 'stadium' | 'hex' | 'cluster',
  size?: number,           // marker scale multiplier, 0.5 to 2.5, default 1
}
```

if a station's coordinates don't coincide with any line's waypoint, the
station won't render. add a waypoint at the same grid cell on at least
one line to make it appear.

## Lift

```ts
{
  a: Waypoint,
  b: Waypoint,
}
```

both endpoints must live on different planes. rendered as a dashed grey
connector across the z-gap.

## back-compat

old saves with `theme: 'cyberpunk'` are auto-aliased to `'outrun'` on
load. old saves with `smooth: false` are interpreted as `curveMode:
'sharp'`. these mappings live in `applyTheme()` and `linePath()` in
`index.html`.
