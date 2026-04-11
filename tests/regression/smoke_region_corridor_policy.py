# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Region-driven corridor policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_region_corridor_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan
from freecad.Corridor_Road.objects.obj_section_set import SectionSet


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
    doc = App.newDocument("CRRegionCorridorPolicy")

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
    reg.RegionIds = ["BASE_A", "BASE_SPLIT", "BASE_SKIP"]
    reg.RegionTypes = ["roadway", "bridge_approach", "earthwork_zone"]
    reg.Layers = ["base", "base", "base"]
    reg.StartStations = [0.0, 30.0, 70.0]
    reg.EndStations = [30.0, 70.0, 90.0]
    reg.Priorities = [0, 0, 0]
    reg.CorridorPolicies = ["", "split_only", "skip_zone"]
    reg.EnabledFlags = ["true", "true", "true"]

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
    sec.CreateChildSections = False

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    cor.UseStructureCorridorModes = False
    cor.UseRegionCorridorModes = True
    cor.SplitAtStructureZones = True

    doc.recompute()

    _assert(_shape_ok(sec), "SectionSet did not generate geometry")
    _assert(_shape_ok(cor), "CorridorLoft did not generate geometry")
    _assert(int(getattr(cor, "StructureSegmentCount", 0) or 0) == 2, "Corridor segment count mismatch for region-driven split/skip")
    _assert(list(getattr(cor, "SkippedStationRanges", []) or []) == ["70.000-90.000"], "Region skip-zone ranges mismatch")

    region_mode_summary = str(getattr(cor, "ResolvedRegionCorridorModeSummary", "-") or "-")
    combined_mode_summary = str(getattr(cor, "ResolvedCombinedCorridorModeSummary", "-") or "-")
    _assert("split_only=1" in region_mode_summary, "Region mode summary missing split_only")
    _assert("skip_zone=1" in region_mode_summary, "Region mode summary missing skip_zone")
    _assert(combined_mode_summary.startswith("region|"), "Combined mode summary should report region source")
    _assert("split_only=1" in combined_mode_summary, "Combined mode summary missing split_only")
    _assert("skip_zone=1" in combined_mode_summary, "Combined mode summary missing skip_zone")

    region_ranges = list(getattr(cor, "ResolvedRegionCorridorRanges", []) or [])
    combined_ranges = list(getattr(cor, "ResolvedCombinedCorridorRanges", []) or [])
    _assert(any("BASE_SPLIT:region:split_only:30.000-60.000" in row for row in region_ranges), "Missing split_only region detail row")
    _assert(any("BASE_SKIP:region:skip_zone:70.000-90.000" in row for row in region_ranges), "Missing skip_zone region detail row")
    _assert(any("BASE_SPLIT:region:split_only:30.000-60.000" in row for row in combined_ranges), "Missing split_only combined row")
    _assert(any("BASE_SKIP:region:skip_zone:70.000-90.000" in row for row in combined_ranges), "Missing skip_zone combined row")
    _assert(len(list(getattr(cor, "ResolvedCombinedCorridorWarnings", []) or [])) == 0, "Region-only combined warnings should stay empty")
    segment_rows = list(getattr(cor, "SegmentSummaryRows", []) or [])
    _assert(any("corridor_segment|" in row and "source=region" in row for row in segment_rows), "Segment summary rows should report region-driven corridor segments")
    _assert(any("corridor_skip|" in row and "70.000-90.000" in row for row in segment_rows), "Segment summary rows should report skipped region span")
    _assert(int(getattr(cor, "CorridorSegmentCount", 0) or 0) == 2, "CorridorSegmentCount mismatch for region-driven split/skip")
    _assert(int(getattr(cor, "SkippedSegmentCount", 0) or 0) == 1, "SkippedSegmentCount mismatch for region-driven split/skip")
    _assert(int(getattr(cor, "RegionSegmentCount", 0) or 0) == 2, "RegionSegmentCount mismatch for region-driven split/skip")
    _assert(int(getattr(cor, "MixedSegmentCount", 0) or 0) == 0, "MixedSegmentCount should stay zero for region-only segmentation")
    _assert(str(getattr(cor, "SegmentKindSummary", "-") or "-") == "segment=2, skip=1", "SegmentKindSummary mismatch")
    _assert(str(getattr(cor, "SegmentSourceSummary", "-") or "-") == "region=2", "SegmentSourceSummary mismatch")
    driver_source_summary = str(getattr(cor, "SegmentDriverSourceSummary", "-") or "-")
    driver_mode_summary = str(getattr(cor, "SegmentDriverModeSummary", "-") or "-")
    profile_contract_summary = str(getattr(cor, "SegmentProfileContractSummary", "-") or "-")
    package_summary = str(getattr(cor, "SegmentPackageSummary", "-") or "-")
    _assert("region=1" in driver_source_summary, "SegmentDriverSourceSummary should include a region-driven package")
    _assert("split_only=1" in driver_mode_summary, "SegmentDriverModeSummary should include a split_only-driven package")
    _assert(profile_contract_summary == "section_profiles=2", "SegmentProfileContractSummary mismatch for region-driven split/skip")
    _assert("src[region=1, full=1]" in package_summary and "mode[-=1, split_only=1]" in package_summary and "contract[section_profiles=2]" in package_summary, "SegmentPackageSummary mismatch for region-driven split/skip")
    package_rows = list(getattr(cor, "SegmentPackageRows", []) or [])
    _assert(int(getattr(cor, "SegmentPackageCount", 0) or 0) == 2, "SegmentPackageCount mismatch for region-driven split/skip")
    _assert(int(getattr(cor, "SegmentObjectCount", 0) or 0) == 2, "SegmentObjectCount mismatch for region-driven split/skip")
    _assert(len(package_rows) == 2, "Region-driven split/skip should create two segment packages")
    _assert(any("corridor_package|" in row and "source=region" in row and "pairCount=" in row for row in package_rows), "SegmentPackageRows should report region-driven package rows")
    _assert(any("driverId=BASE_SPLIT" in row and "driverSource=region" in row for row in package_rows), "SegmentPackageRows should report region driver details")
    _assert(all("profileContract=section_profiles" in row for row in package_rows), "SegmentPackageRows should carry the section_profiles contract source")
    segment_objs = [
        o
        for o in list(getattr(doc, "Objects", []) or [])
        if str(getattr(o, "Name", "") or "").startswith("CorridorSegment")
        and getattr(o, "ParentCorridorLoft", None) == cor
    ]
    _assert(len(segment_objs) == 2, "Region-driven split/skip should create two CorridorSegment children")
    _assert(all(_shape_ok(o) for o in segment_objs), "CorridorSegment children should carry valid shapes")
    _assert(any(str(getattr(o, "DriverId", "") or "") == "BASE_SPLIT" and str(getattr(o, "DriverSource", "") or "") == "region" for o in segment_objs), "CorridorSegment child should carry region driver details")
    _assert(all(str(getattr(o, "ProfileContractSource", "-") or "-") == "section_profiles" for o in segment_objs), "CorridorSegment children should carry the section_profiles contract source")
    _assert(any("region:BASE_SPLIT:split_only[section_profiles]" in str(getattr(o, "Label", "") or "") for o in segment_objs), "CorridorSegment label should expose readable region driver info and contract source")
    _assert(any("region:BASE_SPLIT:split_only@" in str(getattr(o, "SegmentSummary", "") or "") and "|contract=section_profiles" in str(getattr(o, "SegmentSummary", "") or "") for o in segment_objs), "CorridorSegment summary should expose readable region driver info and contract source")

    status = str(getattr(cor, "Status", "") or "")
    _assert("corridorRule=region_aware" in status, "CorridorLoft status missing region-aware token")
    _assert("corridorModes=region|" in status, "CorridorLoft status missing combined region mode summary")
    _assert("regionCorridorModes=split_only=1, skip_zone=1" in status, "CorridorLoft status missing region mode summary")
    _assert("skipZones=1" in status, "CorridorLoft status missing skip-zone summary")
    _assert("segmentPackages=2" in status, "CorridorLoft status missing segmentPackages token")
    _assert("segmentObjects=2" in status, "CorridorLoft status missing segmentObjects token")
    _assert("segmentKinds=segment=2, skip=1" in status, "CorridorLoft status missing segmentKinds token")
    _assert("segmentDrivers=region=2" in status, "CorridorLoft status missing segmentDrivers token")
    _assert("segmentDriverSources=" in status and "region=1" in status, "CorridorLoft status missing usable segmentDriverSources token")
    _assert("segmentDriverModes=" in status and "split_only=1" in status, "CorridorLoft status missing usable segmentDriverModes token")
    _assert("segmentProfileContracts=section_profiles=2" in status, "CorridorLoft status missing segmentProfileContracts token")
    _assert("segmentPackageSummary=" in status and "contract[section_profiles=2]" in status, "CorridorLoft status missing segmentPackageSummary token")
    _assert("segmentDisplay=" in status and "region:BASE_SPLIT:split_only@" in status and "contract=section_profiles" in status, "CorridorLoft status missing usable segmentDisplay token with contract source")
    _assert("diagSource=ok" in status, "CorridorLoft status missing diagSource token")
    _assert("diagConnectivity=ok" in status, "CorridorLoft status missing diagConnectivity token")
    _assert("diagPackaging=info" in status, "CorridorLoft status missing diagPackaging token")
    _assert("diagPolicy=info" in status, "CorridorLoft status missing diagPolicy token")
    _assert("diagClasses=source:ok, connectivity:ok, packaging:info, policy:info" in status, "CorridorLoft status missing diagnostic class summary")
    _assert(str(getattr(cor, "DiagnosticSummary", "-") or "-") == "source=ok, connectivity=ok, packaging=info, policy=info", "DiagnosticSummary mismatch")
    _assert(str(getattr(cor, "DiagnosticClassSummary", "-") or "-") == "source:ok, connectivity:ok, packaging:info, policy:info", "DiagnosticClassSummary mismatch")
    _assert(str(getattr(cor, "SourceDiagnostic", "-") or "-").startswith("ok|section_set"), "SourceDiagnostic mismatch")
    _assert(str(getattr(cor, "ConnectivityDiagnostic", "-") or "-") == "ok|clean", "ConnectivityDiagnostic should use clean summary")
    _assert(str(getattr(cor, "PackagingDiagnostic", "-") or "-") == "info|segmented", "PackagingDiagnostic should use segmented summary")
    _assert(str(getattr(cor, "PolicyDiagnostic", "-") or "-") == "info|region_aware", "PolicyDiagnostic should summarize effective corridor rule")
    diag_rows = list(getattr(cor, "DiagnosticRows", []) or [])
    _assert(len(diag_rows) == 4, "DiagnosticRows should include four diagnostic categories")
    _assert(any("corridor_diag|kind=policy|state=info" in row for row in diag_rows), "DiagnosticRows should include policy info row")
    _assert(any("corridor_diag|kind=connectivity|state=ok|summary=clean" in row and "sections=" in row for row in diag_rows), "DiagnosticRows should retain connectivity detail counts")
    _assert(any("corridor_diag|kind=packaging|state=info|summary=segmented" in row and "packages=2" in row for row in diag_rows), "DiagnosticRows should retain packaging detail counts")

    App.closeDocument(doc.Name)
    print("[PASS] Region-driven corridor policy smoke test completed.")


if __name__ == "__main__":
    run()
