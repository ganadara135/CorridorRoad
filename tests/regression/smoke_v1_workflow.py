# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
v1 workflow smoke test: one document through the main v1 path.

Project -> existing ground terrain -> Alignment -> Profile -> Superelevation -> Stations ->
3D Centerline -> Assembly -> Region -> Applied Sections -> Build Parametric, then save, reopen
and rebuild. It checks that every stage leaves its result in its project tree folder, that the
side slopes daylight on the terrain and the lanes take the superelevation in the curve, that the
corridor surfaces have geometry and are manifold meshes without zero-area or downward-facing
facets, that a saved document reopens with the same objects, folders, surfaces and current
results, that rebuilding the reopened document reproduces the same surfaces, and that a Profile
edit makes the downstream results stale until Rebuild Downstream makes them current again.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_v1_workflow.py
"""

import os
import tempfile

import FreeCAD as App
import Mesh

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_ALIGNMENTS,
    V1_TREE_APPLIED_SECTIONS,
    V1_TREE_ASSEMBLIES,
    V1_TREE_BUILD_PARAMETRIC_OUTPUTS,
    V1_TREE_CENTERLINE3D,
    V1_TREE_CORRIDOR_MODEL,
    V1_TREE_DESIGN_TIN,
    V1_TREE_PROFILES,
    V1_TREE_REGIONS,
    V1_TREE_STATIONS,
    V1_TREE_SUPERELEVATION,
    TREE_KEY_PROP,
)
from freecad.Corridor_Road.v1.commands.cmd_alignment_editor import apply_alignment_ip_rows
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import apply_v1_corridor_model
from freecad.Corridor_Road.v1.commands.cmd_centerline3d import show_v1_centerline3d_preview_object
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_project_setup import create_corridorroad_project
from freecad.Corridor_Road.v1.commands.cmd_rebuild_downstream import rebuild_downstream
from freecad.Corridor_Road.v1.commands.cmd_superelevation_editor import (
    _auto_calculation_request_from_document,
    apply_v1_superelevation_model,
)
from freecad.Corridor_Road.v1.commands.cmd_region_editor import apply_v1_region_model, region_preset_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import (
    apply_v1_assembly_subassembly_model,
    assembly_subassembly_preset_model_from_document,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set
from freecad.Corridor_Road.v1.objects.obj_profile import find_v1_profile
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing
from freecad.Corridor_Road.v1.objects.result_freshness import document_result_freshness
from freecad.Corridor_Road.v1.services.evaluation.superelevation_auto_calculation_service import (
    SuperelevationAutoCalculationService,
)

# Each stage's result and the project tree folder it belongs in.
EXPECTED_FOLDERS = {
    "V1Alignment": V1_TREE_ALIGNMENTS,
    "V1Profile": V1_TREE_PROFILES,
    "V1Stationing": V1_TREE_STATIONS,
    "V1SuperelevationSource": V1_TREE_SUPERELEVATION,
    "V1Centerline3DPreview": V1_TREE_CENTERLINE3D,
    "V1AssemblySubassemblyModel": V1_TREE_ASSEMBLIES,
    "V1RegionModel": V1_TREE_REGIONS,
    "V1AppliedSectionSet": V1_TREE_APPLIED_SECTIONS,
    "V1CorridorModel": V1_TREE_CORRIDOR_MODEL,
    "V1SurfaceModel": V1_TREE_DESIGN_TIN,
    "V1CorridorCenterline3DPreview": V1_TREE_BUILD_PARAMETRIC_OUTPUTS,
    "V1CorridorDesignSurfacePreview": V1_TREE_BUILD_PARAMETRIC_OUTPUTS,
    "V1CorridorSubgradeSurfacePreview": V1_TREE_BUILD_PARAMETRIC_OUTPUTS,
    "V1CorridorDaylightSurfacePreview": V1_TREE_BUILD_PARAMETRIC_OUTPUTS,
}
SURFACES = ("V1CorridorDesignSurfacePreview", "V1CorridorSubgradeSurfacePreview", "V1CorridorDaylightSurfacePreview")


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _folders(doc):
    """Object name -> tree key of the folder holding it."""

    owner = {}
    for folder in doc.Objects:
        key = str(getattr(folder, TREE_KEY_PROP, "") or "")
        if not key:
            continue
        for child in list(getattr(folder, "Group", []) or []):
            if not str(getattr(child, TREE_KEY_PROP, "") or ""):
                owner[child.Name] = key
    return owner


def _facets(doc):
    return {name: int(doc.getObject(name).Mesh.CountFacets) for name in SURFACES}


def _check_mesh_quality(doc, stage):
    # a zero-area facet makes FreeCAD's mesh non-manifold, and it reports the document as
    # defective when it opens again
    for name in SURFACES:
        mesh = doc.getObject(name).Mesh
        _assert(not mesh.hasNonManifolds(), f"{stage}: {name} is not manifold")
        degenerate = [facet for facet in mesh.Topology[1] if len(set(facet)) < 3]
        _assert(not degenerate, f"{stage}: {name} has {len(degenerate)} zero-area facets")
        # corridor surfaces wind counterclockwise in plan; a vertical face (a curb) has no up side
        downward = [facet for facet in mesh.Facets if facet.Normal.z < -1.0e-6]
        _assert(not downward, f"{stage}: {name} has {len(downward)} facets facing down")


def _check_tree(doc, stage):
    owner = _folders(doc)
    for name, key in EXPECTED_FOLDERS.items():
        _assert(doc.getObject(name) is not None, f"{stage}: {name} was not created")
        _assert(owner.get(name) == key, f"{stage}: {name} is in {owner.get(name)!r}, expected {key!r}")
    project = doc.getObject("CorridorRoadProject")
    loose = [o.Name for o in project.Group if not str(getattr(o, TREE_KEY_PROP, "") or "")]
    _assert(not loose, f"{stage}: objects left at the project root: {loose}")


def _add_existing_ground(doc, project):
    """A flat existing ground 3 m below the lowest road elevation, wider than the corridor."""

    x0, x1, y0, y1, z = -40.0, 220.0, -80.0, 100.0, 9.0
    mesh = Mesh.Mesh()
    mesh.addFacet(App.Vector(x0, y0, z), App.Vector(x1, y0, z), App.Vector(x1, y1, z))
    mesh.addFacet(App.Vector(x0, y0, z), App.Vector(x1, y1, z), App.Vector(x0, y1, z))
    terrain = doc.addObject("Mesh::Feature", "ExistingGround")
    terrain.Label = "Existing Ground"
    terrain.Mesh = mesh
    project.Terrain = terrain


def _build(doc, project):
    _add_existing_ground(doc, project)
    alignment = create_sample_v1_alignment(doc, project=project)
    # a curve as the Alignment editor builds it: R 120 m with 20 m transitions, 174.9 m long, inside
    # the sample Profile's 0-180 m
    apply_alignment_ip_rows(
        alignment,
        [
            {"x": 0.0, "y": 0.0, "radius": 0.0, "transition_length": 0.0},
            {"x": 90.0, "y": 0.0, "radius": 120.0, "transition_length": 20.0},
            {"x": 170.0, "y": 30.0, "radius": 0.0, "transition_length": 0.0},
        ],
        use_transition_curves=True,
        spiral_segments=16,
        min_radius=20.0,
        min_tangent_length=10.0,
        min_transition_length=5.0,
    )
    create_sample_v1_profile(doc, project=project, alignment=alignment)
    # Superelevation from the Alignment's design speed, as Auto Calculate in its panel
    superelevation = SuperelevationAutoCalculationService().calculate(_auto_calculation_request_from_document(doc, alignment))
    apply_v1_superelevation_model(document=doc, project=project, superelevation_model=superelevation.superelevation_model)
    create_v1_stationing(doc, project=project, alignment=alignment, interval=20.0)
    show_v1_centerline3d_preview_object(doc, project=project)
    # Full Set Road side slopes daylight on the terrain with cut and fill slopes
    apply_v1_assembly_subassembly_model(
        document=doc,
        project=project,
        assembly_model=assembly_subassembly_preset_model_from_document("Full Set Road", doc, project=project, alignment=alignment),
    )
    apply_v1_region_model(
        document=doc,
        project=project,
        region_model=region_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
    )
    applied = build_document_applied_section_set(doc, project=project)
    _assert(len(applied.sections) >= 10, f"Applied Sections built only {len(applied.sections)} sections")
    apply_v1_applied_section_set(document=doc, project=project, applied_section_set=applied)
    apply_v1_corridor_model(document=doc, project=project)


def _check_terrain_and_superelevation(doc, stage):
    sections = to_applied_section_set(find_v1_applied_section_set(doc)).sections
    daylight = doc.getObject("V1CorridorDaylightSurfacePreview")
    hits = int(daylight.AppliedSectionDaylightTerrainHitCount)
    fallbacks = int(daylight.AppliedSectionDaylightFallbackCount)
    _assert(hits >= 2 * len(sections), f"{stage}: {hits} terrain daylight hits for {len(sections)} sections")
    _assert(fallbacks == 0, f"{stage}: {fallbacks} side slopes fell back instead of reaching the terrain")
    lane_slopes = [abs(float(row.slope)) for section in sections for row in section.subassembly_rows if row.kind == "lane"]
    _assert(max(lane_slopes) > 0.05, f"{stage}: the lanes never take the superelevation, steepest {max(lane_slopes):.3f}")


def _freshness(doc) -> dict[str, tuple[str, tuple[str, ...]]]:
    return {row.stage: (row.status, row.changed_inputs) for row in document_result_freshness(doc)}


def _check_current(doc, stage):
    stale = {name: value for name, value in _freshness(doc).items() if value[0] != "current"}
    _assert(not stale, f"{stage}: results are not current: {stale}")


def _check_stale_and_rebuild(doc):
    profile = find_v1_profile(doc)
    elevations = list(profile.ControlElevations)
    elevations[1] += 1.5
    profile.ControlElevations = elevations
    key = f"profile@{profile.AlignmentId}"
    freshness = _freshness(doc)
    _assert(freshness["stationing"][0] == "current", f"profile edit: Stations went stale: {freshness}")
    for name in ("centerline3d", "applied_sections", "build_parametric"):
        _assert(freshness[name] == ("stale", (key,)), f"profile edit: {name} is {freshness[name]}, expected stale on {key}")
    report = rebuild_downstream(doc)
    _assert(not report.failed, f"Rebuild Downstream failed:\n{report.text}")
    _assert(
        report.rebuilt_stages == ("centerline3d", "applied_sections", "build_parametric"),
        f"Rebuild Downstream rebuilt {report.rebuilt_stages}",
    )
    _check_current(doc, "rebuild downstream")


def run():
    doc = App.newDocument("CRV1WorkflowSmoke")
    reopened = None
    folder = tempfile.mkdtemp(prefix="cr_v1_workflow_")
    path = os.path.join(folder, "v1_workflow.FCStd")
    try:
        project = create_corridorroad_project(doc)
        _build(doc, project)
        _check_tree(doc, "build")
        facets = _facets(doc)
        _assert(all(count > 0 for count in facets.values()), f"Corridor surfaces without geometry: {facets}")
        _check_mesh_quality(doc, "build")
        _check_terrain_and_superelevation(doc, "build")
        _check_current(doc, "build")

        doc.saveAs(path)
        App.closeDocument(doc.Name)
        doc = None

        reopened = App.openDocument(path)
        _check_tree(reopened, "reopen")
        _assert(_facets(reopened) == facets, f"Reopened surfaces differ: {_facets(reopened)} != {facets}")
        _check_mesh_quality(reopened, "reopen")
        _check_current(reopened, "reopen")

        apply_v1_corridor_model(document=reopened, project=reopened.getObject("CorridorRoadProject"))
        _check_tree(reopened, "rebuild")
        _assert(_facets(reopened) == facets, f"Rebuilt surfaces differ: {_facets(reopened)} != {facets}")
        _check_current(reopened, "rebuild")

        _check_stale_and_rebuild(reopened)
        _check_tree(reopened, "rebuild downstream")
        _check_mesh_quality(reopened, "rebuild downstream")
        _check_terrain_and_superelevation(reopened, "rebuild downstream")

        print(f"[PASS] v1 workflow smoke test completed: {facets}")
    finally:
        for document in (doc, reopened):
            if document is not None:
                try:
                    App.closeDocument(document.Name)
                except Exception:
                    pass
        try:
            os.remove(path)
            os.rmdir(folder)
        except OSError:
            pass


if __name__ == "__main__":
    run()
