# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Mixed region/structure corridor precedence smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_structure_corridor_precedence.py
"""

import FreeCAD as App

from freecad.Corridor_Road.corridor_compat import CORRIDOR_CHILD_LINK_PROPERTY
from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor import Corridor
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
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


def run():
    doc = App.newDocument("CRRegionStructureCorridorPrecedence")

    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(100.0, 0.0, 0.0)]
    aln.UseTransitionCurves = False

    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False

    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.UseSideSlopes = False

    reg = doc.addObject("Part::FeaturePython", "RegionPlan")
    RegionPlan(reg)
    reg.RegionIds = ["BASE_A", "BASE_SKIP", "BASE_B"]
    reg.RegionTypes = ["roadway", "earthwork_zone", "roadway"]
    reg.Layers = ["base", "base", "base"]
    reg.StartStations = [0.0, 40.0, 80.0]
    reg.EndStations = [40.0, 80.0, 100.0]
    reg.Priorities = [0, 0, 0]
    reg.CorridorPolicies = ["", "skip_zone", ""]
    reg.EnabledFlags = ["true", "true", "true"]

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)
    ss.StructureIds = ["STR_SPLIT"]
    ss.StructureTypes = ["bridge_zone"]
    ss.StartStations = [60.0]
    ss.EndStations = [70.0]
    ss.CenterStations = [65.0]
    ss.Sides = ["both"]
    ss.Widths = [8.0]
    ss.Heights = [4.0]
    ss.CorridorModes = ["split_only"]

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Range"
    sec.StartStation = 0.0
    sec.EndStation = 100.0
    sec.Interval = 20.0
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.UseRegionPlan = True
    sec.RegionPlan = reg
    sec.IncludeRegionBoundaries = True
    sec.IncludeRegionTransitions = False
    sec.UseStructureSet = True
    sec.StructureSet = ss
    sec.IncludeStructureStartEnd = True
    sec.IncludeStructureCenters = False
    sec.IncludeStructureTransitionStations = False
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "Corridor")
    Corridor(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = True
    cor.UseRegionCorridorModes = True
    cor.SplitAtStructureZones = True

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "Corridor did not generate geometry")
    _assert(int(getattr(cor, "StructureSegmentCount", 0) or 0) == 2, "Mixed corridor segment count mismatch")
    _assert(list(getattr(cor, "SkippedStationRanges", []) or []) == ["40.000-60.000"], "Mixed skipped ranges mismatch")

    structure_mode_summary = str(getattr(cor, "ResolvedStructureCorridorModeSummary", "-") or "-")
    region_mode_summary = str(getattr(cor, "ResolvedRegionCorridorModeSummary", "-") or "-")
    combined_mode_summary = str(getattr(cor, "ResolvedCombinedCorridorModeSummary", "-") or "-")
    _assert(structure_mode_summary == "split_only=1", "Structure mode summary mismatch")
    _assert(region_mode_summary == "skip_zone=1", "Region mode summary mismatch")
    _assert(combined_mode_summary.startswith("mixed|"), "Combined mode summary should report mixed precedence")
    _assert("split_only=1" in combined_mode_summary, "Combined mode summary missing split_only")
    _assert("skip_zone=1" in combined_mode_summary, "Combined mode summary missing skip_zone")

    structure_ranges = list(getattr(cor, "ResolvedStructureCorridorRanges", []) or [])
    region_ranges = list(getattr(cor, "ResolvedRegionCorridorRanges", []) or [])
    combined_ranges = list(getattr(cor, "ResolvedCombinedCorridorRanges", []) or [])
    _assert(structure_ranges == ["STR_SPLIT:bridge_zone:split_only:60.000-70.000"], "Structure range diagnostics mismatch")
    _assert(region_ranges == ["BASE_SKIP:region:skip_zone:40.000-70.000 (source=section_regions)"], "Region range diagnostics mismatch")
    _assert(
        combined_ranges == [
            "BASE_SKIP:region:skip_zone:40.000-60.000 (source=region)",
            "STR_SPLIT:structure:split_only:60.000-70.000 (source=structure)",
        ],
        f"Combined range diagnostics mismatch: {combined_ranges}",
    )

    combined_warnings = list(getattr(cor, "ResolvedCombinedCorridorWarnings", []) or [])
    _assert(
        combined_warnings == ["BASE_SKIP: overridden by structure corridor mode 'split_only' from STR_SPLIT"],
        f"Combined warnings mismatch: {combined_warnings}",
    )
    segment_rows = list(getattr(cor, "SegmentSummaryRows", []) or [])
    _assert(any("corridor_segment|" in row and "source=structure+region" in row for row in segment_rows), "Segment summary rows should report mixed structure+region segmentation")
    _assert(int(getattr(cor, "CorridorSegmentCount", 0) or 0) == 2, "CorridorSegmentCount mismatch for mixed structure/region segmentation")
    _assert(int(getattr(cor, "SkippedSegmentCount", 0) or 0) == 1, "SkippedSegmentCount mismatch for mixed structure/region segmentation")
    _assert(int(getattr(cor, "MixedSegmentCount", 0) or 0) == 2, "MixedSegmentCount mismatch for mixed structure/region segmentation")
    _assert(int(getattr(cor, "RegionSegmentCount", 0) or 0) == 0, "RegionSegmentCount should stay zero for mixed rows")
    _assert(int(getattr(cor, "StructureDrivenSegmentCount", 0) or 0) == 0, "StructureDrivenSegmentCount should stay zero for mixed rows")
    _assert(str(getattr(cor, "SegmentKindSummary", "-") or "-") == "segment=2, skip=1", "SegmentKindSummary mismatch for mixed structure/region segmentation")
    _assert(str(getattr(cor, "SegmentSourceSummary", "-") or "-") == "mixed=2", "SegmentSourceSummary mismatch for mixed structure/region segmentation")
    driver_source_summary = str(getattr(cor, "SegmentDriverSourceSummary", "-") or "-")
    driver_mode_summary = str(getattr(cor, "SegmentDriverModeSummary", "-") or "-")
    profile_contract_summary = str(getattr(cor, "SegmentProfileContractSummary", "-") or "-")
    package_summary = str(getattr(cor, "SegmentPackageSummary", "-") or "-")
    _assert("structure=1" in driver_source_summary, "SegmentDriverSourceSummary should include a structure-driven package")
    _assert("split_only=1" in driver_mode_summary, "SegmentDriverModeSummary should include a split_only-driven package")
    _assert(profile_contract_summary == "section_profiles=2", "SegmentProfileContractSummary mismatch for mixed precedence")
    _assert("src[full=1, structure=1]" in package_summary and "mode[-=1, split_only=1]" in package_summary and "contract[section_profiles=2]" in package_summary, "SegmentPackageSummary mismatch for mixed precedence")
    package_rows = list(getattr(cor, "SegmentPackageRows", []) or [])
    _assert(int(getattr(cor, "SegmentPackageCount", 0) or 0) == 2, "SegmentPackageCount mismatch for mixed structure/region segmentation")
    _assert(int(getattr(cor, "SegmentObjectCount", 0) or 0) == 2, "SegmentObjectCount mismatch for mixed structure/region segmentation")
    _assert(len(package_rows) == 2, "Mixed structure/region segmentation should create two segment packages")
    _assert(any("corridor_package|" in row and "source=structure+region" in row and "pairCount=" in row for row in package_rows), "SegmentPackageRows should report mixed structure+region package rows")
    _assert(any("driverId=STR_SPLIT" in row and "driverSource=structure" in row for row in package_rows), "SegmentPackageRows should report effective structure driver details")
    _assert(all("profileContract=section_profiles" in row for row in package_rows), "SegmentPackageRows should carry the section_profiles contract source for mixed precedence")
    segment_objs = [
        o
        for o in list(getattr(doc, "Objects", []) or [])
        if str(getattr(o, "Name", "") or "").startswith("CorridorSegment")
        and getattr(o, CORRIDOR_CHILD_LINK_PROPERTY, None) == cor
    ]
    _assert(len(segment_objs) == 2, "Mixed structure/region segmentation should create two CorridorSegment children")
    _assert(all(_shape_ok(o) for o in segment_objs), "CorridorSegment children should carry valid shapes")
    _assert(any(str(getattr(o, "DriverId", "") or "") == "STR_SPLIT" and str(getattr(o, "DriverSource", "") or "") == "structure" for o in segment_objs), "CorridorSegment child should carry effective structure driver details")
    _assert(all(str(getattr(o, "ProfileContractSource", "-") or "-") == "section_profiles" for o in segment_objs), "CorridorSegment children should carry the section_profiles contract source for mixed precedence")
    _assert(any("structure:STR_SPLIT:split_only[section_profiles]" in str(getattr(o, "Label", "") or "") for o in segment_objs), "CorridorSegment label should expose readable structure driver info and contract source")
    _assert(any("structure:STR_SPLIT:split_only@" in str(getattr(o, "SegmentSummary", "") or "") and "|contract=section_profiles" in str(getattr(o, "SegmentSummary", "") or "") for o in segment_objs), "CorridorSegment summary should expose readable structure driver info and contract source")
    cor_export = list(getattr(cor, "ExportSummaryRows", []) or [])
    _assert(len(cor_export) == 1 and "segmentRows=" in cor_export[0], "Corridor export summary should include segmentRows")
    _assert("segmentPackages=2" in cor_export[0], "Corridor export summary should include segmentPackages")
    _assert("segmentObjects=2" in cor_export[0], "Corridor export summary should include segmentObjects")
    _assert("segmentKinds=segment=2, skip=1" in cor_export[0], "Corridor export summary should include segmentKinds")
    _assert("segmentDrivers=mixed=2" in cor_export[0], "Corridor export summary should include segmentDrivers")
    _assert("segmentDriverSources=" in cor_export[0] and "structure=1" in cor_export[0], "Corridor export summary should include usable segmentDriverSources")
    _assert("segmentDriverModes=" in cor_export[0] and "split_only=1" in cor_export[0], "Corridor export summary should include usable segmentDriverModes")
    _assert("segmentProfileContracts=section_profiles=2" in cor_export[0], "Corridor export summary should include segmentProfileContracts")
    _assert("segmentPackageSummary=" in cor_export[0] and "contract[section_profiles=2]" in cor_export[0], "Corridor export summary should include segmentPackageSummary")
    _assert("segmentDisplay=" in cor_export[0] and "structure:STR_SPLIT:split_only@" in cor_export[0] and "contract=section_profiles" in cor_export[0], "Corridor export summary should include usable segmentDisplay with contract source")

    status = str(getattr(cor, "Status", "") or "")
    _assert("corridorRule=mixed" in status, "Corridor status missing mixed corridor token")
    _assert("corridorModes=mixed|" in status, "Corridor status missing mixed combined mode summary")
    _assert("regionCorridorModes=skip_zone=1" in status, "Corridor status missing region corridor summary")
    _assert("structCorridorModes=split_only=1" in status, "Corridor status missing structure corridor summary")
    _assert("corridorWarn=1" in status, "Corridor status missing mixed warning count")
    _assert("segmentRows=" in status, "Corridor status missing segmentRows token")
    _assert("segmentPackages=2" in status, "Corridor status missing segmentPackages token")
    _assert("segmentObjects=2" in status, "Corridor status missing segmentObjects token")
    _assert("segmentSources=structure+region" in status, "Corridor status missing segmentSources token")
    _assert("segmentKinds=segment=2, skip=1" in status, "Corridor status missing segmentKinds token")
    _assert("segmentDrivers=mixed=2" in status, "Corridor status missing segmentDrivers token")
    _assert("segmentDriverSources=" in status and "structure=1" in status, "Corridor status missing usable segmentDriverSources token")
    _assert("segmentDriverModes=" in status and "split_only=1" in status, "Corridor status missing usable segmentDriverModes token")
    _assert("segmentProfileContracts=section_profiles=2" in status, "Corridor status missing segmentProfileContracts token")
    _assert("segmentPackageSummary=" in status and "contract[section_profiles=2]" in status, "Corridor status missing segmentPackageSummary token")
    _assert("segmentDisplay=" in status and "structure:STR_SPLIT:split_only@" in status and "contract=section_profiles" in status, "Corridor status missing usable segmentDisplay token with contract source")
    _assert("diagSource=ok" in status, "Corridor status missing diagSource token")
    _assert("diagConnectivity=ok" in status, "Corridor status missing diagConnectivity token")
    _assert("diagPackaging=info" in status, "Corridor status missing diagPackaging token")
    _assert("diagPolicy=warn" in status, "Corridor status missing diagPolicy token")
    _assert("diagClasses=source:ok, connectivity:ok, packaging:info, policy:warn" in status, "Corridor status missing diagnostic class summary")
    _assert(str(getattr(cor, "DiagnosticSummary", "-") or "-") == "source=ok, connectivity=ok, packaging=info, policy=warn", "DiagnosticSummary mismatch for mixed precedence")
    _assert(str(getattr(cor, "DiagnosticClassSummary", "-") or "-") == "source:ok, connectivity:ok, packaging:info, policy:warn", "DiagnosticClassSummary mismatch for mixed precedence")
    _assert(str(getattr(cor, "SourceDiagnostic", "-") or "-").startswith("ok|section_set"), "SourceDiagnostic mismatch for mixed precedence")
    _assert(str(getattr(cor, "ConnectivityDiagnostic", "-") or "-") == "ok|clean", "ConnectivityDiagnostic should use clean summary for mixed precedence")
    _assert(str(getattr(cor, "PackagingDiagnostic", "-") or "-") == "info|segmented", "PackagingDiagnostic should use segmented summary for mixed precedence")
    _assert(str(getattr(cor, "PolicyDiagnostic", "-") or "-") == "warn|mixed", "PolicyDiagnostic should summarize mixed corridor precedence")
    diag_rows = list(getattr(cor, "DiagnosticRows", []) or [])
    _assert(len(diag_rows) == 4, "DiagnosticRows should include four diagnostic categories for mixed precedence")
    _assert(any("corridor_diag|kind=policy|state=warn" in row for row in diag_rows), "DiagnosticRows should include policy warn row")
    _assert(any("corridor_diag|kind=connectivity|state=ok|summary=clean" in row and "sections=" in row for row in diag_rows), "DiagnosticRows should retain connectivity detail counts for mixed precedence")
    _assert(any("corridor_diag|kind=packaging|state=info|summary=segmented" in row and "packages=2" in row for row in diag_rows), "DiagnosticRows should retain packaging detail counts for mixed precedence")
    _assert(any("corridor_diag|kind=policy|state=warn|summary=mixed" in row and "warnings=1" in row for row in diag_rows), "DiagnosticRows should retain policy warning detail for mixed precedence")

    App.closeDocument(doc.Name)
    print("[PASS] Mixed region/structure corridor precedence smoke test completed.")


if __name__ == "__main__":
    run()
