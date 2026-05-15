#!/usr/bin/env python3
"""
isometric transit map generator.

emits a print quality svg with stacked planes, octolinear lines,
parallel corridor tracks, station markers, terminus tabs, and labels.
edit the data tables below and re-run.

projection:
    world coords are (gx, gy, plane).
    gx, gy are integer or fractional grid units inside a plane.
    plane is an integer 0..N from bottom to top.

    isometric basis (screen y points down):
        i hat = ( cos30,  sin30)    east in plane
        j hat = (-cos30,  sin30)    north in plane (toward upper left)
        k hat = (     0,    -1)    rise between planes

corridor model:
    every consecutive (a, b) waypoint pair on the same plane is an edge.
    edges are canonicalized by sorting the endpoints, so two lines
    traversing the same corridor in opposite directions still share it.
    every line in a shared corridor gets a slot index 0..n-1 and is
    rendered offset perpendicular to the corridor by
    (slot - (n-1)/2) * TRACK_SPACING grid units.

    waypoints must be subdivided wherever a corridor membership changes.
    that is, if line A goes (-7,-4) to (3,-4) but line B only joins it
    from (-5,-4) to (-1,-4), line A's waypoints must include (-5,-4)
    and (-1,-4) so the corridor membership can change at those nodes.
"""

import math
import sys

COS30 = math.cos(math.radians(30))
SIN30 = math.sin(math.radians(30))

# layout knobs
GRID = 46
PLANE_GAP = 210
LINE_WIDTH = 6.5
TRACK_SPACING = 0.20      # grid units between parallel tracks in a corridor
STATION_R = 5
INTERCHANGE_R = 8.5
TERMINAL_R = 6.5

PAGE_FONT = "Inter, Helvetica, Arial, sans-serif"
SHOW_GRID = False

# stations: id -> (gx, gy, plane, name, kind, label_dx, label_dy, anchor)
# kind in {terminal, interchange, regular, bend}
STATIONS = {
    # plane 0 surface
    "vco_w":      (-7, -4, 0, "VCO West",        "terminal",     -10, -10, "end"),
    "pulse":      (-5, -4, 0, "Pulse Park",      "regular",       -8, -10, "end"),
    "filter_jn":  (-3, -4, 0, "Filter Junction", "interchange",   12,  -8, "start"),
    "patch_bay":  ( 3, -4, 0, "Patch Bay",       "interchange",   12,  -8, "start"),
    "vco_e":      ( 6, -4, 0, "VCO East",        "terminal",      12, -10, "start"),

    "vcf_n":      (-3, -5, 0, "VCF North",       "terminal",     -10,  -8, "end"),
    "low_cut":    (-3,  0, 0, "Low Cut",         "interchange",  -14,   4, "end"),
    "bass_bin":   (-3,  2, 0, "Bass Bin",        "interchange",  -14,   4, "end"),
    "vcf_s":      (-3,  5, 0, "VCF South",       "terminal",     -10,  18, "end"),

    "bus_yard":   (-1,  4, 0, "Bus Yard",        "terminal",      12,  18, "start"),
    "vca_far":    (-6,  5, 0, "VCA Far",         "terminal",     -10,  18, "end"),
    "modulator":  ( 1, -2, 0, "Modulator",       "regular",       12,   4, "start"),
    "vca_e":      ( 5, -2, 0, "VCA East",        "terminal",      12,  -8, "start"),

    # plane 1 mid level
    "lfo_w":      (-6, -2, 1, "LFO West",        "terminal",     -10, -10, "end"),
    "trunk_w":    (-3, -2, 1, "Trunk West",      "interchange",  -14,  -8, "end"),
    "triangle":   ( 2, -2, 1, "Triangle Plaza",  "interchange",   14,  -8, "start"),
    "lfo_e":      ( 6, -2, 1, "LFO East",        "terminal",      12, -10, "start"),

    "eg_n":       ( 2, -4, 1, "EG North",        "terminal",      12, -10, "start"),
    "attack":     ( 2,  1, 1, "Attack",          "interchange",   14,   4, "start"),
    "decay":      ( 2,  3, 1, "Decay",           "interchange",   14,   4, "start"),
    "trunk_e":    ( 2,  4, 1, "Trunk End",       "terminal",     -14,   4, "end"),
    "eg_s":       ( 2,  5, 1, "EG South",        "terminal",      12,  18, "start"),

    "mixer_w":    (-5,  4, 1, "Mixer West",      "terminal",     -10,  18, "end"),
    "bus_cross":  (-1,  0, 1, "Bus Cross",       "regular",      -14,  -8, "end"),
    "mix_jn":     ( 4,  0, 1, "Mix Junction",    "terminal",      12,  -8, "start"),

    # plane 2 sky lines
    "sampler_w":  (-5, -1, 2, "Sampler West",    "terminal",     -10, -10, "end"),
    "loop_point": (-1, -1, 2, "Loop Point",      "interchange",   14,  -8, "start"),
    "branch_jn":  ( 3, -1, 2, "Branch Junction", "interchange",   14,  -8, "start"),
    "sampler_e":  ( 5, -1, 2, "Sampler East",    "terminal",      12, -10, "start"),

    "step_one":   (-3,  4, 2, "Step One",        "terminal",     -10,  18, "end"),
    "gate_w":     (-3,  1, 2, "Gate West",       "bend",         -14,  -8, "end"),
    "gate_e":     ( 3,  1, 2, "Gate East",       "interchange",   14,  -8, "start"),
    "step_eight": ( 3,  4, 2, "Step Eight",      "terminal",      12,  18, "start"),
}

