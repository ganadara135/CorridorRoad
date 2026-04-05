# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

# CorridorRoad/objects/obj_assembly_template.py
import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_project import get_length_scale

try:
    import FreeCADGui as Gui
except Exception:
    Gui = None


def _parse_bench_row(row, default_post_slope: float):
    if isinstance(row, dict):
        data = {str(k).strip().lower(): v for k, v in row.items()}
    else:
        text = str(row or "").strip()
        if not text:
            return None
        data = {}
        if "=" in text:
            for tok in [t for t in text.replace(";", "|").split("|") if str(t).strip()]:
                if "=" not in tok:
                    continue
                key, val = tok.split("=", 1)
                data[str(key).strip().lower()] = str(val).strip()
        else:
            parts = [p.strip() for p in text.split(",")]
            if len(parts) < 2:
                return None
            data = {
                "drop": parts[0],
                "width": parts[1],
                "slope": parts[2] if len(parts) >= 3 else "0",
                "post": parts[3] if len(parts) >= 4 else str(default_post_slope),
            }

    try:
        drop = max(0.0, float(data.get("drop", data.get("predrop", 0.0)) or 0.0))
        width = max(0.0, float(data.get("width", 0.0) or 0.0))
        slope = float(data.get("slope", data.get("benchslope", 0.0)) or 0.0)
        post = float(data.get("post", data.get("postslope", data.get("post_slope", default_post_slope))) or default_post_slope)
    except Exception:
        return None
    if width <= 1e-9:
        return None
    return {
        "drop": float(drop),
        "width": float(width),
        "slope": float(slope),
        "post_slope": float(post),
    }


def _serialize_bench_row(row) -> str:
    parsed = _parse_bench_row(row, 0.0)
    if parsed is None:
        return ""
    return "drop={drop:.6f}|width={width:.6f}|slope={slope:.6f}|post={post_slope:.6f}".format(**parsed)


def _collect_side_bench_rows(use_bench: bool, bench_drop: float, bench_width: float, bench_slope_pct: float, post_bench_slope_pct: float, bench_rows):
    if not bool(use_bench):
        return []
    primary = _parse_bench_row(
        {
            "drop": bench_drop,
            "width": bench_width,
            "slope": bench_slope_pct,
            "post": post_bench_slope_pct,
        },
        post_bench_slope_pct,
    )
    out = []
    for row in list(bench_rows or []):
        parsed = _parse_bench_row(row, post_bench_slope_pct)
        if parsed is not None:
            out.append(parsed)
    if out:
        if primary is None:
            return out
        first = out[0]
        tol = 1e-9
        same_as_primary = (
            abs(float(first.get("drop", 0.0) or 0.0) - float(primary.get("drop", 0.0) or 0.0)) <= tol
            and abs(float(first.get("width", 0.0) or 0.0) - float(primary.get("width", 0.0) or 0.0)) <= tol
            and abs(float(first.get("slope", 0.0) or 0.0) - float(primary.get("slope", 0.0) or 0.0)) <= tol
            and abs(float(first.get("post_slope", 0.0) or 0.0) - float(primary.get("post_slope", 0.0) or 0.0)) <= tol
        )
        return out if same_as_primary else ([primary] + out)
    if primary is not None:
        return [primary]
    return []


