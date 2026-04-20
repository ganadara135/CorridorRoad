# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Notch profile contract smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_notch_profile_contract.py
"""

import FreeCAD as App

from freecad.Corridor_Road.corridor_compat import CORRIDOR_CHILD_LINK_PROPERTY
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor import Corridor
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet


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


def _make_alignment(doc, length=120.0):
    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(float(length), 0.0, 0.0)]
    aln.UseTransitionCurves = False
    return aln


def _make_display(doc, aln):
    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False
    return disp


def _make_assembly(doc):
    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.UseSideSlopes = False
    asm.LeftWidth = 5.0
    asm.RightWidth = 5.0
    asm.HeightLeft = 4.0
    asm.HeightRight = 4.0
    return asm


def run():
    doc = App.newDocument("CRNotchProfileContract")

    aln = _make_alignment(doc)
    disp = _make_display(doc, aln)
    asm = _make_assembly(doc)

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    ss.StructureIds = ["CULV_VAR"]
    ss.StructureTypes = ["culvert"]
    ss.StartStations = [50.0]
    ss.EndStations = [70.0]
    ss.CenterStations = [60.0]
    ss.Sides = ["both"]
    ss.Widths = [4.0]
    ss.Heights = [2.0]
    ss.CorridorModes = ["notch"]

    ss.ProfileStructureIds = ["CULV_VAR", "CULV_VAR", "CULV_VAR"]
    ss.ProfileStations = [50.0, 60.0, 70.0]
    ss.ProfileWidths = [4.0, 8.0, 6.0]
    ss.ProfileHeights = [2.0, 3.0, 2.5]
    ss.ProfileBottomElevations = [1.0, 1.2, 1.1]

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 40.0
    sec.EndStation = 80.0
    sec.Interval = 20.0
    sec.UseStructureSet = True
    sec.StructureSet = ss
    sec.IncludeStructureStartEnd = True
    sec.IncludeStructureCenters = True
    sec.IncludeStructureTransitionStations = True
    sec.AutoStructureTransitionDistance = False
    sec.StructureTransitionDistance = 5.0
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "Corridor")
    Corridor(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = True
    cor.SplitAtStructureZones = True
    cor.DefaultStructureCorridorMode = "split_only"
    cor.NotchTransitionScale = 1.0

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "Corridor did not generate geometry")
    _assert(int(getattr(cor, "ClosedProfileSchemaVersion", 0) or 0) == 2, "Notch workflow should use closed profile schema 2")
    _assert(len(list(getattr(getattr(cor, "Shape", None), "Solids", []) or [])) == 0, "Corridor should not generate solids in surface mode")
    _assert(str(getattr(cor, "ResolvedNotchSchemaName", "") or "") == "notch_v1_8pt", "Unexpected notch schema name")
    _assert(int(getattr(cor, "ResolvedNotchStationCount", 0) or 0) == 5, "Unexpected notch-aware station count")
    _assert(int(getattr(cor, "ResolvedStructureNotchCount", 0) or 0) == 1, "Unexpected notch structure count")
    _assert(list(getattr(cor, "ResolvedNotchStructureIds", []) or []) == ["CULV_VAR"], "Unexpected notch structure ids")
    _assert(str(getattr(cor, "ResolvedNotchBuildMode", "") or "") == "schema_profiles", "Unexpected notch build mode")
    _assert(int(getattr(cor, "ResolvedNotchCutterCount", 0) or 0) == 0, "Notch schema path should not rely on cutters")
    _assert(str(getattr(cor, "ResolvedRuledMode", "") or "") == "auto:notch_schema", "Expected auto notch-schema ruled mode")
    _assert(str(getattr(cor, "ProfileContractSource", "-") or "-") == "notch_schema_profiles", "Notch workflow should report notch_schema_profiles contract source")
    _assert("notch_schema_profiles" in str(getattr(cor, "SegmentProfileContractSummary", "-") or "-"), "Notch workflow should summarize notch_schema_profiles package contract")
    _assert("contract[notch_schema_profiles=" in str(getattr(cor, "SegmentPackageSummary", "-") or "-"), "Notch workflow should include notch_schema_profiles in segment package summary")

    notch_summary = str(getattr(cor, "ResolvedNotchProfileSummary", "") or "")
    _assert("schema=notch_v1_8pt" in notch_summary, "Notch summary missing schema name")
    _assert("active=3" in notch_summary, "Notch summary missing active-station count")
    _assert("transition=2" in notch_summary, "Notch summary missing transition-station count")
    _assert("station_profile=5" in notch_summary, "Notch summary missing station-profile usage")

    profile_rows = list(getattr(cor, "ResolvedNotchProfileRows", []) or [])
    _assert(len(profile_rows) == 5, "Expected 5 notch profile rows")
    _assert(any("CULV_VAR@45.000" in row and "roles=transition_before" in row and "ramp=0.004" in row for row in profile_rows), "Missing transition-before notch diagnostic")
    _assert(any("CULV_VAR@50.000" in row and "roles=start,active" in row and "ramp=0.350" in row for row in profile_rows), "Missing start-of-span notch diagnostic")
    _assert(any("CULV_VAR@60.000" in row and "profile=station_profile" in row and "width=10.800" in row and "height=4.200" in row for row in profile_rows), "Missing profile-driven mid-span notch diagnostic")
    _assert(any("CULV_VAR@70.000" in row and "roles=end,active" in row and "ramp=0.350" in row for row in profile_rows), "Missing end-of-span notch diagnostic")
    _assert(any("CULV_VAR@75.000" in row and "roles=transition_after" in row and "ramp=0.004" in row for row in profile_rows), "Missing transition-after notch diagnostic")
    _assert(any("bottomMode=bottom_elevation" in row for row in profile_rows), "Expected bottom-elevation-based notch diagnostic")
    split_stations = list(getattr(cor, "StructureSplitStations", []) or [])
    _assert(split_stations == ["45.000", "50.000", "75.000", "80.000"], "Unexpected structure split-station diagnostics")

    package_rows = list(getattr(cor, "SegmentPackageRows", []) or [])
    _assert(len(package_rows) >= 1, "Notch workflow should expose segment package rows")
    _assert(all("profileContract=notch_schema_profiles" in row for row in package_rows), "Notch package rows should carry the notch_schema_profiles contract source")
    _assert(any("driverSource=structure" in row and "driverMode=notch" in row for row in package_rows), "Notch package rows should expose effective structure/notch driver details")

    segment_objs = [
        o
        for o in list(getattr(doc, "Objects", []) or [])
        if str(getattr(o, "Name", "") or "").startswith("CorridorSegment")
        and getattr(o, CORRIDOR_CHILD_LINK_PROPERTY, None) == cor
    ]
    _assert(len(segment_objs) >= 1, "Notch workflow should create CorridorSegment children")
    _assert(all(str(getattr(o, "ProfileContractSource", "-") or "-") == "notch_schema_profiles" for o in segment_objs), "Notch CorridorSegment children should carry notch_schema_profiles contract source")
    _assert(any(str(getattr(o, "DriverSource", "") or "") == "structure" and str(getattr(o, "DriverMode", "") or "") == "notch" for o in segment_objs), "Notch CorridorSegment child should expose effective structure/notch driver details")
    _assert(any("[notch_schema_profiles]" in str(getattr(o, "Label", "") or "") for o in segment_objs), "Notch CorridorSegment labels should expose contract source")
    _assert(any("|contract=notch_schema_profiles" in str(getattr(o, "SegmentSummary", "") or "") for o in segment_objs), "Notch CorridorSegment summaries should expose contract source")

    cor_status = str(getattr(cor, "Status", "") or "")
    _assert(cor_status.startswith("OK (Surface)"), "Corridor status should report successful surface build")
    _assert("output=surface" in cor_status, "Corridor status should report surface output")
    _assert("notchSchema=notch_v1_8pt" in cor_status, "Corridor status missing notch schema token")
    _assert("notchProfile=schema=notch_v1_8pt" in cor_status, "Corridor status missing notch profile summary token")
    _assert("notchBuild=schema_profiles" in cor_status, "Corridor status missing notch build-mode token")
    _assert("structureSegs=4" in cor_status, "Corridor status missing structure-segmentation token")
    _assert("corridorRule=structure_aware" in cor_status, "Corridor status missing structure-aware token")
    _assert("profileContract=notch_schema_profiles" in cor_status, "Corridor status should expose notch_schema_profiles contract source")
    _assert("segmentProfileContracts=" in cor_status and "notch_schema_profiles" in cor_status, "Corridor status should expose package-level notch contract summary")
    _assert("segmentPackageSummary=" in cor_status and "contract[notch_schema_profiles=" in cor_status, "Corridor status should expose segmentPackageSummary for notch workflow")

    ss_invalid = doc.addObject("Part::FeaturePython", "StructureSetInvalid")
    StructureSet(ss_invalid)
    ss_invalid.StructureIds = ["WALL_BAD"]
    ss_invalid.StructureTypes = ["retaining_wall"]
    ss_invalid.StartStations = [10.0]
    ss_invalid.EndStations = [20.0]
    ss_invalid.CenterStations = [15.0]
    ss_invalid.Sides = ["left"]
    ss_invalid.Widths = [3.0]
    ss_invalid.Heights = [4.0]
    ss_invalid.CorridorModes = ["notch"]
    issues = StructureSet.validate(ss_invalid)
    _assert(any("retaining_wall should use split_only rather than notch" in row for row in issues), "Missing retaining-wall notch validation warning")

    App.closeDocument(doc.Name)
    print("[PASS] Notch profile contract smoke test completed.")


if __name__ == "__main__":
    run()