# lines. waypoints subdivided at every corridor membership change.
# id, name, color, ordered list of (gx, gy, plane).
LINES = [
    # waypoints can be sparse. autosubdivide_lines() inserts breakpoints
    # automatically wherever another line joins, leaves, or crosses.
    {"id": "vco", "name": "VCO", "color": "#d62828", "waypoints": [
        (-7, -4, 0), (6, -4, 0),
    ]},
    {"id": "vcf", "name": "VCF", "color": "#1565c0", "waypoints": [
        (-3, -5, 0), (-3, 5, 0),
    ]},
    {"id": "vca", "name": "VCA", "color": "#2e7d32", "waypoints": [
        (-6, 5, 0), (-3, 2, 0), (1, -2, 0), (5, -2, 0),
    ]},
    {"id": "bus", "name": "BUS", "color": "#5d4037", "waypoints": [
        (-5, -4, 0), (-3, -4, 0), (-3, 2, 0), (-1, 4, 0),
    ]},
    {"id": "lfo", "name": "LFO", "color": "#f9a825", "waypoints": [
        (-6, -2, 1), (6, -2, 1),
    ]},
    {"id": "eg",  "name": "EG",  "color": "#c2185b", "waypoints": [
        (2, -4, 1), (2, 5, 1),
    ]},
    {"id": "mix", "name": "MIX", "color": "#00838f", "waypoints": [
        (-5, 4, 1), (-1, 0, 1), (4, 0, 1),
    ]},
    {"id": "trk", "name": "TRK", "color": "#37474f", "waypoints": [
        (-3, -2, 1), (2, -2, 1), (2, 4, 1),
    ]},
    {"id": "smp", "name": "SMP", "color": "#6a1b9a", "waypoints": [
        (-5, -1, 2), (5, -1, 2),
    ]},
    {"id": "seq", "name": "SEQ", "color": "#ef6c00", "waypoints": [
        (-3, 4, 2), (-3, 1, 2), (3, 1, 2), (3, 4, 2),
    ]},
    {"id": "brn", "name": "BRN", "color": "#558b2f", "waypoints": [
        (-1, -1, 2), (3, -1, 2), (3, 1, 2),
    ]},
]

# inter plane lifts
LIFTS = [
    ("patch_bay", "triangle"),
    ("low_cut",   "bus_cross"),
    ("bus_cross", "gate_w"),
    ("mix_jn",    "gate_e"),
    ("trunk_e",   "step_eight"),
]


def project(gx, gy, plane):
    wx = gx * GRID
    wy = gy * GRID
    X = (wx - wy) * COS30
    Y = (wx + wy) * SIN30 - plane * PLANE_GAP
    return X, Y


def edge_key(a, b):
    """canonical undirected edge key. requires same plane."""
    plane = a[2]
    p1 = (a[0], a[1])
    p2 = (b[0], b[1])
    return (plane, min(p1, p2), max(p1, p2))


def _direction(a, b):
    """returns the octolinear unit direction (dx, dy) of segment a->b, or None."""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if dx == 0 and dy == 0:
        return None
    if dx == 0:
        return (0, 1 if dy > 0 else -1)
    if dy == 0:
        return (1 if dx > 0 else -1, 0)
    if abs(dx) == abs(dy):
        return (1 if dx > 0 else -1, 1 if dy > 0 else -1)
    return None


def _collinear(a, b, c):
    """is point c on the line through a, b? assumes octolinear segments."""
    ab = _direction(a, b)
    if ab is None:
        return False
    ac_x = c[0] - a[0]
    ac_y = c[1] - a[1]
    return ac_x * ab[1] - ac_y * ab[0] == 0