def _resolve_side_bench_segments(total_w: float, side_slope_pct: float, use_bench: bool, bench_drop: float, bench_width: float, bench_slope_pct: float, post_bench_slope_pct: float):
    total = max(0.0, float(total_w))
    side_slope = float(side_slope_pct)
    out = {
        "active": False,
        "pre_width": 0.0,
        "bench_width": 0.0,
        "post_width": total,
        "pre_slope": side_slope,
        "bench_slope": float(bench_slope_pct),
        "post_slope": side_slope,
    }
    if (not bool(use_bench)) or total <= 1e-9:
        return out

    bench_w = max(0.0, float(bench_width))
    if bench_w <= 1e-9:
        return out

    drop = max(0.0, float(bench_drop))
    pre_w = 0.0
    if drop > 1e-9 and abs(side_slope) > 1e-9:
        pre_w = min(total, drop * 100.0 / abs(side_slope))

    remain = max(0.0, total - pre_w)
    bench_w = min(remain, bench_w)
    if bench_w <= 1e-9:
        return out

    post_w = max(0.0, total - pre_w - bench_w)
    post_slope = float(post_bench_slope_pct)
    if post_w > 1e-9 and abs(post_slope) <= 1e-9:
        post_slope = side_slope

    out.update(
        {
            "active": True,
            "pre_width": float(pre_w),
            "bench_width": float(bench_w),
            "post_width": float(post_w),
            "pre_slope": side_slope,
            "bench_slope": float(bench_slope_pct),
            "post_slope": float(post_slope),
        }
    )
    return out


def _resolve_side_bench_profile(total_w: float, side_slope_pct: float, bench_rows, repeat_first_row_to_end: bool = False):
    total = max(0.0, float(total_w))
    side_slope = float(side_slope_pct)
    rows = list(bench_rows or [])
    segments = []
    active_rows = []
    remaining = total
    current_slope = side_slope

    def _append_bench_row(row):
        nonlocal remaining, current_slope
        spec = _resolve_side_bench_segments(
            remaining,
            current_slope,
            True,
            float(row.get("drop", 0.0) or 0.0),
            float(row.get("width", 0.0) or 0.0),
            float(row.get("slope", 0.0) or 0.0),
            float(row.get("post_slope", current_slope) or current_slope),
        )
        if not bool(spec.get("active", False)):
            return False
        pre_w = float(spec.get("pre_width", 0.0) or 0.0)
        if pre_w > 1e-9:
            segments.append({"kind": "slope", "width": pre_w, "slope": float(spec.get("pre_slope", current_slope) or current_slope)})
        bench_w = float(spec.get("bench_width", 0.0) or 0.0)
        if bench_w <= 1e-9:
            return False
        segments.append({"kind": "bench", "width": bench_w, "slope": float(spec.get("bench_slope", 0.0) or 0.0)})
        active_rows.append(dict(row))
        next_remaining = max(0.0, float(spec.get("post_width", 0.0) or 0.0))
        current_slope = float(spec.get("post_slope", current_slope) or current_slope)
        progressed = abs(float(remaining) - float(next_remaining)) > 1e-9
        remaining = next_remaining
        return progressed

    if bool(repeat_first_row_to_end) and rows:
        template_row = dict(rows[0])
        guard = 0
        while remaining > 1e-9 and guard < 512:
            guard += 1
            if not _append_bench_row(template_row):
                break
    else:
        for row in rows:
            if remaining <= 1e-9:
                break
            _append_bench_row(row)

    if remaining > 1e-9 or not segments or active_rows:
        segments.append({"kind": "slope", "width": max(remaining, total if not segments else 0.0), "slope": current_slope})

    return {
        "active": bool(active_rows),
        "segments": segments,
        "rows": active_rows,
        "bench_count": int(len(active_rows)),
        "total_width": float(sum(float(seg.get("width", 0.0) or 0.0) for seg in segments)),
    }


def _append_preview_side_points(points, edge_pt, sign_x: float, profile):
    cur = App.Vector(float(edge_pt.x), float(edge_pt.y), float(edge_pt.z))
    seg_pts = []
    for seg in list(profile.get("segments", []) or []):
        seg_w = float(seg.get("width", 0.0) or 0.0)
        if seg_w <= 1e-9:
            continue
        seg_s = float(seg.get("slope", 0.0) or 0.0)
        cur = App.Vector(cur.x + sign_x * seg_w, cur.y - seg_w * seg_s / 100.0, cur.z)
        seg_pts.append(cur)
    points.extend(seg_pts)


