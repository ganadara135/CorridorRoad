import FreeCAD as App
import Part


def find_sketch_objects(doc):
    out = []
    if doc is None:
        return out
    for o in list(getattr(doc, "Objects", []) or []):
        try:
            tid = str(getattr(o, "TypeId", "") or "")
            if tid.startswith("Sketcher::"):
                out.append(o)
        except Exception:
            continue
    return out


def _dedupe_points(points, tol: float = 1e-6):
    out = []
    for p in points:
        if not out or (p - out[-1]).Length > tol:
            out.append(p)
    return out


def _edge_endpoints(edge):
    try:
        p0 = edge.valueAt(float(edge.FirstParameter))
        p1 = edge.valueAt(float(edge.LastParameter))
        return App.Vector(float(p0.x), float(p0.y), float(p0.z)), App.Vector(float(p1.x), float(p1.y), float(p1.z))
    except Exception:
        v = list(getattr(edge, "Vertexes", []) or [])
        if len(v) >= 2:
            p0 = v[0].Point
            p1 = v[-1].Point
            return App.Vector(float(p0.x), float(p0.y), float(p0.z)), App.Vector(float(p1.x), float(p1.y), float(p1.z))
    raise ValueError("Edge endpoint extraction failed.")


def _orient_chain_edges(edges, tol: float = 1e-6):
    if not edges:
        return []
    out = []
    a0, b0 = _edge_endpoints(edges[0])
    out.append({"edge": edges[0], "start": a0, "end": b0})
    tail = b0
    for e in edges[1:]:
        a, b = _edge_endpoints(e)
        if (a - tail).Length <= tol:
            st, en = a, b
        elif (b - tail).Length <= tol:
            st, en = b, a
        else:
            da = float((a - tail).Length)
            db = float((b - tail).Length)
            st, en = (a, b) if da <= db else (b, a)
        out.append({"edge": e, "start": st, "end": en})
        tail = en
    return out


def _single_open_chain(shape, tol: float = 1e-6):
    edges = list(getattr(shape, "Edges", []) or [])
    if not edges:
        raise ValueError("Sketch has no edges.")
    try:
        chains = Part.sortEdges(edges)
    except Exception:
        chains = [edges]
    if not chains:
        raise ValueError("Sketch edge chaining failed.")
    if len(chains) != 1:
        raise ValueError(f"Sketch must have a single connected path. Found {len(chains)} paths.")
    oriented = _orient_chain_edges(chains[0], tol=tol)
    pts = []
    if oriented:
        pts = [oriented[0]["start"]]
        for info in oriented:
            pts.append(info["end"])
        pts = _dedupe_points(pts, tol=tol)
    if len(pts) < 2:
        raise ValueError("Sketch path has fewer than 2 valid points.")
    if (pts[0] - pts[-1]).Length <= tol:
        raise ValueError("Closed sketch is not supported. Use an open sketch path.")
    return oriented, pts


def _edge_radius_if_arc(edge):
    try:
        c = getattr(edge, "Curve", None)
        if c is None:
            return 0.0
        tid = str(getattr(c, "TypeId", "") or "")
        if "Circle" in tid:
            return abs(float(getattr(c, "Radius", 0.0)))
    except Exception:
        return 0.0
    return 0.0


def _is_line_edge(edge) -> bool:
    try:
        c = getattr(edge, "Curve", None)
        if c is None:
            return False
        tid = str(getattr(c, "TypeId", "") or "")
        return "Line" in tid
    except Exception:
        return False


def _is_arc_edge(edge) -> bool:
    return _edge_radius_if_arc(edge) > 1e-12


def _line_dir(info):
    v = info["end"] - info["start"]
    L = float(v.Length)
    if L <= 1e-12:
        return None
    return v * (1.0 / L)


def _line_intersection_xy(p1: App.Vector, d1: App.Vector, p2: App.Vector, d2: App.Vector):
    a11 = float(d1.x)
    a12 = -float(d2.x)
    a21 = float(d1.y)
    a22 = -float(d2.y)
    b1 = float(p2.x - p1.x)
    b2 = float(p2.y - p1.y)
    det = a11 * a22 - a12 * a21
    if abs(det) <= 1e-12:
        return None
    t = (b1 * a22 - b2 * a12) / det
    return App.Vector(float(p1.x + t * d1.x), float(p1.y + t * d1.y), 0.0)


