import math

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects.obj_project import get_length_scale

try:
    import FreeCADGui as Gui
except Exception:
    Gui = None


ALLOWED_COMPONENT_TYPES = (
    "lane",
    "shoulder",
    "median",
    "sidewalk",
    "bike_lane",
    "curb",
    "green_strip",
    "gutter",
    "ditch",
    "berm",
)
ALLOWED_COMPONENT_SIDES = ("left", "right", "center", "both")
ALLOWED_PAVEMENT_LAYER_TYPES = ("surface", "binder", "base", "subbase", "subgrade")


def _safe_float(v, default: float = 0.0) -> float:
    try:
        x = float(v)
    except Exception:
        return float(default)
    if not math.isfinite(x):
        return float(default)
    return float(x)


def _safe_int(v, default: int = 0) -> int:
    try:
        return int(round(float(v)))
    except Exception:
        return int(default)


def _as_bool_flag(v) -> bool:
    try:
        return bool(int(v))
    except Exception:
        return bool(v)


def _default_component_data(scale: float):
    return {
        "ComponentIds": ["LANE-L", "SHL-L", "LANE-R", "SHL-R"],
        "ComponentTypes": ["lane", "shoulder", "lane", "shoulder"],
        "ComponentSides": ["left", "left", "right", "right"],
        "ComponentWidths": [3.50 * scale, 1.50 * scale, 3.50 * scale, 1.50 * scale],
        "ComponentCrossSlopes": [2.0, 4.0, 2.0, 4.0],
        "ComponentHeights": [0.0, 0.0, 0.0, 0.0],
        "ComponentOffsets": [0.0, 0.0, 0.0, 0.0],
        "ComponentOrders": [10, 20, 10, 20],
        "ComponentEnabled": [1, 1, 1, 1],
    }


def _component_array_specs(scale: float):
    defaults = _default_component_data(scale)
    return (
        ("ComponentIds", "App::PropertyStringList", defaults["ComponentIds"], "Ordered component identifiers"),
        ("ComponentTypes", "App::PropertyStringList", defaults["ComponentTypes"], "Component types"),
        ("ComponentSides", "App::PropertyStringList", defaults["ComponentSides"], "Component side assignments"),
        ("ComponentWidths", "App::PropertyFloatList", defaults["ComponentWidths"], "Component widths (m)"),
        ("ComponentCrossSlopes", "App::PropertyFloatList", defaults["ComponentCrossSlopes"], "Cross slopes (%)"),
        ("ComponentHeights", "App::PropertyFloatList", defaults["ComponentHeights"], "Vertical steps/heights (m)"),
        ("ComponentOffsets", "App::PropertyFloatList", defaults["ComponentOffsets"], "Optional local lateral offsets (m)"),
        ("ComponentOrders", "App::PropertyIntegerList", defaults["ComponentOrders"], "Sort order per side"),
        ("ComponentEnabled", "App::PropertyIntegerList", defaults["ComponentEnabled"], "Enabled flags (1/0)"),
    )


def _default_pavement_data(scale: float):
    return {
        "PavementLayerIds": ["SURF", "BINDER", "BASE", "SUBBASE"],
        "PavementLayerTypes": ["surface", "binder", "base", "subbase"],
        "PavementLayerThicknesses": [0.05 * scale, 0.07 * scale, 0.20 * scale, 0.25 * scale],
        "PavementLayerEnabled": [1, 1, 1, 1],
    }


def _pavement_array_specs(scale: float):
    defaults = _default_pavement_data(scale)
    return (
        ("PavementLayerIds", "App::PropertyStringList", defaults["PavementLayerIds"], "Pavement layer identifiers"),
        ("PavementLayerTypes", "App::PropertyStringList", defaults["PavementLayerTypes"], "Pavement layer types"),
        ("PavementLayerThicknesses", "App::PropertyFloatList", defaults["PavementLayerThicknesses"], "Pavement layer thicknesses (m)"),
        ("PavementLayerEnabled", "App::PropertyIntegerList", defaults["PavementLayerEnabled"], "Pavement layer enabled flags (1/0)"),
    )