def ensure_assembly_template_properties(obj):
    # Hard-remove legacy thickness properties.
    for legacy_prop in ("PavementThickness", "SolidThickness"):
        try:
            if hasattr(obj, legacy_prop):
                obj.removeProperty(legacy_prop)
        except Exception:
            pass

    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)

    if not hasattr(obj, "LeftWidth"):
        obj.addProperty("App::PropertyFloat", "LeftWidth", "Assembly", "Width to left side from centerline (m)")
        obj.LeftWidth = 4.0 * scale
    if not hasattr(obj, "RightWidth"):
        obj.addProperty("App::PropertyFloat", "RightWidth", "Assembly", "Width to right side from centerline (m)")
        obj.RightWidth = 4.0 * scale

    if not hasattr(obj, "LeftSlopePct"):
        obj.addProperty("App::PropertyFloat", "LeftSlopePct", "Assembly", "Cross slope (%) on left side (downward)")
        obj.LeftSlopePct = 2.0
    if not hasattr(obj, "RightSlopePct"):
        obj.addProperty("App::PropertyFloat", "RightSlopePct", "Assembly", "Cross slope (%) on right side (downward)")
        obj.RightSlopePct = 2.0

    if not hasattr(obj, "UseSideSlopes"):
        obj.addProperty("App::PropertyBool", "UseSideSlopes", "Assembly", "Enable side slope wings")
        obj.UseSideSlopes = False
    if not hasattr(obj, "LeftSideWidth"):
        obj.addProperty("App::PropertyFloat", "LeftSideWidth", "Assembly", "Left side slope horizontal width (m)")
        obj.LeftSideWidth = 0.0
    if not hasattr(obj, "RightSideWidth"):
        obj.addProperty("App::PropertyFloat", "RightSideWidth", "Assembly", "Right side slope horizontal width (m)")
        obj.RightSideWidth = 0.0
    if not hasattr(obj, "LeftSideSlopePct"):
        obj.addProperty("App::PropertyFloat", "LeftSideSlopePct", "Assembly", "Left side slope (%) downward outward")
        obj.LeftSideSlopePct = 50.0
    if not hasattr(obj, "RightSideSlopePct"):
        obj.addProperty("App::PropertyFloat", "RightSideSlopePct", "Assembly", "Right side slope (%) downward outward")
        obj.RightSideSlopePct = 50.0
    if not hasattr(obj, "UseLeftBench"):
        obj.addProperty("App::PropertyBool", "UseLeftBench", "Assembly", "Enable a left-side mid-slope bench")
        obj.UseLeftBench = False
    if not hasattr(obj, "UseRightBench"):
        obj.addProperty("App::PropertyBool", "UseRightBench", "Assembly", "Enable a right-side mid-slope bench")
        obj.UseRightBench = False
    if not hasattr(obj, "LeftBenchDrop"):
        obj.addProperty("App::PropertyFloat", "LeftBenchDrop", "Assembly", "Vertical drop before the left bench starts (m)")
        obj.LeftBenchDrop = 1.0 * scale
    if not hasattr(obj, "RightBenchDrop"):
        obj.addProperty("App::PropertyFloat", "RightBenchDrop", "Assembly", "Vertical drop before the right bench starts (m)")
        obj.RightBenchDrop = 1.0 * scale
    if not hasattr(obj, "LeftBenchWidth"):
        obj.addProperty("App::PropertyFloat", "LeftBenchWidth", "Assembly", "Left bench width (m)")
        obj.LeftBenchWidth = 1.5 * scale
    if not hasattr(obj, "RightBenchWidth"):
        obj.addProperty("App::PropertyFloat", "RightBenchWidth", "Assembly", "Right bench width (m)")
        obj.RightBenchWidth = 1.5 * scale
    if not hasattr(obj, "LeftBenchSlopePct"):
        obj.addProperty("App::PropertyFloat", "LeftBenchSlopePct", "Assembly", "Left bench slope (%)")
        obj.LeftBenchSlopePct = 0.0
    if not hasattr(obj, "RightBenchSlopePct"):
        obj.addProperty("App::PropertyFloat", "RightBenchSlopePct", "Assembly", "Right bench slope (%)")
        obj.RightBenchSlopePct = 0.0
    if not hasattr(obj, "LeftPostBenchSlopePct"):
        obj.addProperty("App::PropertyFloat", "LeftPostBenchSlopePct", "Assembly", "Left slope (%) after the bench")
        obj.LeftPostBenchSlopePct = 50.0
    if not hasattr(obj, "RightPostBenchSlopePct"):
        obj.addProperty("App::PropertyFloat", "RightPostBenchSlopePct", "Assembly", "Right slope (%) after the bench")
        obj.RightPostBenchSlopePct = 50.0
    if not hasattr(obj, "LeftBenchRows"):
        obj.addProperty("App::PropertyStringList", "LeftBenchRows", "Assembly", "Unified left bench rows (drop,width,slope,post)")
        obj.LeftBenchRows = []
    if not hasattr(obj, "RightBenchRows"):
        obj.addProperty("App::PropertyStringList", "RightBenchRows", "Assembly", "Unified right bench rows (drop,width,slope,post)")
        obj.RightBenchRows = []
    if not hasattr(obj, "LeftBenchRepeatToDaylight"):
        obj.addProperty("App::PropertyBool", "LeftBenchRepeatToDaylight", "Assembly", "Repeat the first left bench row until daylight")
        obj.LeftBenchRepeatToDaylight = False
    if not hasattr(obj, "RightBenchRepeatToDaylight"):
        obj.addProperty("App::PropertyBool", "RightBenchRepeatToDaylight", "Assembly", "Repeat the first right bench row until daylight")
        obj.RightBenchRepeatToDaylight = False
    if not hasattr(obj, "UseDaylightToTerrain"):
        obj.addProperty("App::PropertyBool", "UseDaylightToTerrain", "Assembly", "Use terrain-daylight for side slopes")
        obj.UseDaylightToTerrain = False
    if not hasattr(obj, "DaylightSearchStep"):
        obj.addProperty("App::PropertyFloat", "DaylightSearchStep", "Assembly", "Search step for terrain-daylight (m)")
        obj.DaylightSearchStep = 1.0 * scale
    if not hasattr(obj, "DaylightMaxSearchWidth"):
        obj.addProperty("App::PropertyFloat", "DaylightMaxSearchWidth", "Assembly", "Max search width for terrain-daylight (m)")
        obj.DaylightMaxSearchWidth = 200.0 * scale
    if not hasattr(obj, "DaylightMaxWidthDelta"):
        obj.addProperty(
            "App::PropertyFloat",
            "DaylightMaxWidthDelta",
            "Assembly",
            "Max daylight-width change allowed between neighboring sections (m, 0=off)",
        )
        obj.DaylightMaxWidthDelta = 6.0 * scale
    if not hasattr(obj, "DaylightMaxTriangles"):
        obj.addProperty("App::PropertyInteger", "DaylightMaxTriangles", "Assembly", "Max triangles used for daylight sampler")
        obj.DaylightMaxTriangles = 300000

    if not hasattr(obj, "HeightLeft"):
        obj.addProperty("App::PropertyFloat", "HeightLeft", "Assembly", "Left depth for corridor solid (m, downward)")
        obj.HeightLeft = 0.30 * scale

    if not hasattr(obj, "HeightRight"):
        obj.addProperty("App::PropertyFloat", "HeightRight", "Assembly", "Right depth for corridor solid (m, downward)")
        obj.HeightRight = 0.30 * scale

    try:
        obj.setGroupOfProperty("HeightLeft", "Assembly")
        obj.setGroupOfProperty("HeightRight", "Assembly")
    except Exception:
        pass

    if not hasattr(obj, "ShowTemplateWire"):
        obj.addProperty("App::PropertyBool", "ShowTemplateWire", "Display", "Show template wire (local profile view)")
        obj.ShowTemplateWire = True

    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"
    if not hasattr(obj, "PracticalRole"):
        obj.addProperty("App::PropertyString", "PracticalRole", "Result", "Practical engineering role summary")
        obj.PracticalRole = "assembly_core"
    if not hasattr(obj, "GeometryDrivingFieldSummary"):
        obj.addProperty("App::PropertyString", "GeometryDrivingFieldSummary", "Result", "Geometry-driving field summary")
        obj.GeometryDrivingFieldSummary = ""
    if not hasattr(obj, "AnalysisDrivingFieldSummary"):
        obj.addProperty("App::PropertyString", "AnalysisDrivingFieldSummary", "Result", "Analysis-driving field summary")
        obj.AnalysisDrivingFieldSummary = ""
    if not hasattr(obj, "ReportOnlyFieldSummary"):
        obj.addProperty("App::PropertyString", "ReportOnlyFieldSummary", "Result", "Report-only field summary")
        obj.ReportOnlyFieldSummary = "-"