def sketch_to_alignment_rows(sketch_obj, tol: float = 1e-6, z_tol: float = 1e-4):
    if sketch_obj is None:
        raise ValueError("Sketch is not selected.")
    shp = getattr(sketch_obj, "Shape", None)
    if shp is None or shp.isNull():
        raise ValueError("Sketch shape is empty.")

    oriented, pts = _single_open_chain(shp, tol=tol)
    zs = [float(p.z) for p in pts]
    if zs and (max(zs) - min(zs)) > float(z_tol):
        raise ValueError(f"Sketch must be planar in XY (Z range={max(zs)-min(zs):.6f}).")

    rows = []
    if not oriented:
        raise ValueError("Sketch path has no oriented edges.")

    rows.append((float(oriented[0]["start"].x), float(oriented[0]["start"].y), 0.0, 0.0))

    m = len(oriented)
    for i, info in enumerate(oriented):
        e = info["edge"]
        prev_info = oriented[i - 1] if i > 0 else None
        next_info = oriented[i + 1] if (i + 1) < m else None

        if _is_arc_edge(e):
            if prev_info is not None and next_info is not None and _is_line_edge(prev_info["edge"]) and _is_line_edge(next_info["edge"]):
                d1 = _line_dir(prev_info)
                d2 = _line_dir(next_info)
                pi = None
                if d1 is not None and d2 is not None:
                    pi = _line_intersection_xy(prev_info["end"], d1, next_info["start"], d2)
                if pi is None:
                    # Fallback when tangents are near-parallel: use arc chord midpoint as approximate PI.
                    pi = App.Vector(
                        0.5 * float(info["start"].x + info["end"].x),
                        0.5 * float(info["start"].y + info["end"].y),
                        0.0,
                    )
                rows.append((float(pi.x), float(pi.y), float(_edge_radius_if_arc(e)), 0.0))
            # Arc endpoints (tangent points) are intentionally not added as IP rows.
            continue

        if _is_line_edge(e):
            # If next edge is an arc, this endpoint is arc tangent point (TS) not PI.
            if next_info is not None and _is_arc_edge(next_info["edge"]):
                continue
            rows.append((float(info["end"].x), float(info["end"].y), 0.0, 0.0))
            continue

        # Generic fallback for unsupported edge types.
        rows.append((float(info["end"].x), float(info["end"].y), 0.0, 0.0))

    # Remove near-duplicate consecutive rows while keeping max radius/transition hints.
    dedup_rows = []
    for x, y, rr, ls in rows:
        if not dedup_rows:
            dedup_rows.append([float(x), float(y), float(rr), float(ls)])
            continue
        dx = float(x) - float(dedup_rows[-1][0])
        dy = float(y) - float(dedup_rows[-1][1])
        if (dx * dx + dy * dy) <= (tol * tol):
            dedup_rows[-1][2] = max(float(dedup_rows[-1][2]), float(rr))
            dedup_rows[-1][3] = max(float(dedup_rows[-1][3]), float(ls))
        else:
            dedup_rows.append([float(x), float(y), float(rr), float(ls)])

    if len(dedup_rows) < 2:
        raise ValueError("Sketch path has fewer than 2 valid points.")

    # Preserve imported arc radius exactly by default: no auto-transition on sketch import.
    dedup_rows[0][2] = 0.0
    dedup_rows[0][3] = 0.0
    dedup_rows[-1][2] = 0.0
    dedup_rows[-1][3] = 0.0
    for i in range(1, len(dedup_rows) - 1):
        dedup_rows[i][3] = 0.0

    return [(float(x), float(y), float(rr), float(ls)) for (x, y, rr, ls) in dedup_rows]


def sketch_to_ip_points(sketch_obj, tol: float = 1e-6, z_tol: float = 1e-4):
    rows = sketch_to_alignment_rows(sketch_obj, tol=tol, z_tol=z_tol)
    out = []
    for x, y, _r, _ls in rows:
        out.append(App.Vector(float(x), float(y), 0.0))
    if len(out) < 2:
        raise ValueError("Sketch path has fewer than 2 valid points.")
    return out