def ensure_typical_section_template_properties(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
    for name, ptype, default, doc in _component_array_specs(scale):
        if not hasattr(obj, name):
            obj.addProperty(ptype, name, "Components", doc)
            setattr(obj, name, list(default))
    for name, ptype, default, doc in _pavement_array_specs(scale):
        if not hasattr(obj, name):
            obj.addProperty(ptype, name, "Pavement", doc)
            setattr(obj, name, list(default))

    if not hasattr(obj, "PreviewSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "PreviewSchemaVersion", "Result", "Preview schema version")
        obj.PreviewSchemaVersion = 2
    if not hasattr(obj, "ComponentCount"):
        obj.addProperty("App::PropertyInteger", "ComponentCount", "Result", "Total component row count")
        obj.ComponentCount = 0
    if not hasattr(obj, "EnabledComponentCount"):
        obj.addProperty("App::PropertyInteger", "EnabledComponentCount", "Result", "Enabled component row count")
        obj.EnabledComponentCount = 0
    if not hasattr(obj, "PavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "PavementLayerCount", "Result", "Total pavement layer row count")
        obj.PavementLayerCount = 0
    if not hasattr(obj, "EnabledPavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "EnabledPavementLayerCount", "Result", "Enabled pavement layer row count")
        obj.EnabledPavementLayerCount = 0
    if not hasattr(obj, "PavementTotalThickness"):
        obj.addProperty("App::PropertyFloat", "PavementTotalThickness", "Result", "Enabled pavement total thickness (m)")
        obj.PavementTotalThickness = 0.0
    if not hasattr(obj, "LeftEdgeComponentType"):
        obj.addProperty("App::PropertyString", "LeftEdgeComponentType", "Result", "Outermost left component type")
        obj.LeftEdgeComponentType = ""
    if not hasattr(obj, "RightEdgeComponentType"):
        obj.addProperty("App::PropertyString", "RightEdgeComponentType", "Result", "Outermost right component type")
        obj.RightEdgeComponentType = ""
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Execution status")
        obj.Status = "Idle"
    if not hasattr(obj, "ShowPreviewWire"):
        obj.addProperty("App::PropertyBool", "ShowPreviewWire", "Display", "Show preview wire")
        obj.ShowPreviewWire = True


def _normalized_component_arrays(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
    specs = _component_array_specs(scale)
    lengths = []
    for name, _ptype, default, _doc in specs:
        raw = list(getattr(obj, name, list(default)) or [])
        lengths.append(len(raw))
    n = max(lengths or [0])
    if n <= 0:
        n = len(_default_component_data(scale)["ComponentIds"])

    out = {}
    for name, _ptype, default, _doc in specs:
        vals = list(getattr(obj, name, list(default)) or [])
        if len(vals) < n:
            fill = list(default)
            while len(vals) < n:
                idx = len(vals)
                vals.append(fill[idx] if idx < len(fill) else fill[-1])
        elif len(vals) > n:
            vals = vals[:n]
        out[name] = vals
    return out


def _normalized_pavement_arrays(obj):
    scale = get_length_scale(getattr(obj, "Document", None), default=1.0)
    specs = _pavement_array_specs(scale)
    lengths = []
    for name, _ptype, default, _doc in specs:
        raw = list(getattr(obj, name, list(default)) or [])
        lengths.append(len(raw))
    n = max(lengths or [0])
    if n <= 0:
        n = len(_default_pavement_data(scale)["PavementLayerIds"])

    out = {}
    for name, _ptype, default, _doc in specs:
        vals = list(getattr(obj, name, list(default)) or [])
        if len(vals) < n:
            fill = list(default)
            while len(vals) < n:
                idx = len(vals)
                vals.append(fill[idx] if idx < len(fill) else fill[-1])
        elif len(vals) > n:
            vals = vals[:n]
        out[name] = vals
    return out


def component_rows(obj):
    ensure_typical_section_template_properties(obj)
    data = _normalized_component_arrays(obj)
    rows = []
    count = len(data.get("ComponentIds", []) or [])
    for i in range(count):
        row = {
            "Id": str(data["ComponentIds"][i] or "").strip() or f"COMP-{i+1:02d}",
            "Type": str(data["ComponentTypes"][i] or "").strip().lower() or "lane",
            "Side": str(data["ComponentSides"][i] or "").strip().lower() or "left",
            "Width": max(0.0, _safe_float(data["ComponentWidths"][i], default=0.0)),
            "CrossSlopePct": _safe_float(data["ComponentCrossSlopes"][i], default=0.0),
            "Height": _safe_float(data["ComponentHeights"][i], default=0.0),
            "Offset": _safe_float(data["ComponentOffsets"][i], default=0.0),
            "Order": _safe_int(data["ComponentOrders"][i], default=i + 1),
            "Enabled": _as_bool_flag(data["ComponentEnabled"][i]),
            "_Index": i,
        }
        if row["Type"] == "bench":
            row["Type"] = "berm"
        rows.append(row)
    return rows


def validate_components(obj):
    rows = component_rows(obj)
    issues = []
    seen = set()
    for row in rows:
        cid = str(row["Id"] or "").strip()
        if cid in seen:
            issues.append(f"Duplicate component id: {cid}")
        seen.add(cid)

        typ = str(row["Type"] or "").strip().lower()
        if typ not in ALLOWED_COMPONENT_TYPES:
            issues.append(f"{cid}: unsupported component type '{typ}'")

        side = str(row["Side"] or "").strip().lower()
        if side not in ALLOWED_COMPONENT_SIDES:
            issues.append(f"{cid}: unsupported side '{side}'")

        if float(row["Width"]) < 0.0:
            issues.append(f"{cid}: width must be >= 0")
        if not math.isfinite(float(row["CrossSlopePct"])):
            issues.append(f"{cid}: cross slope must be finite")
        if not math.isfinite(float(row["Height"])):
            issues.append(f"{cid}: height must be finite")
        if not math.isfinite(float(row["Offset"])):
            issues.append(f"{cid}: offset must be finite")
    return issues


def pavement_rows(obj):
    ensure_typical_section_template_properties(obj)
    data = _normalized_pavement_arrays(obj)
    rows = []
    count = len(data.get("PavementLayerIds", []) or [])
    for i in range(count):
        row = {
            "Id": str(data["PavementLayerIds"][i] or "").strip() or f"LAYER-{i+1:02d}",
            "Type": str(data["PavementLayerTypes"][i] or "").strip().lower() or "base",
            "Thickness": max(0.0, _safe_float(data["PavementLayerThicknesses"][i], default=0.0)),
            "Enabled": _as_bool_flag(data["PavementLayerEnabled"][i]),
            "_Index": i,
        }
        rows.append(row)
    return rows


def validate_pavement_layers(obj):
    rows = pavement_rows(obj)
    issues = []
    seen = set()
    for row in rows:
        lid = str(row["Id"] or "").strip()
        if lid in seen:
            issues.append(f"Duplicate pavement layer id: {lid}")
        seen.add(lid)
        typ = str(row["Type"] or "").strip().lower()
        if typ not in ALLOWED_PAVEMENT_LAYER_TYPES:
            issues.append(f"{lid}: unsupported pavement layer type '{typ}'")
        if float(row["Thickness"]) < 0.0:
            issues.append(f"{lid}: thickness must be >= 0")
    return issues


def _split_rows_by_side(rows):
    left = []
    right = []
    center = []
    for row in rows:
        if not bool(row.get("Enabled", True)):
            continue
        side = str(row.get("Side", "") or "").strip().lower()
        if side == "left":
            left.append(row)
        elif side == "right":
            right.append(row)
        elif side == "center":
            center.append(row)
        elif side == "both":
            lrow = dict(row)
            lrow["Side"] = "left"
            rrow = dict(row)
            rrow["Side"] = "right"
            left.append(lrow)
            right.append(rrow)
    left.sort(key=lambda r: (int(r.get("Order", 0) or 0), str(r.get("Id", ""))))
    right.sort(key=lambda r: (int(r.get("Order", 0) or 0), str(r.get("Id", ""))))
    center.sort(key=lambda r: (int(r.get("Order", 0) or 0), str(r.get("Id", ""))))
    return left, center, right


def _apply_segment(x0: float, y0: float, width: float, slope_pct: float, height: float, direction: float):
    x = float(x0)
    y = float(y0)
    h = _safe_float(height, default=0.0)
    if abs(h) > 1e-9:
        y += h
    w = max(0.0, _safe_float(width, default=0.0))
    x += float(direction) * w
    y -= w * _safe_float(slope_pct, default=0.0) / 100.0
    return x, y


def _segment_profile_points(x0: float, y0: float, row, direction: float):
    typ = str(row.get("Type", "") or "").strip().lower()
    width = max(0.0, _safe_float(row.get("Width", 0.0), default=0.0))
    slope = _safe_float(row.get("CrossSlopePct", 0.0), default=0.0)
    height = _safe_float(row.get("Height", 0.0), default=0.0)
    pts = []
    x = float(x0)
    y = float(y0)

    if typ == "curb":
        if abs(height) > 1e-9:
            y += height
            pts.append(App.Vector(x, y, 0.0))
        x, y = _apply_segment(x, y, width, slope, 0.0, direction)
        pts.append(App.Vector(x, y, 0.0))
        return pts

    if typ == "ditch" and width > 1e-9 and abs(height) > 1e-9:
        half_w = 0.5 * width
        x_mid = x + float(direction) * half_w
        y_mid = y - abs(height)
        pts.append(App.Vector(x_mid, y_mid, 0.0))
        x_end = x + float(direction) * width
        y_end = y - (width * slope / 100.0)
        pts.append(App.Vector(x_end, y_end, 0.0))
        return pts

    if typ == "berm":
        x, y = _apply_segment(x, y, width, 0.0, height, direction)
        pts.append(App.Vector(x, y, 0.0))
        return pts

    x, y = _apply_segment(x, y, width, slope, height, direction)
    pts.append(App.Vector(x, y, 0.0))
    return pts


def build_top_profile(obj):
    rows = component_rows(obj)
    left_rows, center_rows, right_rows = _split_rows_by_side(rows)

    left_pts = [App.Vector(0.0, 0.0, 0.0)]
    right_pts = [App.Vector(0.0, 0.0, 0.0)]
    x_left = 0.0
    y_left = 0.0
    x_right = 0.0
    y_right = 0.0

    for row in center_rows:
        half_w = 0.5 * max(0.0, float(row.get("Width", 0.0) or 0.0))
        slope = float(row.get("CrossSlopePct", 0.0) or 0.0)
        height = float(row.get("Height", 0.0) or 0.0)
        x_left, y_left = _apply_segment(x_left, y_left, half_w, slope, height, +1.0)
        x_right, y_right = _apply_segment(x_right, y_right, half_w, slope, height, -1.0)
        left_pts.append(App.Vector(x_left, y_left, 0.0))
        right_pts.append(App.Vector(x_right, y_right, 0.0))

    for row in left_rows:
        x_left += float(row.get("Offset", 0.0) or 0.0)
        seg_pts = _segment_profile_points(x_left, y_left, row, +1.0)
        if seg_pts:
            left_pts.extend(seg_pts)
            x_left = float(seg_pts[-1].x)
            y_left = float(seg_pts[-1].y)

    for row in right_rows:
        x_right -= float(row.get("Offset", 0.0) or 0.0)
        seg_pts = _segment_profile_points(x_right, y_right, row, -1.0)
        if seg_pts:
            right_pts.extend(seg_pts)
            x_right = float(seg_pts[-1].x)
            y_right = float(seg_pts[-1].y)

    top_pts = list(reversed(left_pts[1:])) + [left_pts[0]] + right_pts[1:]
    cleaned = []
    for pt in top_pts:
        if not cleaned or (pt - cleaned[-1]).Length > 1e-9:
            cleaned.append(pt)
    return cleaned


def build_pavement_layer_shapes(obj):
    top_pts = build_top_profile(obj)
    if len(top_pts) < 2:
        return []

    layers = [r for r in pavement_rows(obj) if bool(r.get("Enabled", True)) and float(r.get("Thickness", 0.0) or 0.0) > 1e-9]
    if not layers:
        return []

    shapes = []
    prev_pts = [App.Vector(float(p.x), float(p.y), float(p.z)) for p in top_pts]
    cum_thk = 0.0
    for row in layers:
        cum_thk += max(0.0, float(row.get("Thickness", 0.0) or 0.0))
        bot_pts = [App.Vector(float(p.x), float(p.y) - cum_thk, float(p.z)) for p in top_pts]
        poly = list(prev_pts) + list(reversed(bot_pts))
        if poly:
            poly.append(prev_pts[0])
        try:
            shapes.append(Part.Face(Part.makePolygon(poly)))
        except Exception:
            try:
                shapes.append(Part.makePolygon(bot_pts))
            except Exception:
                pass
        prev_pts = bot_pts
    return shapes


class TypicalSectionTemplate:
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "TypicalSectionTemplate"
        ensure_typical_section_template_properties(obj)

    def execute(self, obj):
        ensure_typical_section_template_properties(obj)
        try:
            rows = component_rows(obj)
            issues = validate_components(obj)
            pav_rows = pavement_rows(obj)
            pav_issues = validate_pavement_layers(obj)
            enabled_count = sum(1 for r in rows if bool(r.get("Enabled", True)))
            pav_enabled_count = sum(1 for r in pav_rows if bool(r.get("Enabled", True)))
            pav_total_thk = sum(float(r.get("Thickness", 0.0) or 0.0) for r in pav_rows if bool(r.get("Enabled", True)))
            left_rows, _center_rows, right_rows = _split_rows_by_side(rows)
            obj.ComponentCount = int(len(rows))
            obj.EnabledComponentCount = int(enabled_count)
            obj.PavementLayerCount = int(len(pav_rows))
            obj.EnabledPavementLayerCount = int(pav_enabled_count)
            obj.PavementTotalThickness = float(pav_total_thk)
            if hasattr(obj, "PavementPreviewCount"):
                obj.PavementPreviewCount = 0
            obj.LeftEdgeComponentType = str(left_rows[-1].get("Type", "") or "") if left_rows else ""
            obj.RightEdgeComponentType = str(right_rows[-1].get("Type", "") or "") if right_rows else ""
            obj.PreviewSchemaVersion = 2

            if not bool(getattr(obj, "ShowPreviewWire", True)):
                obj.Shape = Part.Shape()
                obj.Status = (
                    f"Hidden: edges=({obj.LeftEdgeComponentType or '-'}, "
                    f"{obj.RightEdgeComponentType or '-'}) "
                    f"pavement={obj.PavementTotalThickness:.3f}m"
                )
                return

            pts = build_top_profile(obj)
            if len(pts) < 2:
                obj.Shape = Part.Shape()
                obj.Status = "WARN: No enabled components."
                return

            obj.Shape = Part.makePolygon(pts)
            all_issues = list(issues) + list(pav_issues)
            if all_issues:
                obj.Status = "WARN: " + " | ".join(all_issues[:4])
            else:
                obj.Status = (
                    f"OK: {enabled_count}/{len(rows)} components enabled; "
                    f"edges=({obj.LeftEdgeComponentType or '-'}, {obj.RightEdgeComponentType or '-'}) "
                    f"pavement={obj.PavementTotalThickness:.3f}m ({pav_enabled_count}/{len(pav_rows)} layers)"
                )
        except Exception as ex:
            obj.Shape = Part.Shape()
            if hasattr(obj, "PavementPreviewCount"):
                obj.PavementPreviewCount = 0
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if prop in (
            "ComponentIds",
            "ComponentTypes",
            "ComponentSides",
            "ComponentWidths",
            "ComponentCrossSlopes",
            "ComponentHeights",
            "ComponentOffsets",
            "ComponentOrders",
            "ComponentEnabled",
            "PavementLayerIds",
            "PavementLayerTypes",
            "PavementLayerThicknesses",
            "PavementLayerEnabled",
            "ShowPreviewWire",
        ):
            try:
                obj.touch()
                if obj.Document is not None and Gui is not None:
                    Gui.updateGui()
            except Exception:
                pass


class ViewProviderTypicalSectionTemplate:
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


def ensure_typical_section_pavement_display_properties(obj):
    if not hasattr(obj, "SourceTypicalSection"):
        obj.addProperty("App::PropertyLink", "SourceTypicalSection", "Display", "Source TypicalSectionTemplate")
    if not hasattr(obj, "LayerCount"):
        obj.addProperty("App::PropertyInteger", "LayerCount", "Result", "Enabled pavement layer count")
        obj.LayerCount = 0
    if not hasattr(obj, "TotalThickness"):
        obj.addProperty("App::PropertyFloat", "TotalThickness", "Result", "Enabled pavement total thickness (m)")
        obj.TotalThickness = 0.0
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Display generation status")
        obj.Status = "Idle"


class TypicalSectionPavementDisplay:
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "TypicalSectionPavementDisplay"
        ensure_typical_section_pavement_display_properties(obj)

    def execute(self, obj):
        ensure_typical_section_pavement_display_properties(obj)
        try:
            src = getattr(obj, "SourceTypicalSection", None)
            if src is None:
                obj.Shape = Part.Shape()
                obj.LayerCount = 0
                obj.TotalThickness = 0.0
                obj.Status = "Missing source TypicalSectionTemplate"
                return

            enabled_layers = [r for r in pavement_rows(src) if bool(r.get("Enabled", True)) and float(r.get("Thickness", 0.0) or 0.0) > 1e-9]
            obj.LayerCount = int(len(enabled_layers))
            obj.TotalThickness = float(sum(float(r.get("Thickness", 0.0) or 0.0) for r in enabled_layers))

            shapes = build_pavement_layer_shapes(src)
            if not shapes:
                obj.Shape = Part.Shape()
                obj.Status = "No enabled pavement layers"
                return

            obj.Shape = Part.Compound(shapes)
            obj.Status = f"OK: {obj.LayerCount} layers, total={obj.TotalThickness:.3f}m"
        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.LayerCount = 0
            obj.TotalThickness = 0.0
            obj.Status = f"ERROR: {ex}"


class ViewProviderTypicalSectionPavementDisplay:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Flat Lines"
            vobj.LineWidth = 1
            vobj.ShapeColor = (0.80, 0.66, 0.30)
            vobj.Transparency = 55
        except Exception:
            pass

    def getIcon(self):
        return ""

    def updateData(self, obj, prop):
        return

    def onChanged(self, vobj, prop):
        return

    def getDisplayModes(self, vobj):
        return ["Flat Lines", "Shaded", "Wireframe"]

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode
