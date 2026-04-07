# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Practical sample-driven workflow smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_practical_sample_driven_workflow.py
"""

import csv
import os

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet
from freecad.Corridor_Road.objects.obj_typical_section_template import TypicalSectionTemplate


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _shape_ok(obj) -> bool:
    shp = getattr(obj, "Shape", None)
    if shp is None:
        return False
    try:
        return not shp.isNull()
    except Exception:
        return False


def _mesh_ok(obj) -> bool:
    mesh = getattr(obj, "Mesh", None)
    if mesh is None:
        return False
    try:
        return int(getattr(mesh, "CountFacets", 0) or 0) > 0
    except Exception:
        return False


def _samples_dir():
    roots = []
    try:
        roots.append(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass
    roots.append(os.path.join(os.getcwd(), "tests", "regression"))
    roots.append(os.getcwd())
    for root in roots:
        candidate = os.path.abspath(os.path.join(root, "..", "samples"))
        if os.path.isdir(candidate):
            return candidate
        candidate = os.path.abspath(os.path.join(root, "tests", "samples"))
        if os.path.isdir(candidate):
            return candidate
    raise Exception("tests/samples directory could not be resolved")


def _read_csv_rows(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fp:
        return list(csv.DictReader(fp))


def _to_float(row, key, default=0.0):
    txt = str(row.get(key, "") or "").strip()
    if txt == "":
        return float(default)
    return float(txt)


def _to_int(row, key, default=0):
    txt = str(row.get(key, "") or "").strip()
    if txt == "":
        return int(default)
    return int(round(float(txt)))


def _to_bool(row, key, default=False):
    txt = str(row.get(key, "") or "").strip().lower()
    if txt == "":
        return bool(default)
    return txt not in ("0", "false", "no", "off")


def _assign_component_rows(obj, rows):
    obj.ComponentIds = [str(r.get("Id", "") or "") for r in rows]
    obj.ComponentTypes = [str(r.get("Type", "") or "") for r in rows]
    obj.ComponentSides = [str(r.get("Side", "") or "") for r in rows]
    obj.ComponentWidths = [_to_float(r, "Width") for r in rows]
    obj.ComponentCrossSlopes = [_to_float(r, "CrossSlopePct") for r in rows]
    obj.ComponentHeights = [_to_float(r, "Height") for r in rows]
    obj.ComponentExtraWidths = [_to_float(r, "ExtraWidth") for r in rows]
    obj.ComponentBackSlopes = [_to_float(r, "BackSlopePct") for r in rows]
    obj.ComponentOffsets = [_to_float(r, "Offset") for r in rows]
    obj.ComponentOrders = [_to_int(r, "Order", default=(idx + 1) * 10) for idx, r in enumerate(rows)]
    obj.ComponentEnabled = [1 if _to_bool(r, "Enabled", default=True) else 0 for r in rows]


def _assign_pavement_rows(obj, rows):
    obj.PavementLayerIds = [str(r.get("Id", "") or "") for r in rows]
    obj.PavementLayerTypes = [str(r.get("Type", "") or "") for r in rows]
    obj.PavementLayerThicknesses = [_to_float(r, "Thickness") for r in rows]
    obj.PavementLayerEnabled = [1 if _to_bool(r, "Enabled", default=True) else 0 for r in rows]


def _assign_structure_rows(obj, rows):
    obj.StructureIds = [str(r.get("Id", "") or "") for r in rows]
    obj.StructureTypes = [str(r.get("Type", "") or "") for r in rows]
    obj.StartStations = [_to_float(r, "StartStation") for r in rows]
    obj.EndStations = [_to_float(r, "EndStation") for r in rows]
    obj.CenterStations = [_to_float(r, "CenterStation") for r in rows]
    obj.Sides = [str(r.get("Side", "") or "") for r in rows]
    obj.Offsets = [_to_float(r, "Offset") for r in rows]
    obj.Widths = [_to_float(r, "Width") for r in rows]
    obj.Heights = [_to_float(r, "Height") for r in rows]
    obj.BottomElevations = [_to_float(r, "BottomElevation") for r in rows]
    obj.Covers = [_to_float(r, "Cover") for r in rows]
    obj.RotationsDeg = [_to_float(r, "RotationDeg") for r in rows]
    obj.BehaviorModes = [str(r.get("BehaviorMode", "") or "") for r in rows]
    obj.GeometryModes = [str(r.get("GeometryMode", "") or "") for r in rows]
    obj.TemplateNames = [str(r.get("TemplateName", "") or "") for r in rows]
    obj.ShapeSourcePaths = [str(r.get("ShapeSourcePath", "") or "") for r in rows]
    obj.ScaleFactors = [_to_float(r, "ScaleFactor", default=1.0) for r in rows]
    obj.PlacementModes = [str(r.get("PlacementMode", "") or "") for r in rows]
    obj.UseSourceBaseAsBottoms = [str(r.get("UseSourceBaseAsBottom", "") or "") for r in rows]
    obj.WallThicknesses = [_to_float(r, "WallThickness") for r in rows]
    obj.FootingWidths = [_to_float(r, "FootingWidth") for r in rows]
    obj.FootingThicknesses = [_to_float(r, "FootingThickness") for r in rows]
    obj.CapHeights = [_to_float(r, "CapHeight") for r in rows]
    obj.CellCounts = [_to_float(r, "CellCount", default=1.0) for r in rows]
    obj.CorridorModes = [str(r.get("CorridorMode", "") or "") for r in rows]
    obj.CorridorMargins = [_to_float(r, "CorridorMargin") for r in rows]
    obj.Notes = [str(r.get("Notes", "") or "") for r in rows]


def _assign_structure_profile_rows(obj, rows):
    obj.ProfileStructureIds = [str(r.get("StructureId", "") or "") for r in rows]
    obj.ProfileStations = [_to_float(r, "Station") for r in rows]
    obj.ProfileOffsets = [_to_float(r, "Offset") for r in rows]
    obj.ProfileWidths = [_to_float(r, "Width") for r in rows]
    obj.ProfileHeights = [_to_float(r, "Height") for r in rows]
    obj.ProfileBottomElevations = [_to_float(r, "BottomElevation") for r in rows]
    obj.ProfileCovers = [_to_float(r, "Cover") for r in rows]
    obj.ProfileWallThicknesses = [_to_float(r, "WallThickness") for r in rows]
    obj.ProfileFootingWidths = [_to_float(r, "FootingWidth") for r in rows]
    obj.ProfileFootingThicknesses = [_to_float(r, "FootingThickness") for r in rows]
    obj.ProfileCapHeights = [_to_float(r, "CapHeight") for r in rows]
    obj.ProfileCellCounts = [_to_int(r, "CellCount", default=1) for r in rows]


def run():
    samples = _samples_dir()
    required = [
        "alignment_utm_realistic_hilly.csv",
        "pointcloud_utm_realistic_hilly.csv",
        "profile_fg_manual_import_basic.csv",
        "profile_fg_manual_import_aliases.csv",
        "structure_utm_realistic_hilly.csv",
        "structure_utm_realistic_hilly_notch.csv",
        "structure_utm_realistic_hilly_template.csv",
        "structure_utm_realistic_hilly_external_shape.csv",
        "structure_utm_realistic_hilly_station_profile_headers.csv",
        "structure_utm_realistic_hilly_station_profile_points.csv",
        "structure_utm_realistic_hilly_mixed.csv",
        "structure_utm_realistic_hilly_mixed_profile_points.csv",
        "typical_section_basic_rural.csv",
        "typical_section_ditch_trapezoid.csv",
        "typical_section_ditch_u.csv",
        "typical_section_ditch_v.csv",
        "typical_section_urban_complete_street.csv",
        "typical_section_with_ditch.csv",
        "typical_section_pavement_basic.csv",
    ]
    for name in required:
        _assert(os.path.isfile(os.path.join(samples, name)), f"Missing practical sample file: {name}")

    urban_rows = _read_csv_rows(os.path.join(samples, "typical_section_urban_complete_street.csv"))
    ditch_v_rows = _read_csv_rows(os.path.join(samples, "typical_section_ditch_v.csv"))
    ditch_trap_rows = _read_csv_rows(os.path.join(samples, "typical_section_ditch_trapezoid.csv"))
    ditch_u_rows = _read_csv_rows(os.path.join(samples, "typical_section_ditch_u.csv"))
    ditch_rows = _read_csv_rows(os.path.join(samples, "typical_section_with_ditch.csv"))
    pavement_rows = _read_csv_rows(os.path.join(samples, "typical_section_pavement_basic.csv"))
    fg_basic_rows = _read_csv_rows(os.path.join(samples, "profile_fg_manual_import_basic.csv"))
    fg_alias_rows = _read_csv_rows(os.path.join(samples, "profile_fg_manual_import_aliases.csv"))
    simple_structure_rows = _read_csv_rows(os.path.join(samples, "structure_utm_realistic_hilly.csv"))
    notch_rows = _read_csv_rows(os.path.join(samples, "structure_utm_realistic_hilly_notch.csv"))
    template_rows = _read_csv_rows(os.path.join(samples, "structure_utm_realistic_hilly_template.csv"))
    external_rows = _read_csv_rows(os.path.join(samples, "structure_utm_realistic_hilly_external_shape.csv"))
    mixed_rows = _read_csv_rows(os.path.join(samples, "structure_utm_realistic_hilly_mixed.csv"))
    mixed_profile_rows = _read_csv_rows(os.path.join(samples, "structure_utm_realistic_hilly_mixed_profile_points.csv"))

    urban_types = {str(r.get("Type", "") or "").strip().lower() for r in urban_rows}
    _assert({"median", "bike_lane", "curb", "sidewalk", "green_strip"}.issubset(urban_types), "Urban sample is missing expected component types")
    ditch_types = {str(r.get("Type", "") or "").strip().lower() for r in ditch_rows}
    _assert({"ditch", "berm"}.issubset(ditch_types), "Ditch sample is missing ditch/berm components")
    _assert(any(str(r.get("Type", "") or "").strip().lower() == "ditch" and str(r.get("Shape", "") or "").strip().lower() == "v" for r in ditch_v_rows), "V-ditch sample should contain Shape=v")
    _assert(any(str(r.get("Type", "") or "").strip().lower() == "ditch" and str(r.get("Shape", "") or "").strip().lower() == "trapezoid" for r in ditch_trap_rows), "Trapezoid-ditch sample should contain Shape=trapezoid")
    _assert(any(str(r.get("Type", "") or "").strip().lower() == "ditch" and str(r.get("Shape", "") or "").strip().lower() == "u" for r in ditch_u_rows), "U-ditch sample should contain Shape=u")
    _assert(sum(_to_float(r, "Thickness") for r in pavement_rows if _to_bool(r, "Enabled", default=True)) > 0.5, "Pavement sample total thickness is unexpectedly small")
    _assert(len(fg_basic_rows) >= 8, "FG basic import sample should have at least 8 rows")
    _assert("Station" in list((fg_basic_rows[0] or {}).keys()), "FG basic import sample should expose Station header")
    _assert("FG" in list((fg_basic_rows[0] or {}).keys()), "FG basic import sample should expose FG header")
    _assert(len(fg_alias_rows) >= 8, "FG alias import sample should have at least 8 rows")
    alias_keys = {str(k) for k in list((fg_alias_rows[0] or {}).keys())}
    _assert({"PK", "DesignElevation"}.issubset(alias_keys), "FG alias import sample should expose PK/DesignElevation headers")
    _assert(all(str(r.get("CorridorMode", "") or "").strip().lower() == "notch" for r in notch_rows), "Notch starter sample should contain only notch corridor rows")
    _assert(all(str(r.get("GeometryMode", "") or "").strip().lower() == "template" for r in template_rows), "Template starter sample should contain only template geometry rows")
    _assert(all(str(r.get("GeometryMode", "") or "").strip().lower() == "external_shape" for r in external_rows), "External-shape starter sample should contain only external-shape rows")
    _assert(any("replace-with-your-models" in str(r.get("ShapeSourcePath", "") or "") for r in external_rows), "External-shape sample should keep placeholder path text")
    _assert(any(str(r.get("CorridorMode", "") or "").strip().lower() == "skip_zone" for r in simple_structure_rows), "Baseline structure sample should include skip_zone rows")
    _assert(any(str(r.get("CorridorMode", "") or "").strip().lower() == "split_only" for r in simple_structure_rows), "Baseline structure sample should include split_only rows")
    mixed_modes = {str(r.get("CorridorMode", "") or "").strip().lower() for r in mixed_rows}
    _assert({"notch", "split_only", "skip_zone", "none"}.issubset(mixed_modes), "Mixed structure sample is missing expected corridor modes")
    mixed_geom = {str(r.get("GeometryMode", "") or "").strip().lower() for r in mixed_rows}
    _assert({"template", "box", "external_shape"}.issubset(mixed_geom), "Mixed structure sample is missing expected geometry modes")
    _assert(len(mixed_profile_rows) >= 9, "Mixed structure profile sample should have at least 9 control points")

    doc = App.newDocument("CRPracticalSampleDrivenWorkflow")
    try:
        aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(aln)
        aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(760.0, 0.0, 0.0)]
        aln.UseTransitionCurves = False

        disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
        Centerline3DDisplay(disp)
        disp.Alignment = aln
        disp.ElevationSource = "FlatZero"
        disp.UseStationing = False

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        asm.UseSideSlopes = True
        asm.LeftSideWidth = 8.0
        asm.RightSideWidth = 8.0
        asm.LeftSideSlopePct = 40.0
        asm.RightSideSlopePct = 40.0

        typ = doc.addObject("Part::FeaturePython", "TypicalSectionTemplate")
        TypicalSectionTemplate(typ)
        _assign_component_rows(typ, urban_rows)
        _assign_pavement_rows(typ, pavement_rows)

        ss = doc.addObject("Part::FeaturePython", "StructureSet")
        StructureSet(ss)
        _assign_structure_rows(ss, mixed_rows)
        _assign_structure_profile_rows(ss, mixed_profile_rows)

        sec = doc.addObject("Part::FeaturePython", "SectionSet")
        SectionSet(sec)
        sec.SourceCenterlineDisplay = disp
        sec.AssemblyTemplate = asm
        sec.TypicalSectionTemplate = typ
        sec.UseTypicalSectionTemplate = True
        sec.UseStructureSet = True
        sec.StructureSet = ss
        sec.IncludeStructureStartEnd = True
        sec.IncludeStructureCenters = True
        sec.IncludeStructureTransitionStations = True
        sec.AutoStructureTransitionDistance = False
        sec.StructureTransitionDistance = 10.0
        sec.ApplyStructureOverrides = True
        sec.Mode = "Range"
        sec.StartStation = 0.0
        sec.EndStation = 760.0
        sec.Interval = 80.0
        sec.IncludeAlignmentIPStations = False
        sec.IncludeAlignmentSCCSStations = False
        sec.CreateChildSections = False

        cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
        CorridorLoft(cor)
        cor.SourceSectionSet = sec
        cor.UseStructureCorridorModes = True
        cor.SplitAtStructureZones = True

        dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
        DesignGradingSurface(dgs)
        dgs.SourceSectionSet = sec

        doc.recompute()

        _assert(_shape_ok(typ), "TypicalSectionTemplate did not generate geometry from practical sample CSV")
        _assert(_shape_ok(sec), "SectionSet did not generate geometry from practical sample workflow")
        _assert(_shape_ok(cor), "CorridorLoft did not generate geometry from practical sample workflow")
        _assert(_mesh_ok(dgs), "DesignGradingSurface did not generate mesh from practical sample workflow")

        _assert(int(getattr(typ, "AdvancedComponentCount", 0) or 0) >= 2, "Practical sample typical section should report advanced components")
        _assert(int(getattr(typ, "ReportSchemaVersion", 0) or 0) == 1, "TypicalSectionTemplate report schema mismatch")
        _assert(len(list(getattr(typ, "PavementScheduleRows", []) or [])) >= 4, "TypicalSectionTemplate pavement schedule rows missing")
        _assert("roadside=" in str(getattr(typ, "Status", "") or ""), "TypicalSectionTemplate status missing roadside summary")

        _assert(int(getattr(sec, "SectionSchemaVersion", 0) or 0) == 2, "SectionSet schema mismatch")
        _assert(int(getattr(sec, "ResolvedStructureCount", 0) or 0) >= 12, "SectionSet resolved structure count is too low for mixed sample")
        _assert(len(list(getattr(sec, "StructureInteractionSummaryRows", []) or [])) >= 1, "SectionSet structure interaction report rows missing")
        sec_status = str(getattr(sec, "Status", "") or "")
        _assert("practical=advanced" in sec_status, "SectionSet status missing practical mode token")
        _assert("subSchema=" in sec_status, "SectionSet status missing subassembly schema token")
        _assert("structures=" in sec_status, "SectionSet status missing structure count token")

        cor_mode_summary = str(getattr(cor, "ResolvedStructureCorridorModeSummary", "") or "")
        _assert("notch=" in cor_mode_summary, "CorridorLoft corridor mode summary missing notch")
        _assert("split_only=" in cor_mode_summary, "CorridorLoft corridor mode summary missing split_only")
        _assert("skip_zone=" in cor_mode_summary, "CorridorLoft corridor mode summary missing skip_zone")
        _assert(len(list(getattr(cor, "ResolvedNotchStructureIds", []) or [])) >= 1, "CorridorLoft notch structure ids missing")
        _assert(len(list(getattr(cor, "ExportSummaryRows", []) or [])) >= 1, "CorridorLoft export summary rows missing")
        cor_status = str(getattr(cor, "Status", "") or "")
        _assert("corridorModes=" in cor_status, "CorridorLoft status missing corridor mode token")
        _assert("typicalAdvanced=" in cor_status, "CorridorLoft status missing advanced typical summary")

        dgs_status = str(getattr(dgs, "Status", "") or "")
        _assert("earthwork=" in dgs_status, "DesignGradingSurface status missing earthwork token")
        _assert("practical=advanced" in dgs_status, "DesignGradingSurface status missing practical mode token")
        _assert(len(list(getattr(dgs, "ExportSummaryRows", []) or [])) >= 1, "DesignGradingSurface export summary rows missing")

        App.closeDocument(doc.Name)
        print("[PASS] Practical sample-driven workflow smoke test completed.")
    finally:
        try:
            App.closeDocument(doc.Name)
        except Exception:
            pass


if __name__ == "__main__":
    run()