class AssemblyTemplate:
    """
    Cross-section template parameters for section generation.
    """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "AssemblyTemplate"
        self._suspend_recompute = False
        ensure_assembly_template_properties(obj)

    def execute(self, obj):
        ensure_assembly_template_properties(obj)
        try:
            if not bool(getattr(obj, "ShowTemplateWire", True)):
                obj.Shape = Part.Shape()
                obj.PracticalRole = "assembly_core"
                obj.GeometryDrivingFieldSummary = "LeftWidth,RightWidth,LeftSlopePct,RightSlopePct,HeightLeft,HeightRight,LeftSideWidth,RightSideWidth,LeftSideSlopePct,RightSideSlopePct,UseLeftBench,UseRightBench,LeftBenchDrop,RightBenchDrop,LeftBenchWidth,RightBenchWidth,LeftBenchSlopePct,RightBenchSlopePct,LeftPostBenchSlopePct,RightPostBenchSlopePct,LeftBenchRows,RightBenchRows,LeftBenchRepeatToDaylight,RightBenchRepeatToDaylight"
                obj.AnalysisDrivingFieldSummary = "UseSideSlopes,UseDaylightToTerrain,DaylightSearchStep,DaylightMaxSearchWidth,DaylightMaxWidthDelta,DaylightMaxTriangles"
                obj.ReportOnlyFieldSummary = "-"
                obj.Status = "Hidden | role=assembly_core"
                return

            lw = max(0.0, float(getattr(obj, "LeftWidth", 0.0)))
            rw = max(0.0, float(getattr(obj, "RightWidth", 0.0)))
            ls = float(getattr(obj, "LeftSlopePct", 0.0))
            rs = float(getattr(obj, "RightSlopePct", 0.0))
            hl = max(0.0, float(getattr(obj, "HeightLeft", 0.0)))
            hr = max(0.0, float(getattr(obj, "HeightRight", 0.0)))
            use_ss = bool(getattr(obj, "UseSideSlopes", False))
            lsw = max(0.0, float(getattr(obj, "LeftSideWidth", 0.0)))
            rsw = max(0.0, float(getattr(obj, "RightSideWidth", 0.0)))
            lss = float(getattr(obj, "LeftSideSlopePct", 0.0))
            rss = float(getattr(obj, "RightSideSlopePct", 0.0))
            left_bench_rows = _collect_side_bench_rows(
                bool(getattr(obj, "UseLeftBench", False)),
                float(getattr(obj, "LeftBenchDrop", 0.0) or 0.0),
                float(getattr(obj, "LeftBenchWidth", 0.0) or 0.0),
                float(getattr(obj, "LeftBenchSlopePct", 0.0) or 0.0),
                float(getattr(obj, "LeftPostBenchSlopePct", lss) or lss),
                list(getattr(obj, "LeftBenchRows", []) or []),
            )
            right_bench_rows = _collect_side_bench_rows(
                bool(getattr(obj, "UseRightBench", False)),
                float(getattr(obj, "RightBenchDrop", 0.0) or 0.0),
                float(getattr(obj, "RightBenchWidth", 0.0) or 0.0),
                float(getattr(obj, "RightBenchSlopePct", 0.0) or 0.0),
                float(getattr(obj, "RightPostBenchSlopePct", rss) or rss),
                list(getattr(obj, "RightBenchRows", []) or []),
            )
            left_bench = _resolve_side_bench_profile(
                lsw,
                lss,
                left_bench_rows,
                repeat_first_row_to_end=bool(getattr(obj, "LeftBenchRepeatToDaylight", False)),
            )
            right_bench = _resolve_side_bench_profile(
                rsw,
                rss,
                right_bench_rows,
                repeat_first_row_to_end=bool(getattr(obj, "RightBenchRepeatToDaylight", False)),
            )

            dz_l = -lw * ls / 100.0
            dz_r = -rw * rs / 100.0

            p_l = App.Vector(+lw, dz_l, 0.0)
            p_c = App.Vector(0.0, 0.0, 0.0)
            p_r = App.Vector(-rw, dz_r, 0.0)

            top_pts = [p_l, p_c, p_r]
            if use_ss and (lsw > 1e-9):
                if bool(left_bench.get("active", False)):
                    left_pts = []
                    _append_preview_side_points(left_pts, p_l, 1.0, left_bench)
                    top_pts = list(reversed(left_pts)) + top_pts
                else:
                    p_lt = App.Vector(+lw + lsw, dz_l - lsw * lss / 100.0, 0.0)
                    top_pts = [p_lt] + top_pts
            if use_ss and (rsw > 1e-9):
                if bool(right_bench.get("active", False)):
                    right_pts = []
                    _append_preview_side_points(right_pts, p_r, -1.0, right_bench)
                    top_pts = top_pts + right_pts
                else:
                    p_rt = App.Vector(-(rw + rsw), dz_r - rsw * rss / 100.0, 0.0)
                    top_pts = top_pts + [p_rt]

            # Display both crown line and solid-depth envelope so HeightLeft/Right
            # edits are visible immediately in 3D view.
            if max(hl, hr) <= 1e-9:
                obj.Shape = Part.makePolygon(top_pts)
            else:
                n_top = len(top_pts)
                q_pts = []
                for i, tp in enumerate(top_pts):
                    if n_top <= 1:
                        alpha = 0.5
                    else:
                        alpha = float(i) / float(n_top - 1)
                    h = (1.0 - alpha) * hl + alpha * hr
                    q_pts.append(App.Vector(tp.x, tp.y - h, tp.z))
                obj.Shape = Part.makePolygon(list(top_pts) + list(reversed(q_pts)) + [top_pts[0]])
            obj.PracticalRole = "assembly_core"
            obj.GeometryDrivingFieldSummary = "LeftWidth,RightWidth,LeftSlopePct,RightSlopePct,HeightLeft,HeightRight,LeftSideWidth,RightSideWidth,LeftSideSlopePct,RightSideSlopePct,UseLeftBench,UseRightBench,LeftBenchDrop,RightBenchDrop,LeftBenchWidth,RightBenchWidth,LeftBenchSlopePct,RightBenchSlopePct,LeftPostBenchSlopePct,RightPostBenchSlopePct,LeftBenchRows,RightBenchRows,LeftBenchRepeatToDaylight,RightBenchRepeatToDaylight"
            obj.AnalysisDrivingFieldSummary = "UseSideSlopes,UseDaylightToTerrain,DaylightSearchStep,DaylightMaxSearchWidth,DaylightMaxWidthDelta,DaylightMaxTriangles"
            obj.ReportOnlyFieldSummary = "-"
            left_count = int(len(list(left_bench_rows or [])))
            right_count = int(len(list(right_bench_rows or [])))
            bench_mode = "-"
            if left_count > 0 and right_count > 0:
                bench_mode = f"both({left_count}/{right_count})"
            elif left_count > 0:
                bench_mode = f"left({left_count})"
            elif right_count > 0:
                bench_mode = f"right({right_count})"
            obj.Status = f"OK | role=assembly_core | bench={bench_mode}"
        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if bool(getattr(self, "_suspend_recompute", False)):
            return
        if prop in (
            "LeftWidth",
            "RightWidth",
            "LeftSlopePct",
            "RightSlopePct",
            "UseSideSlopes",
            "LeftSideWidth",
            "RightSideWidth",
            "LeftSideSlopePct",
            "RightSideSlopePct",
            "UseLeftBench",
            "UseRightBench",
            "LeftBenchDrop",
            "RightBenchDrop",
            "LeftBenchWidth",
            "RightBenchWidth",
            "LeftBenchSlopePct",
            "RightBenchSlopePct",
            "LeftPostBenchSlopePct",
            "RightPostBenchSlopePct",
            "LeftBenchRows",
            "RightBenchRows",
            "LeftBenchRepeatToDaylight",
            "RightBenchRepeatToDaylight",
            "UseDaylightToTerrain",
            "DaylightSearchStep",
            "DaylightMaxSearchWidth",
            "DaylightMaxWidthDelta",
            "DaylightMaxTriangles",
            "HeightLeft",
            "HeightRight",
            "ShowTemplateWire",
        ):
            try:
                if prop == "UseSideSlopes" and bool(getattr(obj, "UseSideSlopes", False)):
                    # Keep side-slope preview visible by seeding practical defaults
                    # when user enables side slopes with zero widths.
                    lsw = max(0.0, float(getattr(obj, "LeftSideWidth", 0.0)))
                    rsw = max(0.0, float(getattr(obj, "RightSideWidth", 0.0)))
                    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
                    if lsw <= 1e-9:
                        obj.LeftSideWidth = max(2.0 * scale, 0.5 * max(0.0, float(getattr(obj, "LeftWidth", 0.0))))
                    if rsw <= 1e-9:
                        obj.RightSideWidth = max(2.0 * scale, 0.5 * max(0.0, float(getattr(obj, "RightWidth", 0.0))))
                scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
                if prop == "UseLeftBench" and bool(getattr(obj, "UseLeftBench", False)):
                    if float(getattr(obj, "LeftBenchWidth", 0.0) or 0.0) <= 1e-9:
                        obj.LeftBenchWidth = 1.5 * scale
                    if float(getattr(obj, "LeftBenchDrop", 0.0) or 0.0) <= 1e-9:
                        obj.LeftBenchDrop = 1.0 * scale
                    if abs(float(getattr(obj, "LeftPostBenchSlopePct", 0.0) or 0.0)) <= 1e-9:
                        obj.LeftPostBenchSlopePct = float(getattr(obj, "LeftSideSlopePct", 50.0) or 50.0)
                if prop == "UseRightBench" and bool(getattr(obj, "UseRightBench", False)):
                    if float(getattr(obj, "RightBenchWidth", 0.0) or 0.0) <= 1e-9:
                        obj.RightBenchWidth = 1.5 * scale
                    if float(getattr(obj, "RightBenchDrop", 0.0) or 0.0) <= 1e-9:
                        obj.RightBenchDrop = 1.0 * scale
                    if abs(float(getattr(obj, "RightPostBenchSlopePct", 0.0) or 0.0)) <= 1e-9:
                        obj.RightPostBenchSlopePct = float(getattr(obj, "RightSideSlopePct", 50.0) or 50.0)
                obj.touch()
                if obj.Document is not None:
                    # Propagate template edits to linked SectionSet objects.
                    for o in list(obj.Document.Objects):
                        try:
                            if getattr(o, "AssemblyTemplate", None) == obj:
                                o.touch()
                        except Exception:
                            pass
                    if Gui is not None:
                        Gui.updateGui()
            except Exception:
                pass


class ViewProviderAssemblyTemplate:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Wireframe"
            vobj.LineWidth = 2
        except Exception:
            pass

    def getIcon(self):
        return ""

    def updateData(self, obj, prop):
        return

    def onChanged(self, vobj, prop):
        return

    def getDisplayModes(self, vobj):
        return ["Wireframe", "Flat Lines"]

    def getDefaultDisplayMode(self):
        return "Wireframe"

    def setDisplayMode(self, mode):
        return mode
