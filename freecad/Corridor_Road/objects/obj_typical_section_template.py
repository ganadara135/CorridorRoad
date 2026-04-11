import math

import FreeCAD as App
import Part

from freecad.Corridor_Road.objects import unit_policy as _units

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
ALLOWED_DITCH_SHAPES = ("", "v", "u", "trapezoid")
ALLOWED_PAVEMENT_LAYER_TYPES = ("surface", "binder", "base", "subbase", "subgrade")
ROADSIDE_ADVANCED_TYPES = ("curb", "ditch", "berm")
_TYPICAL_SECTION_LENGTH_SCHEMA_TARGET = 1
ROADSIDE_LIBRARY_BUNDLES = {
    "shoulder_edge": [
        {"Id": "SHL", "Type": "shoulder", "Side": "left", "Width": 1.500, "CrossSlopePct": 4.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
    ],
    "ditch_edge": [
        {"Id": "GUT", "Type": "gutter", "Side": "left", "Width": 0.800, "CrossSlopePct": 6.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 10, "Enabled": True},
        {"Id": "DITCH", "Type": "ditch", "Side": "left", "Width": 2.400, "CrossSlopePct": 2.0, "Height": 1.000, "ExtraWidth": 0.800, "BackSlopePct": -10.0, "Offset": 0.000, "Order": 20, "Enabled": True},
        {"Id": "BERM", "Type": "berm", "Side": "left", "Width": 1.200, "CrossSlopePct": 0.0, "Height": 0.000, "ExtraWidth": 0.800, "BackSlopePct": 6.0, "Offset": 0.000, "Order": 30, "Enabled": True},
    ],
    "urban_edge": [
        {"Id": "CURB", "Type": "curb", "Side": "left", "Width": 0.180, "CrossSlopePct": 0.0, "Height": 0.150, "ExtraWidth": 0.060, "BackSlopePct": 1.0, "Offset": 0.000, "Order": 10, "Enabled": True},
        {"Id": "WALK", "Type": "sidewalk", "Side": "left", "Width": 2.000, "CrossSlopePct": 1.5, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 20, "Enabled": True},
        {"Id": "GREEN", "Type": "green_strip", "Side": "left", "Width": 1.200, "CrossSlopePct": 4.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 30, "Enabled": True},
    ],
    "median_core": [
        {"Id": "MED", "Type": "median", "Side": "center", "Width": 2.000, "CrossSlopePct": 0.0, "Height": 0.000, "ExtraWidth": 0.000, "BackSlopePct": 0.000, "Offset": 0.000, "Order": 5, "Enabled": True},
    ],
}


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


def _default_component_data(scale: float = 1.0):
    return {
        "ComponentIds": ["LANE-L", "SHL-L", "LANE-R", "SHL-R"],
        "ComponentTypes": ["lane", "shoulder", "lane", "shoulder"],
        "ComponentShapes": ["", "", "", ""],
        "ComponentSides": ["left", "left", "right", "right"],
        "ComponentWidths": [3.50 * scale, 1.50 * scale, 3.50 * scale, 1.50 * scale],
        "ComponentCrossSlopes": [2.0, 4.0, 2.0, 4.0],
        "ComponentHeights": [0.0, 0.0, 0.0, 0.0],
        "ComponentExtraWidths": [0.0, 0.0, 0.0, 0.0],
        "ComponentBackSlopes": [0.0, 0.0, 0.0, 0.0],
        "ComponentOffsets": [0.0, 0.0, 0.0, 0.0],
        "ComponentOrders": [10, 20, 10, 20],
        "ComponentEnabled": [1, 1, 1, 1],
    }


def _component_array_specs(scale: float = 1.0):
    defaults = _default_component_data(scale)
    return (
        ("ComponentIds", "App::PropertyStringList", defaults["ComponentIds"], "Ordered component identifiers"),
        ("ComponentTypes", "App::PropertyStringList", defaults["ComponentTypes"], "Component types"),
        ("ComponentShapes", "App::PropertyStringList", defaults["ComponentShapes"], "Optional component shape modes"),
        ("ComponentSides", "App::PropertyStringList", defaults["ComponentSides"], "Component side assignments"),
        ("ComponentWidths", "App::PropertyFloatList", defaults["ComponentWidths"], "Component widths (m)"),
        ("ComponentCrossSlopes", "App::PropertyFloatList", defaults["ComponentCrossSlopes"], "Cross slopes (%)"),
        ("ComponentHeights", "App::PropertyFloatList", defaults["ComponentHeights"], "Vertical steps/heights (m)"),
        ("ComponentExtraWidths", "App::PropertyFloatList", defaults["ComponentExtraWidths"], "Type-specific extra widths (m)"),
        ("ComponentBackSlopes", "App::PropertyFloatList", defaults["ComponentBackSlopes"], "Type-specific secondary/back slopes (%)"),
        ("ComponentOffsets", "App::PropertyFloatList", defaults["ComponentOffsets"], "Optional local lateral offsets (m)"),
        ("ComponentOrders", "App::PropertyIntegerList", defaults["ComponentOrders"], "Sort order per side"),
        ("ComponentEnabled", "App::PropertyIntegerList", defaults["ComponentEnabled"], "Enabled flags (1/0)"),
    )


def _default_pavement_data(scale: float = 1.0):
    return {
        "PavementLayerIds": ["SURF", "BINDER", "BASE", "SUBBASE"],
        "PavementLayerTypes": ["surface", "binder", "base", "subbase"],
        "PavementLayerThicknesses": [0.05 * scale, 0.07 * scale, 0.20 * scale, 0.25 * scale],
        "PavementLayerEnabled": [1, 1, 1, 1],
    }


def _pavement_array_specs(scale: float = 1.0):
    defaults = _default_pavement_data(scale)
    return (
        ("PavementLayerIds", "App::PropertyStringList", defaults["PavementLayerIds"], "Pavement layer identifiers"),
        ("PavementLayerTypes", "App::PropertyStringList", defaults["PavementLayerTypes"], "Pavement layer types"),
        ("PavementLayerThicknesses", "App::PropertyFloatList", defaults["PavementLayerThicknesses"], "Pavement layer thicknesses (m)"),
        ("PavementLayerEnabled", "App::PropertyIntegerList", defaults["PavementLayerEnabled"], "Pavement layer enabled flags (1/0)"),
    )


def ensure_typical_section_template_properties(obj):
    had_length_props = any(
        hasattr(obj, prop)
        for prop in (
            "ComponentWidths",
            "ComponentHeights",
            "ComponentExtraWidths",
            "ComponentOffsets",
            "PavementLayerThicknesses",
        )
    )

    for name, ptype, default, doc in _component_array_specs():
        if not hasattr(obj, name):
            obj.addProperty(ptype, name, "Components", doc)
            setattr(obj, name, list(default))
    for name, ptype, default, doc in _pavement_array_specs():
        if not hasattr(obj, name):
            obj.addProperty(ptype, name, "Pavement", doc)
            setattr(obj, name, list(default))
    if not hasattr(obj, "LengthSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "LengthSchemaVersion", "Result", "Length storage schema version")
        obj.LengthSchemaVersion = 0

    try:
        schema = int(getattr(obj, "LengthSchemaVersion", 0) or 0)
    except Exception:
        schema = 0
    if schema < _TYPICAL_SECTION_LENGTH_SCHEMA_TARGET:
        try:
            obj.LengthSchemaVersion = _TYPICAL_SECTION_LENGTH_SCHEMA_TARGET
        except Exception:
            pass

    if not hasattr(obj, "PreviewSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "PreviewSchemaVersion", "Result", "Preview schema version")
        obj.PreviewSchemaVersion = 2
    if not hasattr(obj, "SubassemblySchemaVersion"):
        obj.addProperty("App::PropertyInteger", "SubassemblySchemaVersion", "Result", "Practical subassembly schema version")
        obj.SubassemblySchemaVersion = 1
    if not hasattr(obj, "PracticalRole"):
        obj.addProperty("App::PropertyString", "PracticalRole", "Result", "Practical engineering role summary")
        obj.PracticalRole = "top_profile_subassembly"
    if not hasattr(obj, "PracticalSectionMode"):
        obj.addProperty("App::PropertyString", "PracticalSectionMode", "Result", "Practical section mode summary")
        obj.PracticalSectionMode = "simple"
    if not hasattr(obj, "GeometryDrivingFieldSummary"):
        obj.addProperty("App::PropertyString", "GeometryDrivingFieldSummary", "Result", "Geometry-driving field summary")
        obj.GeometryDrivingFieldSummary = ""
    if not hasattr(obj, "AnalysisDrivingFieldSummary"):
        obj.addProperty("App::PropertyString", "AnalysisDrivingFieldSummary", "Result", "Analysis-driving field summary")
        obj.AnalysisDrivingFieldSummary = ""
    if not hasattr(obj, "ReportOnlyFieldSummary"):
        obj.addProperty("App::PropertyString", "ReportOnlyFieldSummary", "Result", "Report-only field summary")
        obj.ReportOnlyFieldSummary = ""
    if not hasattr(obj, "ComponentCount"):
        obj.addProperty("App::PropertyInteger", "ComponentCount", "Result", "Total component row count")
        obj.ComponentCount = 0
    if not hasattr(obj, "EnabledComponentCount"):
        obj.addProperty("App::PropertyInteger", "EnabledComponentCount", "Result", "Enabled component row count")
        obj.EnabledComponentCount = 0
    if not hasattr(obj, "AdvancedComponentCount"):
        obj.addProperty("App::PropertyInteger", "AdvancedComponentCount", "Result", "Enabled component rows using advanced geometry parameters")
        obj.AdvancedComponentCount = 0
    if not hasattr(obj, "PavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "PavementLayerCount", "Result", "Total pavement layer row count")
        obj.PavementLayerCount = 0
    if not hasattr(obj, "EnabledPavementLayerCount"):
        obj.addProperty("App::PropertyInteger", "EnabledPavementLayerCount", "Result", "Enabled pavement layer row count")
        obj.EnabledPavementLayerCount = 0
    if not hasattr(obj, "PavementTotalThickness"):
        obj.addProperty("App::PropertyFloat", "PavementTotalThickness", "Result", "Enabled pavement total thickness (m)")
        obj.PavementTotalThickness = 0.0
    if not hasattr(obj, "PavementLayerSummaryRows"):
        obj.addProperty("App::PropertyStringList", "PavementLayerSummaryRows", "Result", "Enabled pavement layer report rows")
        obj.PavementLayerSummaryRows = []
    if not hasattr(obj, "SubassemblyContractRows"):
        obj.addProperty("App::PropertyStringList", "SubassemblyContractRows", "Result", "Resolved subassembly contract rows")
        obj.SubassemblyContractRows = []
    if not hasattr(obj, "SubassemblyValidationRows"):
        obj.addProperty("App::PropertyStringList", "SubassemblyValidationRows", "Result", "Resolved subassembly validation rows")
        obj.SubassemblyValidationRows = []
    if not hasattr(obj, "RoadsideLibraryRows"):
        obj.addProperty("App::PropertyStringList", "RoadsideLibraryRows", "Result", "Detected reusable roadside-library rows")
        obj.RoadsideLibraryRows = []
    if not hasattr(obj, "RoadsideLibrarySummary"):
        obj.addProperty("App::PropertyString", "RoadsideLibrarySummary", "Result", "Detected reusable roadside-library summary")
        obj.RoadsideLibrarySummary = "-"
    if not hasattr(obj, "ReportSchemaVersion"):
        obj.addProperty("App::PropertyInteger", "ReportSchemaVersion", "Result", "Structured report schema version")
        obj.ReportSchemaVersion = 1
    if not hasattr(obj, "SectionComponentSummaryRows"):
        obj.addProperty("App::PropertyStringList", "SectionComponentSummaryRows", "Result", "Structured section-component summary rows")
        obj.SectionComponentSummaryRows = []
    if not hasattr(obj, "PavementScheduleRows"):
        obj.addProperty("App::PropertyStringList", "PavementScheduleRows", "Result", "Structured pavement schedule rows")
        obj.PavementScheduleRows = []
    if not hasattr(obj, "StructureInteractionSummaryRows"):
        obj.addProperty("App::PropertyStringList", "StructureInteractionSummaryRows", "Result", "Structured structure-interaction summary rows")
        obj.StructureInteractionSummaryRows = []
    if not hasattr(obj, "ExportSummaryRows"):
        obj.addProperty("App::PropertyStringList", "ExportSummaryRows", "Result", "Structured export-ready summary rows")
        obj.ExportSummaryRows = []
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
    if not hasattr(obj, "PreviewSelectedComponentIndex"):
        obj.addProperty("App::PropertyInteger", "PreviewSelectedComponentIndex", "Display", "Selected component row index for preview-only wire")
        obj.PreviewSelectedComponentIndex = -1


def _normalized_component_arrays(obj):
    specs = _component_array_specs()
    lengths = []
    for name, _ptype, default, _doc in specs:
        raw = list(getattr(obj, name, list(default)) or [])
        lengths.append(len(raw))
    n = max(lengths or [0])
    if n <= 0:
        n = len(_default_component_data()["ComponentIds"])

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
    specs = _pavement_array_specs()
    lengths = []
    for name, _ptype, default, _doc in specs:
        raw = list(getattr(obj, name, list(default)) or [])
        lengths.append(len(raw))
    n = max(lengths or [0])
    if n <= 0:
        n = len(_default_pavement_data()["PavementLayerIds"])

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
            "Shape": str(data["ComponentShapes"][i] or "").strip().lower(),
            "Side": str(data["ComponentSides"][i] or "").strip().lower() or "left",
            "Width": max(0.0, _safe_float(data["ComponentWidths"][i], default=0.0)),
            "CrossSlopePct": _safe_float(data["ComponentCrossSlopes"][i], default=0.0),
            "Height": _safe_float(data["ComponentHeights"][i], default=0.0),
            "ExtraWidth": max(0.0, _safe_float(data["ComponentExtraWidths"][i], default=0.0)),
            "BackSlopePct": _safe_float(data["ComponentBackSlopes"][i], default=0.0),
            "Offset": _safe_float(data["ComponentOffsets"][i], default=0.0),
            "Order": _safe_int(data["ComponentOrders"][i], default=i + 1),
            "Enabled": _as_bool_flag(data["ComponentEnabled"][i]),
            "_Index": i,
        }
        if row["Type"] == "bench":
            row["Type"] = "berm"
        if row["Type"] == "ditch":
            shape = str(row.get("Shape", "") or "").strip().lower()
            if shape not in ALLOWED_DITCH_SHAPES:
                shape = ""
            if not shape:
                shape = "trapezoid" if float(row.get("ExtraWidth", 0.0) or 0.0) > 1e-9 else "v"
            row["Shape"] = shape
        else:
            row["Shape"] = ""
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
        shape = str(row.get("Shape", "") or "").strip().lower()
        if typ == "ditch":
            if shape not in ALLOWED_DITCH_SHAPES or not shape:
                issues.append(f"{cid}: unsupported ditch shape '{shape or '-'}'")
        elif shape:
            issues.append(f"{cid}: shape is only supported for ditch rows")

        side = str(row["Side"] or "").strip().lower()
        if side not in ALLOWED_COMPONENT_SIDES:
            issues.append(f"{cid}: unsupported side '{side}'")

        if float(row["Width"]) < 0.0:
            issues.append(f"{cid}: width must be >= 0")
        if float(row["ExtraWidth"]) < 0.0:
            issues.append(f"{cid}: extra width must be >= 0")
        if not math.isfinite(float(row["CrossSlopePct"])):
            issues.append(f"{cid}: cross slope must be finite")
        if not math.isfinite(float(row["BackSlopePct"])):
            issues.append(f"{cid}: back slope must be finite")
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


def _component_effective_width(row) -> float:
    typ = str(row.get("Type", "") or "").strip().lower()
    width = max(0.0, _safe_float(row.get("Width", 0.0), default=0.0))
    extra_width = max(0.0, _safe_float(row.get("ExtraWidth", 0.0), default=0.0))
    if typ in ("curb", "berm"):
        return float(width + extra_width)
    return float(width)


def _uses_advanced_component_geometry(row) -> bool:
    if not bool(row.get("Enabled", True)):
        return False
    typ = str(row.get("Type", "") or "").strip().lower()
    width = max(0.0, _safe_float(row.get("Width", 0.0), default=0.0))
    extra_width = max(0.0, _safe_float(row.get("ExtraWidth", 0.0), default=0.0))
    slope = _safe_float(row.get("CrossSlopePct", 0.0), default=0.0)
    back_slope = _safe_float(row.get("BackSlopePct", 0.0), default=0.0)
    shape = str(row.get("Shape", "") or "").strip().lower()
    if typ == "ditch":
        return bool(shape == "trapezoid" or extra_width > 1e-9 or abs(back_slope - slope) > 1e-9)
    if typ == "curb":
        return bool(extra_width > 1e-9 or abs(back_slope) > 1e-9)
    if typ == "berm":
        return bool(extra_width > 1e-9 or abs(back_slope) > 1e-9 or abs(slope) > 1e-9)
    return False


def _component_contract_row(row):
    typ = str(row.get("Type", "") or "").strip().lower()
    side = str(row.get("Side", "") or "").strip().lower() or "-"
    cid = str(row.get("Id", "") or "").strip() or "-"
    if typ in ROADSIDE_ADVANCED_TYPES:
        mode = "advanced" if _uses_advanced_component_geometry(row) else "core"
    else:
        mode = "core"
    return f"{cid}:{typ}:{side}:{mode}"


def _component_validation_rows(rows):
    notes = []
    for row in rows:
        if not bool(row.get("Enabled", True)):
            continue
        cid = str(row.get("Id", "") or "").strip() or "-"
        typ = str(row.get("Type", "") or "").strip().lower()
        side = str(row.get("Side", "") or "").strip().lower()
        width = max(0.0, _safe_float(row.get("Width", 0.0), default=0.0))
        extra_width = max(0.0, _safe_float(row.get("ExtraWidth", 0.0), default=0.0))
        slope = _safe_float(row.get("CrossSlopePct", 0.0), default=0.0)
        back_slope = _safe_float(row.get("BackSlopePct", 0.0), default=0.0)

        if typ in ROADSIDE_ADVANCED_TYPES and side in ("center", "both"):
            notes.append(f"{cid}: {typ} should use left/right side for deterministic practical-section behavior")
        if typ not in ROADSIDE_ADVANCED_TYPES and (extra_width > 1e-9 or abs(back_slope) > 1e-9):
            notes.append(f"{cid}: ExtraWidth/BackSlopePct are currently ignored for type '{typ}'")
        if typ != "ditch" and str(row.get("Shape", "") or "").strip():
            notes.append(f"{cid}: Shape is currently ignored for type '{typ}'")
        if typ == "ditch" and extra_width >= max(width, 1e-9):
            notes.append(f"{cid}: ditch ExtraWidth should stay smaller than Width")
        if typ == "ditch" and str(row.get("Shape", "") or "").strip().lower() == "v" and extra_width > 1e-9:
            notes.append(f"{cid}: ditch Shape=v ignores ExtraWidth and uses a V-bottom profile")
        if typ == "ditch" and str(row.get("Shape", "") or "").strip().lower() == "u" and (extra_width > 1e-9 or abs(back_slope) > 1e-9):
            notes.append(f"{cid}: ditch Shape=u currently ignores ExtraWidth and BackSlopePct")
        if typ == "curb" and abs(_safe_float(row.get("Height", 0.0), default=0.0)) <= 1e-9:
            notes.append(f"{cid}: curb Height is 0, so the curb behaves like a flat edge")
        if typ == "berm" and extra_width > 1e-9 and abs(back_slope) <= 1e-9:
            notes.append(f"{cid}: berm ExtraWidth is set but BackSlopePct is 0")
        if typ == "ditch" and extra_width > 1e-9 and abs(back_slope - slope) <= 1e-9:
            notes.append(f"{cid}: ditch BackSlopePct matches CrossSlopePct, so outer slope is not differentiated")
    return notes


def pavement_layer_summary_rows(obj):
    rows = pavement_rows(obj)
    out = []
    for row in rows:
        if not bool(row.get("Enabled", True)):
            continue
        thickness = max(0.0, float(row.get("Thickness", 0.0) or 0.0))
        if thickness <= 1e-9:
            continue
        out.append(
            f"{str(row.get('Id', '') or '').strip() or '-'}:"
            f"{str(row.get('Type', '') or '').strip() or '-'}:"
            f"{thickness:.3f}m"
        )
    return out


def _report_row(kind: str, **fields) -> str:
    parts = [str(kind or "").strip() or "row"]
    for key, value in fields.items():
        parts.append(f"{str(key)}={value}")
    return "|".join(parts)


def section_component_summary_rows(rows):
    out = []
    for row in rows:
        if not bool(row.get("Enabled", True)):
            continue
        out.append(
            _report_row(
                "component",
                id=str(row.get("Id", "") or "").strip() or "-",
                type=str(row.get("Type", "") or "").strip().lower() or "-",
                shape=str(row.get("Shape", "") or "").strip().lower() or "-",
                side=str(row.get("Side", "") or "").strip().lower() or "-",
                width=f"{max(0.0, _safe_float(row.get('Width', 0.0), default=0.0)):.3f}",
                crossSlopePct=f"{_safe_float(row.get('CrossSlopePct', 0.0), default=0.0):.3f}",
                height=f"{_safe_float(row.get('Height', 0.0), default=0.0):.3f}",
                extraWidth=f"{max(0.0, _safe_float(row.get('ExtraWidth', 0.0), default=0.0)):.3f}",
                backSlopePct=f"{_safe_float(row.get('BackSlopePct', 0.0), default=0.0):.3f}",
                offset=f"{_safe_float(row.get('Offset', 0.0), default=0.0):.3f}",
                order=int(_safe_int(row.get("Order", 0), default=0)),
            )
        )
    return out


def pavement_schedule_rows(rows):
    out = []
    for row in rows:
        if not bool(row.get("Enabled", True)):
            continue
        out.append(
            _report_row(
                "pavement",
                id=str(row.get("Id", "") or "").strip() or "-",
                type=str(row.get("Type", "") or "").strip().lower() or "-",
                thickness=f"{max(0.0, _safe_float(row.get('Thickness', 0.0), default=0.0)):.3f}",
            )
        )
    return out


def export_summary_rows_for_typical_section(
    *,
    report_schema_version: int,
    practical_mode: str,
    component_count: int,
    advanced_count: int,
    pavement_layers: int,
    pavement_total_thickness: float,
    roadside_summary: str,
    validation_count: int,
):
    return [
        _report_row(
            "export",
            target="typical_section",
            reportSchema=int(report_schema_version or 0),
            practical=str(practical_mode or "simple"),
            components=int(component_count or 0),
            advanced=int(advanced_count or 0),
            pavementLayers=int(pavement_layers or 0),
            pavementTotal=f"{float(pavement_total_thickness or 0.0):.3f}",
            roadside=str(roadside_summary or "-"),
            validation=int(validation_count or 0),
        )
    ]


def _row_side_key(row) -> str:
    side = str(row.get("Side", "") or "").strip().lower()
    if side in ("left", "right", "center", "both"):
        return side
    return "-"


def normalize_roadside_bundle_side_mode(value) -> str:
    mode = str(value or "").strip().lower()
    if mode.startswith("left"):
        return "left"
    if mode.startswith("right"):
        return "right"
    if mode.startswith("center"):
        return "center"
    return "both"


def mirror_roadside_bundle_row(row, target_side):
    out = dict(row or {})
    src_side = str(out.get("Side", "") or "").strip().lower()
    side = str(target_side or src_side or "left").strip().lower()
    out["Side"] = side
    base_id = str(out.get("Id", "") or "").strip() or "COMP"
    if base_id.endswith("-L") or base_id.endswith("-R") or base_id.endswith("_L") or base_id.endswith("_R"):
        base_id = base_id[:-2]
    suffix = ""
    if side == "left":
        suffix = "-L"
    elif side == "right":
        suffix = "-R"
    elif side == "center":
        suffix = "-C"
    out["Id"] = f"{base_id}{suffix}" if suffix else base_id
    return out


def expand_roadside_library_bundle(bundle_key, side_mode="both"):
    key = str(bundle_key or "").strip().lower()
    base = [dict(row) for row in list(ROADSIDE_LIBRARY_BUNDLES.get(key, []) or [])]
    if not base:
        return []
    mode = normalize_roadside_bundle_side_mode(side_mode)
    if mode == "center":
        if all(str(r.get("Side", "") or "").strip().lower() == "center" for r in base):
            return base
        return []
    if any(str(r.get("Side", "") or "").strip().lower() == "center" for r in base):
        if mode != "both":
            return []
        return base
    if mode == "left":
        return [mirror_roadside_bundle_row(r, "left") for r in base]
    if mode == "right":
        return [mirror_roadside_bundle_row(r, "right") for r in base]
    out = []
    for side in ("left", "right"):
        out.extend(mirror_roadside_bundle_row(r, side) for r in base)
    return out


def _side_has_types(rows, side: str, required_types) -> bool:
    side_key = str(side or "").strip().lower()
    side_rows = [
        str(r.get("Type", "") or "").strip().lower()
        for r in rows
        if bool(r.get("Enabled", True)) and _row_side_key(r) == side_key
    ]
    return all(req in side_rows for req in list(required_types or []))


def roadside_library_rows(rows):
    out = []
    if _side_has_types(rows, "left", ("gutter", "ditch", "berm")):
        out.append("ditch_edge:left")
    if _side_has_types(rows, "right", ("gutter", "ditch", "berm")):
        out.append("ditch_edge:right")
    if _side_has_types(rows, "left", ("curb", "sidewalk")):
        out.append("urban_edge:left")
    if _side_has_types(rows, "right", ("curb", "sidewalk")):
        out.append("urban_edge:right")
    if _side_has_types(rows, "left", ("shoulder",)) and not _side_has_types(rows, "left", ("ditch", "curb")):
        out.append("shoulder_edge:left")
    if _side_has_types(rows, "right", ("shoulder",)) and not _side_has_types(rows, "right", ("ditch", "curb")):
        out.append("shoulder_edge:right")
    center_types = [
        str(r.get("Type", "") or "").strip().lower()
        for r in rows
        if bool(r.get("Enabled", True)) and _row_side_key(r) == "center"
    ]
    if "median" in center_types:
        out.append("median_core:center")
    return out


def roadside_library_summary(rows):
    counts = {}
    for item in roadside_library_rows(rows):
        fam = str(item).split(":", 1)[0]
        counts[fam] = int(counts.get(fam, 0) or 0) + 1
    if not counts:
        return "-"
    return ",".join(f"{fam}:{int(counts[fam])}" for fam in sorted(counts))


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


def _component_row_to_model_lengths(obj, row):
    out = dict(row or {})
    for key in ("Width", "Height", "ExtraWidth", "Offset"):
        out[key] = _units.model_length_from_meters(getattr(obj, "Document", None), float(out.get(key, 0.0) or 0.0))
    return out


def _pavement_row_to_model_lengths(obj, row):
    out = dict(row or {})
    out["Thickness"] = _units.model_length_from_meters(getattr(obj, "Document", None), float(out.get("Thickness", 0.0) or 0.0))
    return out


def _component_rows_model(obj):
    return [_component_row_to_model_lengths(obj, row) for row in component_rows(obj)]


def _pavement_rows_model(obj):
    return [_pavement_row_to_model_lengths(obj, row) for row in pavement_rows(obj)]


def _segment_profile_points(x0: float, y0: float, row, direction: float):
    typ = str(row.get("Type", "") or "").strip().lower()
    width = max(0.0, _safe_float(row.get("Width", 0.0), default=0.0))
    slope = _safe_float(row.get("CrossSlopePct", 0.0), default=0.0)
    height = _safe_float(row.get("Height", 0.0), default=0.0)
    extra_width = max(0.0, _safe_float(row.get("ExtraWidth", 0.0), default=0.0))
    back_slope = _safe_float(row.get("BackSlopePct", 0.0), default=slope)
    shape = str(row.get("Shape", "") or "").strip().lower()
    pts = []
    x = float(x0)
    y = float(y0)

    if typ == "curb":
        if extra_width > 1e-9:
            x, y = _apply_segment(x, y, extra_width, slope, 0.0, direction)
            pts.append(App.Vector(x, y, 0.0))
        if abs(height) > 1e-9:
            y += height
            pts.append(App.Vector(x, y, 0.0))
        x, y = _apply_segment(x, y, width, back_slope, 0.0, direction)
        pts.append(App.Vector(x, y, 0.0))
        return pts

    if typ == "ditch" and width > 1e-9 and abs(height) > 1e-9:
        if shape not in ALLOWED_DITCH_SHAPES or not shape:
            shape = "trapezoid" if extra_width > 1e-9 else "v"
        if shape == "u":
            half_w = 0.5 * width
            u_steps = (0.25, 0.50, 0.75, 1.0)
            for frac in u_steps:
                x_seg = x + float(direction) * (width * frac)
                norm = (2.0 * frac) - 1.0
                sag = max(0.0, 1.0 - (norm * norm))
                y_seg = y - abs(height) * sag
                pts.append(App.Vector(x_seg, y_seg, 0.0))
            return pts
        bottom_w = min(width - 1e-9, extra_width) if extra_width > 1e-9 else 0.0
        if shape == "v":
            bottom_w = 0.0
        if bottom_w <= 1e-9:
            half_w = 0.5 * width
            x_mid = x + float(direction) * half_w
            y_mid = y - abs(height)
            pts.append(App.Vector(x_mid, y_mid, 0.0))
            x_end = x + float(direction) * width
            y_end = y - (width * slope / 100.0)
            pts.append(App.Vector(x_end, y_end, 0.0))
            return pts
        outer_total = max(0.0, width - bottom_w)
        inner_w = 0.5 * outer_total
        outer_w = max(0.0, outer_total - inner_w)
        x_mid = x + float(direction) * inner_w
        y_mid = y - abs(height)
        pts.append(App.Vector(x_mid, y_mid, 0.0))
        x_bottom = x_mid + float(direction) * bottom_w
        pts.append(App.Vector(x_bottom, y_mid, 0.0))
        x_end = x_bottom + float(direction) * outer_w
        y_end = y_mid - (outer_w * back_slope / 100.0)
        pts.append(App.Vector(x_end, y_end, 0.0))
        return pts

    if typ == "berm":
        x, y = _apply_segment(x, y, width, slope, height, direction)
        pts.append(App.Vector(x, y, 0.0))
        if extra_width > 1e-9:
            x, y = _apply_segment(x, y, extra_width, back_slope, 0.0, direction)
            pts.append(App.Vector(x, y, 0.0))
        return pts

    x, y = _apply_segment(x, y, width, slope, height, direction)
    pts.append(App.Vector(x, y, 0.0))
    return pts


def build_top_profile(obj):
    rows = _component_rows_model(obj)
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


def build_component_preview_profile(obj, selected_index: int):
    rows = _component_rows_model(obj)
    left_rows, center_rows, right_rows = _split_rows_by_side(rows)
    selected_index = int(selected_index)

    x_left = 0.0
    y_left = 0.0
    x_right = 0.0
    y_right = 0.0

    for row in center_rows:
        half_w = 0.5 * max(0.0, float(row.get("Width", 0.0) or 0.0))
        slope = float(row.get("CrossSlopePct", 0.0) or 0.0)
        height = float(row.get("Height", 0.0) or 0.0)
        start_left = App.Vector(x_left, y_left, 0.0)
        start_right = App.Vector(x_right, y_right, 0.0)
        next_left_x, next_left_y = _apply_segment(x_left, y_left, half_w, slope, height, +1.0)
        next_right_x, next_right_y = _apply_segment(x_right, y_right, half_w, slope, height, -1.0)
        end_left = App.Vector(next_left_x, next_left_y, 0.0)
        end_right = App.Vector(next_right_x, next_right_y, 0.0)
        x_left, y_left = next_left_x, next_left_y
        x_right, y_right = next_right_x, next_right_y
        if int(row.get("_Index", -9999)) == selected_index:
            pts = [end_left, App.Vector(0.0, 0.0, 0.0), end_right]
            cleaned = []
            for pt in pts:
                if not cleaned or (pt - cleaned[-1]).Length > 1e-9:
                    cleaned.append(pt)
            return cleaned

    for row in left_rows:
        x_left += float(row.get("Offset", 0.0) or 0.0)
        start = App.Vector(x_left, y_left, 0.0)
        seg_pts = _segment_profile_points(x_left, y_left, row, +1.0)
        if seg_pts:
            x_left = float(seg_pts[-1].x)
            y_left = float(seg_pts[-1].y)
            if int(row.get("_Index", -9999)) == selected_index:
                pts = [start] + list(seg_pts)
                cleaned = []
                for pt in pts:
                    if not cleaned or (pt - cleaned[-1]).Length > 1e-9:
                        cleaned.append(pt)
                return cleaned

    for row in right_rows:
        x_right -= float(row.get("Offset", 0.0) or 0.0)
        start = App.Vector(x_right, y_right, 0.0)
        seg_pts = _segment_profile_points(x_right, y_right, row, -1.0)
        if seg_pts:
            x_right = float(seg_pts[-1].x)
            y_right = float(seg_pts[-1].y)
            if int(row.get("_Index", -9999)) == selected_index:
                pts = [start] + list(seg_pts)
                cleaned = []
                for pt in pts:
                    if not cleaned or (pt - cleaned[-1]).Length > 1e-9:
                        cleaned.append(pt)
                return cleaned
    return []


def build_pavement_layer_shapes(obj):
    top_pts = build_top_profile(obj)
    if len(top_pts) < 2:
        return []

    layers = [r for r in _pavement_rows_model(obj) if bool(r.get("Enabled", True)) and float(r.get("Thickness", 0.0) or 0.0) > 1e-9]
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
            advanced_count = sum(1 for r in rows if _uses_advanced_component_geometry(r))
            pav_enabled_count = sum(1 for r in pav_rows if bool(r.get("Enabled", True)))
            pav_total_thk = sum(float(r.get("Thickness", 0.0) or 0.0) for r in pav_rows if bool(r.get("Enabled", True)))
            pav_summary_rows = pavement_layer_summary_rows(obj)
            contract_rows = [_component_contract_row(r) for r in rows if bool(r.get("Enabled", True))]
            validation_rows = _component_validation_rows(rows)
            roadside_rows = roadside_library_rows(rows)
            roadside_summary = roadside_library_summary(rows)
            component_summary = section_component_summary_rows(rows)
            pavement_schedule = pavement_schedule_rows(pav_rows)
            left_rows, _center_rows, right_rows = _split_rows_by_side(rows)
            practical_mode = "advanced" if advanced_count > 0 else "simple"
            obj.ComponentCount = int(len(rows))
            obj.EnabledComponentCount = int(enabled_count)
            obj.AdvancedComponentCount = int(advanced_count)
            obj.SubassemblySchemaVersion = 1
            obj.PracticalRole = "top_profile_subassembly"
            obj.PracticalSectionMode = practical_mode
            obj.GeometryDrivingFieldSummary = "Type,Shape,Side,Width,CrossSlopePct,Height,ExtraWidth,BackSlopePct,Offset,Order,Enabled"
            obj.AnalysisDrivingFieldSummary = "ComponentIds,ComponentTypes,ComponentShapes,ComponentSides,ComponentWidths,ComponentCrossSlopes,ComponentHeights,ComponentExtraWidths,ComponentBackSlopes"
            obj.ReportOnlyFieldSummary = (
                "PavementLayerIds,PavementLayerTypes,PavementLayerThicknesses,PavementLayerEnabled,"
                "PavementLayerSummaryRows,SectionComponentSummaryRows,PavementScheduleRows,ExportSummaryRows"
            )
            obj.PavementLayerCount = int(len(pav_rows))
            obj.EnabledPavementLayerCount = int(pav_enabled_count)
            obj.PavementTotalThickness = float(pav_total_thk)
            obj.PavementLayerSummaryRows = list(pav_summary_rows)
            obj.SubassemblyContractRows = list(contract_rows)
            obj.SubassemblyValidationRows = list(validation_rows)
            obj.RoadsideLibraryRows = list(roadside_rows)
            obj.RoadsideLibrarySummary = str(roadside_summary or "-")
            obj.ReportSchemaVersion = 1
            obj.SectionComponentSummaryRows = list(component_summary)
            obj.PavementScheduleRows = list(pavement_schedule)
            obj.StructureInteractionSummaryRows = []
            obj.ExportSummaryRows = list(
                export_summary_rows_for_typical_section(
                    report_schema_version=1,
                    practical_mode=practical_mode,
                    component_count=enabled_count,
                    advanced_count=advanced_count,
                    pavement_layers=pav_enabled_count,
                    pavement_total_thickness=pav_total_thk,
                    roadside_summary=roadside_summary,
                    validation_count=len(validation_rows),
                )
            )
            if hasattr(obj, "PavementPreviewCount"):
                obj.PavementPreviewCount = 0
            obj.LeftEdgeComponentType = str(left_rows[-1].get("Type", "") or "") if left_rows else ""
            obj.RightEdgeComponentType = str(right_rows[-1].get("Type", "") or "") if right_rows else ""
            obj.PreviewSchemaVersion = 2

            if not bool(getattr(obj, "ShowPreviewWire", True)):
                obj.Shape = Part.Shape()
                obj.Status = (
                    f"Hidden: role={obj.PracticalRole} practical={obj.PracticalSectionMode} subSchema={int(obj.SubassemblySchemaVersion)} "
                    f"advanced={int(advanced_count)} validation={len(validation_rows)} "
                    f"roadside={obj.RoadsideLibrarySummary} "
                    f"edges=({obj.LeftEdgeComponentType or '-'}, "
                    f"{obj.RightEdgeComponentType or '-'}) "
                    f"pavement={obj.PavementTotalThickness:.3f}m"
                )
                return

            selected_preview_index = int(getattr(obj, "PreviewSelectedComponentIndex", -1))
            if selected_preview_index >= 0:
                pts = build_component_preview_profile(obj, selected_preview_index)
            else:
                pts = build_top_profile(obj)
            if len(pts) < 2:
                obj.Shape = Part.Shape()
                obj.Status = (
                    f"WARN: role={obj.PracticalRole} practical=fallback subSchema={int(obj.SubassemblySchemaVersion)} "
                    f"roadside={obj.RoadsideLibrarySummary} "
                    "No enabled components."
                )
                return

            obj.Shape = Part.makePolygon(pts)
            all_issues = list(issues) + list(pav_issues) + list(validation_rows)
            if all_issues:
                obj.Status = (
                    f"WARN: role={obj.PracticalRole} practical={obj.PracticalSectionMode} subSchema={int(obj.SubassemblySchemaVersion)} "
                    f"roadside={obj.RoadsideLibrarySummary} | "
                    + " | ".join(all_issues[:4])
                )
            else:
                obj.Status = (
                    f"OK: role={obj.PracticalRole} practical={obj.PracticalSectionMode} subSchema={int(obj.SubassemblySchemaVersion)} "
                    f"{enabled_count}/{len(rows)} components enabled; "
                    f"roadside={obj.RoadsideLibrarySummary} "
                    f"edges=({obj.LeftEdgeComponentType or '-'}, {obj.RightEdgeComponentType or '-'}) "
                    f"pavement={obj.PavementTotalThickness:.3f}m ({pav_enabled_count}/{len(pav_rows)} layers) "
                    f"advanced={int(advanced_count)}"
                )
        except Exception as ex:
            obj.Shape = Part.Shape()
            if hasattr(obj, "PavementPreviewCount"):
                obj.PavementPreviewCount = 0
            obj.SubassemblySchemaVersion = 1
            obj.PracticalRole = "top_profile_subassembly"
            obj.PracticalSectionMode = "fallback"
            obj.GeometryDrivingFieldSummary = ""
            obj.AnalysisDrivingFieldSummary = ""
            obj.ReportOnlyFieldSummary = ""
            obj.AdvancedComponentCount = 0
            obj.PavementLayerSummaryRows = []
            obj.SubassemblyContractRows = []
            obj.SubassemblyValidationRows = []
            obj.RoadsideLibraryRows = []
            obj.RoadsideLibrarySummary = "-"
            obj.ReportSchemaVersion = 1
            obj.SectionComponentSummaryRows = []
            obj.PavementScheduleRows = []
            obj.StructureInteractionSummaryRows = []
            obj.ExportSummaryRows = []
            obj.Status = f"ERROR: {ex}"

    def onChanged(self, obj, prop):
        if prop in (
            "ComponentIds",
            "ComponentTypes",
            "ComponentShapes",
            "ComponentSides",
            "ComponentWidths",
            "ComponentCrossSlopes",
            "ComponentHeights",
            "ComponentExtraWidths",
            "ComponentBackSlopes",
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
    if not hasattr(obj, "LayerIds"):
        obj.addProperty("App::PropertyStringList", "LayerIds", "Result", "Enabled pavement layer ids")
        obj.LayerIds = []
    if not hasattr(obj, "LayerTypes"):
        obj.addProperty("App::PropertyStringList", "LayerTypes", "Result", "Enabled pavement layer types")
        obj.LayerTypes = []
    if not hasattr(obj, "LayerThicknesses"):
        obj.addProperty("App::PropertyFloatList", "LayerThicknesses", "Result", "Enabled pavement layer thicknesses")
        obj.LayerThicknesses = []
    if not hasattr(obj, "LayerSummaryRows"):
        obj.addProperty("App::PropertyStringList", "LayerSummaryRows", "Result", "Enabled pavement layer report rows")
        obj.LayerSummaryRows = []
    if not hasattr(obj, "LayerCount"):
        obj.addProperty("App::PropertyInteger", "LayerCount", "Result", "Enabled pavement layer count")
        obj.LayerCount = 0
    if not hasattr(obj, "TotalThickness"):
        obj.addProperty("App::PropertyFloat", "TotalThickness", "Result", "Enabled pavement total thickness (m)")
        obj.TotalThickness = 0.0
    if not hasattr(obj, "Status"):
        obj.addProperty("App::PropertyString", "Status", "Result", "Display generation status")
        obj.Status = "Idle"


def ensure_typical_section_selection_display_properties(obj):
    if not hasattr(obj, "SourceTypicalSection"):
        obj.addProperty("App::PropertyLink", "SourceTypicalSection", "Display", "Source TypicalSectionTemplate")
    if not hasattr(obj, "SelectedComponentIndex"):
        obj.addProperty("App::PropertyInteger", "SelectedComponentIndex", "Display", "Selected component row index")
        obj.SelectedComponentIndex = -1
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
                obj.LayerIds = []
                obj.LayerTypes = []
                obj.LayerThicknesses = []
                obj.LayerSummaryRows = []
                obj.LayerCount = 0
                obj.TotalThickness = 0.0
                obj.Status = "Missing source TypicalSectionTemplate"
                return

            enabled_layers = [r for r in pavement_rows(src) if bool(r.get("Enabled", True)) and float(r.get("Thickness", 0.0) or 0.0) > 1e-9]
            obj.LayerIds = [str(r.get("Id", "") or "") for r in enabled_layers]
            obj.LayerTypes = [str(r.get("Type", "") or "") for r in enabled_layers]
            obj.LayerThicknesses = [float(r.get("Thickness", 0.0) or 0.0) for r in enabled_layers]
            obj.LayerSummaryRows = list(pavement_layer_summary_rows(src))
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
            obj.LayerIds = []
            obj.LayerTypes = []
            obj.LayerThicknesses = []
            obj.LayerSummaryRows = []
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


class TypicalSectionSelectionDisplay:
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "TypicalSectionSelectionDisplay"
        ensure_typical_section_selection_display_properties(obj)

    def execute(self, obj):
        ensure_typical_section_selection_display_properties(obj)
        try:
            src = getattr(obj, "SourceTypicalSection", None)
            selected_index = int(getattr(obj, "SelectedComponentIndex", -1))
            if src is None or selected_index < 0:
                obj.Shape = Part.Shape()
                obj.Status = "No selected component"
                return
            pts = build_component_preview_profile(src, selected_index)
            if len(pts) < 2:
                obj.Shape = Part.Shape()
                obj.Status = "Selected component has no preview segment"
                return
            # Lift the selected preview slightly off the base wire to avoid
            # coplanar z-fighting in the 3D view, and nudge it upward in the
            # section plane so perfectly overlapping first/last edge segments
            # remain distinguishable from the full preview wire.
            z_lift = 0.5
            y_lift = 0.06
            lifted = [App.Vector(float(p.x), float(p.y) + y_lift, float(p.z) + z_lift) for p in pts]
            obj.Shape = Part.makePolygon(lifted)
            obj.Status = f"OK: selected component index={selected_index}"
        except Exception as ex:
            obj.Shape = Part.Shape()
            obj.Status = f"ERROR: {ex}"


class ViewProviderTypicalSectionSelectionDisplay:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Wireframe"
            vobj.LineWidth = 4
            vobj.LineColor = (0.20, 0.85, 0.95)
            vobj.PointColor = (0.20, 0.85, 0.95)
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