def _param_on(p, a, b):
    """t such that p = a + t * (b - a)."""
    if abs(b[0] - a[0]) >= abs(b[1] - a[1]):
        if b[0] == a[0]:
            return 0.0
        return (p[0] - a[0]) / (b[0] - a[0])
    return (p[1] - a[1]) / (b[1] - a[1])


def autosubdivide_lines():
    """insert breakpoints in line waypoints wherever another line joins, leaves
    or crosses an octolinear segment. mutates LINES so the user can author
    sparse waypoints and have shared corridors detected automatically."""
    changed = True
    while changed:
        changed = False
        snapshot = []
        for ln in LINES:
            for i in range(len(ln["waypoints"]) - 1):
                snapshot.append((ln["id"], ln["waypoints"][i],
                                 ln["waypoints"][i + 1]))
        for ln in LINES:
            new_wps = []
            for i in range(len(ln["waypoints"]) - 1):
                a = ln["waypoints"][i]
                b = ln["waypoints"][i + 1]
                new_wps.append(a)
                if a[2] != b[2]:
                    continue
                breakpoints = []
                for other_id, oa, ob in snapshot:
                    if other_id == ln["id"]:
                        continue
                    if oa[2] != a[2]:
                        continue
                    for op in (oa, ob):
                        if op == a or op == b:
                            continue
                        if not _collinear(a, b, op):
                            continue
                        t = _param_on(op, a, b)
                        if 0 < t < 1:
                            bp = (op[0], op[1], a[2])
                            if bp not in breakpoints:
                                breakpoints.append(bp)
                if breakpoints:
                    breakpoints.sort(key=lambda p: _param_on(p, a, b))
                    new_wps.extend(breakpoints)
                    changed = True
            new_wps.append(ln["waypoints"][-1])
            ln["waypoints"] = new_wps


def build_corridors():
    """returns dict edge_key -> [line_id, ...] in deterministic order."""
    corridors = {}
    for ln in LINES:
        wps = ln["waypoints"]
        for i in range(len(wps) - 1):
            a, b = wps[i], wps[i + 1]
            if a[2] != b[2]:
                continue
            key = edge_key(a, b)
            corridors.setdefault(key, [])
            if ln["id"] not in corridors[key]:
                corridors[key].append(ln["id"])
    return corridors


def edge_offset(a, b, line_id, corridors):
    """returns (ox, oy) in plane local grid units."""
    if a[2] != b[2]:
        return (0.0, 0.0)
    key = edge_key(a, b)
    cor = corridors.get(key)
    if not cor or line_id not in cor:
        return (0.0, 0.0)
    slot = cor.index(line_id)
    n = len(cor)
    amount = (slot - (n - 1) / 2.0) * TRACK_SPACING
    cdx = key[2][0] - key[1][0]
    cdy = key[2][1] - key[1][1]
    L = math.hypot(cdx, cdy)
    if L < 1e-6:
        return (0.0, 0.0)
    px, py = -cdy / L, cdx / L
    return (px * amount, py * amount)


def waypoint_offset(line, i, corridors):
    """average perpendicular offset at waypoint i, from incident edges."""
    wps = line["waypoints"]
    offsets = []
    if i > 0 and wps[i - 1][2] == wps[i][2]:
        offsets.append(edge_offset(wps[i - 1], wps[i], line["id"], corridors))
    if i < len(wps) - 1 and wps[i + 1][2] == wps[i][2]:
        offsets.append(edge_offset(wps[i], wps[i + 1], line["id"], corridors))
    if not offsets:
        return (0.0, 0.0)
    ox = sum(o[0] for o in offsets) / len(offsets)
    oy = sum(o[1] for o in offsets) / len(offsets)
    return (ox, oy)


def line_screen_path(line, corridors):
    pts = []
    for i, wp in enumerate(line["waypoints"]):
        ox, oy = waypoint_offset(line, i, corridors)
        gx, gy, plane = wp
        pts.append(project(gx + ox, gy + oy, plane))
    return pts


# label collision avoidance.
LABEL_FONT_SIZE = 10.5
LABEL_CHAR_WIDTH = 5.6  # rough px per char at weight 500 in the chosen font

# candidate label positions in screen space, in priority order.
# generated in three concentric rings so a station whose first choice
# collides can move further out instead of jumping to a worse direction.
def _candidate_offsets():
    base = [
        ( 12,  -8, "start"),
        (-12,  -8, "end"),
        ( 12,  16, "start"),
        (-12,  16, "end"),
        (  0, -14, "middle"),
        (  0,  20, "middle"),
        ( 16,   4, "start"),
        (-16,   4, "end"),
    ]
    out = []
    for scale in (1.0, 1.5, 2.1):
        for dx, dy, anchor in base:
            out.append((dx * scale, dy * scale, anchor))
    return out

CANDIDATE_OFFSETS = _candidate_offsets()


def label_box(text, sx, sy, dx, dy, anchor):
    w = len(text) * LABEL_CHAR_WIDTH + 4
    h = LABEL_FONT_SIZE + 4
    cx = sx + dx
    cy = sy + dy
    if anchor == "start":
        bx = cx - 2
    elif anchor == "end":
        bx = cx - w + 2
    else:
        bx = cx - w / 2
    by = cy - h * 0.78
    return (bx, by, w, h)


def boxes_overlap(a, b, pad=1):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (
        ax + aw + pad < bx
        or bx + bw + pad < ax
        or ay + ah + pad < by
        or by + bh + pad < ay
    )


def seg_box_intersect(p1, p2, box):
    """liang barsky clip test."""
    x1, y1 = p1
    x2, y2 = p2
    bx, by, bw, bh = box
    dx = x2 - x1
    dy = y2 - y1
    p = [-dx, dx, -dy, dy]
    q = [x1 - bx, bx + bw - x1, y1 - by, by + bh - y1]
    u1, u2 = 0.0, 1.0
    for i in range(4):
        if abs(p[i]) < 1e-12:
            if q[i] < 0:
                return False
        else:
            t = q[i] / p[i]
            if p[i] < 0:
                u1 = max(u1, t)
            else:
                u2 = min(u2, t)
    return u1 <= u2


def circle_box_intersect(cx, cy, r, box):
    bx, by, bw, bh = box
    closest_x = max(bx, min(cx, bx + bw))
    closest_y = max(by, min(cy, by + bh))
    dx = cx - closest_x
    dy = cy - closest_y
    return dx * dx + dy * dy <= r * r


def place_labels(corridors):
    """returns dict sid -> (lx, ly, anchor, box, leader_endpoint_or_None)."""
    line_segments = []
    for ln in LINES:
        path = line_screen_path(ln, corridors)
        for i in range(len(path) - 1):
            line_segments.append((path[i], path[i + 1]))
    for a, b in LIFTS:
        ax, ay, ap = STATIONS[a][:3]
        bx, by, bp = STATIONS[b][:3]
        line_segments.append((project(ax, ay, ap), project(bx, by, bp)))

    station_circles = []
    for sid, rec in STATIONS.items():
        gx, gy, plane = rec[:3]
        kind = rec[4]
        X, Y = project(gx, gy, plane)
        if kind == "interchange":
            r = INTERCHANGE_R + 2
        elif kind == "terminal":
            r = TERMINAL_R + 1.5
        else:
            r = STATION_R + 1.5
        station_circles.append((X, Y, r, sid))

    placed = {}  # sid -> box
    result = {}

    def priority(sid):
        kind = STATIONS[sid][4]
        return {"interchange": 0, "terminal": 1, "regular": 2, "bend": 3}.get(kind, 4)

    sids = sorted(STATIONS.keys(), key=priority)

    for sid in sids:
        rec = STATIONS[sid]
        gx, gy, plane, name, kind = rec[:5]
        sx, sy = project(gx, gy, plane)

        best = None
        best_penalty = float('inf')
        best_box = None

        for dx, dy, anchor in CANDIDATE_OFFSETS:
            box = label_box(name, sx, sy, dx, dy, anchor)
            penalty = 0
            for other_sid, other_box in placed.items():
                if boxes_overlap(box, other_box, pad=1):
                    penalty += 100
            for cx, cy, cr, other_sid in station_circles:
                if other_sid == sid:
                    continue
                if circle_box_intersect(cx, cy, cr, box):
                    penalty += 50
            for p1, p2 in line_segments:
                if seg_box_intersect(p1, p2, box):
                    penalty += 30
            if penalty < best_penalty:
                best_penalty = penalty
                best = (sx + dx, sy + dy, anchor)
                best_box = box
                if penalty == 0:
                    break

        placed[sid] = best_box
        # add leader line if label moved more than the closest ring
        leader = None
        primary_dx = best[0] - sx
        primary_dy = best[1] - sy
        if math.hypot(primary_dx, primary_dy) > 24:
            # leader runs from station rim toward label box edge
            ux = primary_dx / math.hypot(primary_dx, primary_dy)
            uy = primary_dy / math.hypot(primary_dx, primary_dy)
            station_r = TERMINAL_R if kind == "terminal" else (
                INTERCHANGE_R if kind == "interchange" else STATION_R
            )
            leader = (
                sx + ux * (station_r + 1),
                sy + uy * (station_r + 1),
                best[0] - ux * 4,
                best[1] - uy * 4,
            )
        result[sid] = (best[0], best[1], best[2], best_box, leader)

    # simulated annealing pass. swap any pair of stations' chosen offsets
    # if the swap reduces total penalty. iterate until no improving swap exists.
    def total_penalty():
        total = 0
        boxes = [v[3] for v in result.values()]
        ids = list(result.keys())
        for i, a in enumerate(boxes):
            for j in range(i + 1, len(boxes)):
                if boxes_overlap(a, boxes[j], pad=1):
                    total += 100
            for cx, cy, cr, other_sid in station_circles:
                if other_sid == ids[i]:
                    continue
                if circle_box_intersect(cx, cy, cr, a):
                    total += 50
            for p1, p2 in line_segments:
                if seg_box_intersect(p1, p2, a):
                    total += 30
        return total

    def candidate_for(sid, dx, dy, anchor):
        rec = STATIONS[sid]
        gx, gy, plane, name = rec[:4]
        sx, sy = project(gx, gy, plane)
        return (sx + dx, sy + dy, anchor,
                label_box(name, sx, sy, dx, dy, anchor))

    improving = True
    rounds = 0
    while improving and rounds < 6:
        improving = False
        rounds += 1
        sids = list(result.keys())
        current_penalty = total_penalty()
        for sid in sids:
            rec = STATIONS[sid]
            best_swap = None
            best_swap_pen = current_penalty
            for dx, dy, anchor in CANDIDATE_OFFSETS:
                lx, ly, anc, box = candidate_for(sid, dx, dy, anchor)
                old = result[sid]
                result[sid] = (lx, ly, anc, box, old[4])
                p = total_penalty()
                if p < best_swap_pen:
                    best_swap_pen = p
                    best_swap = result[sid]
                result[sid] = old
            if best_swap is not None:
                result[sid] = best_swap
                current_penalty = best_swap_pen
                improving = True
    return result


