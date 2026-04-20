# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Surface and corridor panel unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_surface_panels_unit_policy.py
"""

import FreeCAD as App
from types import SimpleNamespace

from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_corridor_loft import CorridorTaskPanel
from freecad.Corridor_Road.ui.task_cut_fill_calc import CutFillCalcTaskPanel
from freecad.Corridor_Road.ui.task_design_terrain import DesignTerrainTaskPanel
from freecad.Corridor_Road.ui.task_pointcloud_dem import PointCloudDEMTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRSurfacePanelUnits")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"

        dem_panel = PointCloudDEMTaskPanel()
        _assert(dem_panel.spin_cell.suffix().strip() == "mm", "PointCloud DEM cell suffix should show millimeters")
        _assert(abs(float(dem_panel.spin_cell.value()) - 4000.0) < 1.0e-6, "PointCloud DEM default cell should display as 4000 mm")
        _assert("World origin (E/N):" in str(dem_panel.lbl_coord_hint.text() or ""), "Coordinate hint should use expanded world-origin wording")
        _assert("Local origin (X/Y):" in str(dem_panel.lbl_coord_hint.text() or ""), "Coordinate hint should use expanded local-origin wording")

        terrain_panel = DesignTerrainTaskPanel()
        _assert(terrain_panel.spin_cell.suffix().strip() == "mm", "Design Terrain cell suffix should show millimeters")
        _assert(abs(float(terrain_panel.spin_cell.value()) - 1000.0) < 1.0e-6, "Design Terrain default cell should display as 1000 mm")
        _assert(terrain_panel.spin_margin.suffix().strip() == "mm", "Design Terrain margin suffix should show millimeters")

        cutfill_panel = CutFillCalcTaskPanel()
        _assert(cutfill_panel.spin_cell.suffix().strip() == "mm", "Cut/Fill cell suffix should show millimeters")
        _assert(abs(float(cutfill_panel.spin_cell.value()) - 1000.0) < 1.0e-6, "Cut/Fill default cell should display as 1000 mm")
        _assert(abs(float(cutfill_panel.spin_margin.value()) - 5000.0) < 1.0e-6, "Cut/Fill default margin should display as 5000 mm")
        _assert(abs(float(cutfill_panel.spin_deadband.value()) - 20.0) < 1.0e-6, "Cut/Fill deadband should display as 20 mm")
        _assert(abs(float(cutfill_panel.spin_clamp.value()) - 2000.0) < 1.0e-6, "Cut/Fill clamp should display as 2000 mm")
        _assert(abs(float(cutfill_panel.spin_zoff.value()) - 50.0) < 1.0e-6, "Cut/Fill visual offset should display as 50 mm")
        _assert(cutfill_panel.spin_xmin.suffix().strip() == "mm", "Cut/Fill manual domain inputs should show millimeters")

        corridor_panel = CorridorTaskPanel()
        _assert(corridor_panel.spin_min_spacing.suffix().strip() == "mm", "Corridor min spacing suffix should show millimeters")
        _assert(abs(float(corridor_panel.spin_min_spacing.value()) - 500.0) < 1.0e-6, "Corridor min spacing should display as 500 mm")

        dem_message = dem_panel._build_completion_message(
            SimpleNamespace(
                Status="OK",
                CsvPath="sample.csv",
                InputCoords="World",
                OutputCoords="Local",
                CellSize=4.0,
                Aggregation="Mean",
                PointCountUsed=12,
                PointCountRaw=14,
                SkippedRows=2,
                GridNX=3,
                GridNY=4,
                NoDataCount=1,
                ZMin=1.0,
                ZMax=2.5,
            )
        )
        _assert("Display unit: mm" in dem_message, "PointCloud DEM completion message should report display unit")
        _assert("CellSize: 4000.000 mm" in dem_message, "PointCloud DEM completion message should format cell size in display unit")
        _assert("Z range: 1000.000 mm .. 2500.000 mm" in dem_message, "PointCloud DEM completion message should format Z range in display unit")

        cutfill_message = cutfill_panel._build_completion_message(
            SimpleNamespace(
                Status="Done",
                CutVolume=1000000000.0,
                FillVolume=2000000000.0,
                DeltaMin=0.1,
                DeltaMax=0.25,
                DeltaMean=0.15,
                ValidCount=20,
                SampleCount=24,
                NoDataArea=3000000.0,
                NoDataRatio=0.125,
                CellSize=0.5,
                DomainCoords="Local",
                ExistingSurfaceCoords="World",
                MaxTrianglesPerSource=3000,
                MaxCandidateTriangles=4000,
                MaxTriangleChecks=5000,
                SignConvention="delta=Design-Existing, +Fill/-Cut",
                ShowDeltaMap=True,
                DeltaDeadband=0.02,
                DeltaClamp=2.0,
            )
        )
        _assert("Display unit: mm" in cutfill_message, "Cut/Fill completion message should report display unit")
        _assert("CellSize: 500.000 mm" in cutfill_message, "Cut/Fill completion message should format cell size in display unit")
        _assert("Delta(min/max/mean): 100.000 mm / 250.000 mm / 150.000 mm" in cutfill_message, "Cut/Fill completion message should format delta values in display unit")

        corridor_message = corridor_panel._build_completion_message(
            SimpleNamespace(
                TypicalSectionAdvancedComponentCount=1,
                PavementLayerCount=2,
                EnabledPavementLayerCount=1,
                PavementTotalThickness=0.25,
                PointCountPerSection=8,
                ResolvedRuledMode="off",
                StructureSegmentCount=0,
                CorridorSegmentCount=2,
                SegmentPackageCount=1,
                SegmentObjectCount=1,
                SkippedSegmentCount=0,
                SegmentKindSummary="surface",
                SegmentSourceSummary="typical_section",
                SegmentDriverSourceSummary="section_strip",
                SegmentDriverModeSummary="adaptive",
                SegmentProfileContractSummary="ok",
                SegmentPackageSummary="1 package",
                SegmentDisplaySummary="mesh",
                ProfileContractSource="section_strip",
                DiagnosticSummary="ok",
                DiagnosticClassSummary="ok",
                SourceDiagnostic="ok|section_set",
                ConnectivityDiagnostic="ok|connected",
                PackagingDiagnostic="ok|packaged",
                PolicyDiagnostic="ok|none",
                SkippedStationRanges=[],
                ResolvedStructureCorridorModeSummary="-",
                ResolvedRegionCorridorModeSummary="-",
                ResolvedCombinedCorridorModeSummary="-",
                ResolvedStructureCorridorWarnings=[],
                ResolvedRegionCorridorWarnings=[],
                ResolvedCombinedCorridorWarnings=[],
                ResolvedSkipBoundaryBehavior="-",
                ResolvedSkipBoundaryStates=[],
                SegmentSummaryRows=["segment-1"],
                ResolvedStructureNotchCount=0,
                ResolvedNotchStationCount=0,
                ResolvedNotchSchemaName="-",
                ResolvedNotchProfileSummary="-",
                ResolvedNotchBuildMode="-",
                ResolvedNotchCutterCount=0,
                ClosedProfileSchemaVersion=1,
                SkipMarkerCount=0,
                Status="OK",
            ),
            SimpleNamespace(
                StationValues=[0.0, 20.0],
                SectionSchemaVersion=2,
                TopProfileSource="typical_section",
                TopProfileEdgeSummary="berm/berm",
            ),
        )
        _assert("Display unit: mm" in corridor_message, "Corridor completion message should report display unit")
        _assert("Pavement total thickness: 250.000 mm" in corridor_message, "Corridor completion message should format pavement thickness in display unit")
        _assert("Sections used: 2" in corridor_message, "Corridor completion message should report section count")

        print("[PASS] Surface and corridor panel unit-policy smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