def emit_terminus_tabs(line, screen_path):
    """short colored pills with line code at each terminus."""
    if len(screen_path) < 2:
        return []
    out = []
    for end_idx, prev_idx in [(0, 1), (-1, -2)]:
        Ex, Ey = screen_path[end_idx]
        Px, Py = screen_path[prev_idx]
        dx, dy = Ex - Px, Ey - Py
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue
        ux, uy = dx / L, dy / L
        # arm extends along the line direction, then tab is horizontal
        arm_len = 14
        ax = Ex + ux * arm_len
        ay = Ey + uy * arm_len
        tab_w, tab_h = 36, 17
        # offset the tab so its inside edge meets the end of the arm
        cx = ax + ux * (tab_w / 2)
        cy = ay + uy * (tab_h / 2 if uy > 0 else -tab_h / 2)
        # short arm in the line color from terminus to tab edge
        out.append(
            f'<line x1="{Ex:.1f}" y1="{Ey:.1f}" '
            f'x2="{ax:.1f}" y2="{ay:.1f}" '
            f'stroke="{line["color"]}" stroke-width="3.5" '
            f'stroke-linecap="round"/>'
        )
        # horizontal tab pill
        out.append(
            f'<rect x="{cx - tab_w/2:.1f}" y="{cy - tab_h/2:.1f}" '
            f'width="{tab_w}" height="{tab_h}" rx="{tab_h/2:.1f}" '
            f'fill="{line["color"]}"/>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="{cy + 4:.1f}" font-size="11" '
            f'font-weight="700" fill="#fff" text-anchor="middle" '
            f'letter-spacing="1.4">{line["name"]}</text>'
        )
    return out


def stadium_for_station(sid, corridors):
    """returns stadium params for an interchange that has a shared corridor.
    returns None for plain interchanges (use circle marker instead).
    returns (cx, cy, length, angle_deg, n_tracks) where length is along
    the perpendicular to the corridor, angle is in degrees in screen space.
    """
    rec = STATIONS[sid]
    gx, gy, plane, name, kind = rec[:5]
    if kind != "interchange":
        return None
    # find the most populous corridor incident to this station
    best = None
    best_n = 1
    for key, lines in corridors.items():
        kp, p1, p2 = key
        if kp != plane:
            continue
        if p1 == (gx, gy) or p2 == (gx, gy):
            if len(lines) > best_n:
                best_n = len(lines)
                best = (key, lines)
    if best is None or best_n < 2:
        return None
    (kp, p1, p2), lines = best
    # screen direction of the corridor at this station
    Sx1, Sy1 = project(p1[0], p1[1], kp)
    Sx2, Sy2 = project(p2[0], p2[1], kp)
    sdx = Sx2 - Sx1
    sdy = Sy2 - Sy1
    L = math.hypot(sdx, sdy)
    if L < 1e-6:
        return None
    ux, uy = sdx / L, sdy / L
    # perpendicular unit in screen
    px, py = -uy, ux
    # screen distance between adjacent tracks (perpendicular offset of TRACK_SPACING grid units)
    track_screen = TRACK_SPACING * GRID  # cardinal corridors give exactly this; diagonals slightly more
    cx, cy = project(gx, gy, plane)
    length = (best_n - 1) * track_screen + 2 * INTERCHANGE_R
    # stadium long axis is perpendicular to corridor; angle of perpendicular
    angle = math.degrees(math.atan2(py, px))
    return cx, cy, length, angle, best_n, (px, py), track_screen


def emit_svg():
    autosubdivide_lines()
    corridors = build_corridors()
    out = []

    pts = []
    for s in STATIONS.values():
        pts.append(project(s[0], s[1], s[2]))
    for ln in LINES:
        for X, Y in line_screen_path(ln, corridors):
            pts.append((X, Y))

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    pad_l, pad_r = 240, 130
    pad_t, pad_b = 130, 80
    minx = min(xs) - pad_l
    maxx = max(xs) + pad_r
    miny = min(ys) - pad_t
    maxy = max(ys) + pad_b
    vbw = maxx - minx
    vbh = maxy - miny

    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{minx:.1f} {miny:.1f} {vbw:.1f} {vbh:.1f}" '
        f'width="1500" font-family="{PAGE_FONT}">'
    )
    # css theme block. override any of these vars in illustrator or a
    # downstream stylesheet to reskin the whole map without touching geometry.
    line_var_decls = "\n".join(
        f"    --line-{ln['id']}: {ln['color']};" for ln in LINES
    )
    out.append(
        '<defs><style><![CDATA[\n'
        ':root {\n'
        '    --paper: #faf8f3;\n'
        '    --plane-1: #f0eadf;\n'
        '    --plane-2: #ece5d6;\n'
        '    --plane-3: #e8e0cd;\n'
        '    --plane-stroke: #cdbf9c;\n'
        '    --plane-label: #6e5d36;\n'
        '    --station-fill: #ffffff;\n'
        '    --station-stroke: #111111;\n'
        '    --label-text: #1a1a1a;\n'
        '    --leader: #777777;\n'
        '    --lift: #3a3a3a;\n'
        f'{line_var_decls}\n'
        '}\n'
        ']]></style></defs>'
    )
    out.append(
        f'<rect x="{minx:.1f}" y="{miny:.1f}" width="{vbw:.1f}" '
        f'height="{vbh:.1f}" fill="var(--paper, #faf8f3)"/>'
    )

    # plane bodies, drawn bottom up
    plane_corners = [(-9, -6), (9, -6), (9, 7), (-9, 7)]
    plane_labels = ["Surface", "Mid Level", "Sky Lines"]
    plane_tints  = ["#f0eadf", "#ece5d6", "#e8e0cd"]
    for plane_idx in range(3):
        proj_corners = [project(c[0], c[1], plane_idx) for c in plane_corners]
        d = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in proj_corners)
        out.append(
            f'<polygon points="{d}" fill="{plane_tints[plane_idx]}" '
            f'stroke="#cdbf9c" stroke-width="0.6" opacity="0.6"/>'
        )
        lx, ly = project(plane_corners[0][0], plane_corners[0][1], plane_idx)
        out.append(
            f'<text x="{lx - 16:.1f}" y="{ly + 6:.1f}" font-size="13" '
            f'font-weight="600" fill="#6e5d36" text-anchor="end" '
            f'letter-spacing="1.4">{plane_labels[plane_idx].upper()}</text>'
        )

    if SHOW_GRID:
        for plane_idx in range(3):
            for gv in range(-9, 10):
                a = project(gv, -6, plane_idx)
                b = project(gv,  7, plane_idx)
                out.append(
                    f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" '
                    f'x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                    f'stroke="#d8cdb1" stroke-width="0.3" opacity="0.5"/>'
                )
            for gv in range(-6, 8):
                a = project(-9, gv, plane_idx)
                b = project( 9, gv, plane_idx)
                out.append(
                    f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" '
                    f'x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                    f'stroke="#d8cdb1" stroke-width="0.3" opacity="0.5"/>'
                )

    # lifts under lines
    for a, b in LIFTS:
        ax, ay, ap = STATIONS[a][:3]
        bx, by, bp = STATIONS[b][:3]
        Ax, Ay = project(ax, ay, ap)
        Bx, By = project(bx, by, bp)
        out.append(
            f'<line x1="{Ax:.1f}" y1="{Ay:.1f}" '
            f'x2="{Bx:.1f}" y2="{By:.1f}" '
            f'stroke="#3a3a3a" stroke-width="2.4" '
            f'stroke-dasharray="3.5,3" stroke-linecap="round"/>'
        )

    # transit lines with parallel offsets
    line_paths = {}
    for ln in LINES:
        path = line_screen_path(ln, corridors)
        line_paths[ln["id"]] = path
        d = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in path)
        out.append(
            f'<polyline points="{d}" fill="none" stroke="{ln["color"]}" '
            f'stroke-width="{LINE_WIDTH}" stroke-linecap="round" '
            f'stroke-linejoin="round"/>'
        )

    # terminus tabs over lines
    for ln in LINES:
        out.extend(emit_terminus_tabs(ln, line_paths[ln["id"]]))

    # auto place all labels using corridor and segment aware collision detection
    label_placement = place_labels(corridors)

    # stations at central waypoint
    for sid, rec in STATIONS.items():
        gx, gy, plane, name, kind = rec[:5]
        X, Y = project(gx, gy, plane)

        if kind == "interchange":
            stadium = stadium_for_station(sid, corridors)
            if stadium is not None:
                cx, cy, length, angle, n_tracks, perp, track_sp = stadium
                rh = INTERCHANGE_R + 1.5
                out.append(
                    f'<g transform="translate({cx:.1f},{cy:.1f}) rotate({angle:.1f})">'
                    f'<rect x="{-length/2:.1f}" y="{-rh:.1f}" '
                    f'width="{length:.1f}" height="{2*rh:.1f}" rx="{rh:.1f}" '
                    f'fill="#fff" stroke="#111" stroke-width="2.4"/>'
                    f'</g>'
                )
                # one black dot per track inside the stadium
                for slot in range(n_tracks):
                    off = (slot - (n_tracks - 1) / 2.0) * track_sp
                    dx_ = cx + off * perp[0]
                    dy_ = cy + off * perp[1]
                    out.append(
                        f'<circle cx="{dx_:.1f}" cy="{dy_:.1f}" '
                        f'r="{INTERCHANGE_R*0.42:.2f}" '
                        f'fill="var(--station-stroke, #111)"/>'
                    )
            else:
                out.append(
                    f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{INTERCHANGE_R + 1.5}" '
                    f'fill="var(--station-fill, #fff)" '
                    f'stroke="var(--station-stroke, #111)" stroke-width="2.4"/>'
                )
                out.append(
                    f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{INTERCHANGE_R*0.45}" '
                    f'fill="var(--station-stroke, #111)"/>'
                )
        elif kind == "terminal":
            out.append(
                f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{TERMINAL_R}" '
                f'fill="var(--station-fill, #fff)" '
                f'stroke="var(--station-stroke, #111)" stroke-width="2"/>'
            )
        elif kind == "bend":
            out.append(
                f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{STATION_R*0.85}" '
                f'fill="var(--station-fill, #fff)" '
                f'stroke="var(--station-stroke, #111)" stroke-width="1.4"/>'
            )
        else:
            out.append(
                f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{STATION_R}" '
                f'fill="var(--station-fill, #fff)" '
                f'stroke="var(--station-stroke, #111)" stroke-width="1.6"/>'
            )

        lx_, ly_, anchor, _bbox, leader = label_placement[sid]
        if leader is not None:
            sxL, syL, exL, eyL = leader
            out.append(
                f'<line x1="{sxL:.1f}" y1="{syL:.1f}" '
                f'x2="{exL:.1f}" y2="{eyL:.1f}" '
                f'stroke="var(--leader, #777)" stroke-width="0.7" '
                f'stroke-linecap="round" opacity="0.85"/>'
            )
        out.append(
            f'<text x="{lx_:.1f}" y="{ly_:.1f}" font-size="10.5" '
            f'fill="var(--label-text, #1a1a1a)" text-anchor="{anchor}" '
            f'font-weight="500">{name}</text>'
        )

    # title block
    out.append(
        f'<text x="{minx + 30:.1f}" y="{miny + 60:.1f}" font-size="34" '
        f'font-weight="700" fill="#111" letter-spacing="-0.5">'
        f'Synth City Transit</text>'
    )
    out.append(
        f'<text x="{minx + 30:.1f}" y="{miny + 86:.1f}" font-size="12" '
        f'fill="#555">Eleven lines across three isometric planes. '
        f'octolinear, parallel corridors, stadium interchanges, '
        f'auto subdivided waypoints, css theme variables.'
        f'</text>'
    )

    # legend
    lx0 = minx + 30
    ly0 = miny + 130
    out.append(
        f'<text x="{lx0:.1f}" y="{ly0:.1f}" font-size="11" '
        f'font-weight="600" fill="#333" letter-spacing="1.4">LINES</text>'
    )
    for i, ln in enumerate(LINES):
        yy = ly0 + 22 + i * 18
        out.append(
            f'<line x1="{lx0:.1f}" y1="{yy:.1f}" x2="{lx0 + 28:.1f}" '
            f'y2="{yy:.1f}" stroke="{ln["color"]}" stroke-width="5" '
            f'stroke-linecap="round"/>'
        )
        out.append(
            f'<text x="{lx0 + 38:.1f}" y="{yy + 4:.1f}" font-size="11" '
            f'fill="#222">{ln["name"]}</text>'
        )
    legend_h = 22 + len(LINES) * 18
    yy = ly0 + legend_h + 16
    out.append(
        f'<text x="{lx0:.1f}" y="{yy:.1f}" font-size="11" '
        f'font-weight="600" fill="#333" letter-spacing="1.4">TRANSFERS</text>'
    )
    yy += 20
    out.append(
        f'<line x1="{lx0:.1f}" y1="{yy:.1f}" x2="{lx0 + 28:.1f}" '
        f'y2="{yy:.1f}" stroke="#3a3a3a" stroke-width="2.4" '
        f'stroke-dasharray="3.5,3" stroke-linecap="round"/>'
    )
    out.append(
        f'<text x="{lx0 + 38:.1f}" y="{yy + 4:.1f}" font-size="11" '
        f'fill="#222">vertical lift between planes</text>'
    )
    yy += 18
    out.append(
        f'<rect x="{lx0 + 4:.1f}" y="{yy - 7:.1f}" width="20" height="14" '
        f'rx="7" fill="#fff" stroke="#111" stroke-width="2"/>'
    )
    out.append(
        f'<circle cx="{lx0 + 10:.1f}" cy="{yy:.1f}" r="2.6" fill="#111"/>'
    )
    out.append(
        f'<circle cx="{lx0 + 18:.1f}" cy="{yy:.1f}" r="2.6" fill="#111"/>'
    )
    out.append(
        f'<text x="{lx0 + 38:.1f}" y="{yy + 4:.1f}" font-size="11" '
        f'fill="#222">stadium interchange</text>'
    )
    yy += 18
    out.append(
        f'<circle cx="{lx0 + 14:.1f}" cy="{yy:.1f}" r="6.5" fill="#fff" '
        f'stroke="#111" stroke-width="2"/>'
    )
    out.append(
        f'<text x="{lx0 + 38:.1f}" y="{yy + 4:.1f}" font-size="11" '
        f'fill="#222">terminus (with line tab)</text>'
    )

    nx = maxx - 130
    ny = miny + 90
    out.append(
        f'<text x="{nx:.1f}" y="{ny - 26:.1f}" font-size="11" '
        f'font-weight="600" fill="#333" letter-spacing="1.4" '
        f'text-anchor="middle">PLANE AXES</text>'
    )
    for ang_deg in range(0, 360, 45):
        rad = math.radians(ang_deg)
        ix, iy = COS30, SIN30
        jx, jy = -COS30, SIN30
        sx_ = math.cos(rad) * ix + math.sin(rad) * jx
        sy_ = math.cos(rad) * iy + math.sin(rad) * jy
        out.append(
            f'<line x1="{nx:.1f}" y1="{ny:.1f}" '
            f'x2="{nx + sx_*26:.1f}" y2="{ny + sy_*26:.1f}" '
            f'stroke="#777" stroke-width="1.2" stroke-linecap="round"/>'
        )
    out.append(
        f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="2" fill="#333"/>'
    )

    out.append(
        f'<text x="{maxx - 30:.1f}" y="{maxy - 22:.1f}" font-size="10" '
        f'fill="#888" text-anchor="end">'
        f'transit_map.py / iso octolinear / auto subdivide / parallel corridors / '
        f'stadium interchanges / annealed labels / css theme / 30 deg projection'
        f'</text>'
    )

    out.append('</svg>')
    return '\n'.join(out)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "transit_map.svg"
    svg = emit_svg()
    with open(target, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote %s (%d bytes)" % (target, len(svg)))
