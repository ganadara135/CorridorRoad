# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
v1 workflow smoke test: one document through the main v1 path.

Project -> Alignment -> Stations -> Profile -> Assembly -> Region -> Applied Sections ->
Build Parametric, then save, reopen and rebuild. It checks that every stage leaves its result
in its project tree folder, that the corridor surfaces have geometry, that a saved document
reopens with the same objects, folders and surfaces, and that rebuilding the reopened document
reproduces the same surfaces.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_v1_workflow.py
"""

import os
import tempfile

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_ALIGNMENTS,
    V1_TREE_APPLIED_SECTIONS,
    V1_TREE_ASSEMBLIES,
    V1_TREE_BUILD_PARAMETRIC_OUTPUTS,
    V1_TREE_CORRIDOR_MODEL,
    V1_TREE_DESIGN_TIN,
    V1_TREE_PROFILES,
    V1_TREE_REGIONS,
    V1_TREE_STATIONS,
    TREE_KEY_PROP,
)
from freecad.Corridor_Road.v1.commands.cmd_build_corridor import apply_v1_corridor_model
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    apply_v1_applied_section_set,
    build_document_applied_section_set,
)
from freecad.Corridor_Road.v1.commands.cmd_project_setup import create_corridorroad_project
from freecad.Corridor_Road.v1.commands.cmd_region_editor import apply_v1_region_model, region_preset_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import (
    apply_v1_assembly_subassembly_model,
    assembly_subassembly_preset_model_from_document,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing

# Each stage's result and the project tree folder it belongs in.
EXPECTED_FOLDERS = {
    "V1Alignment": V1_TREE_ALIGNMENTS,
    "V1Profile": V1_TREE_PROFILES,
    "V1Stationing": V1_TREE_STATIONS,
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


def _check_tree(doc, stage):
    owner = _folders(doc)
    for name, key in EXPECTED_FOLDERS.items():
        _assert(doc.getObject(name) is not None, f"{stage}: {name} was not created")
        _assert(owner.get(name) == key, f"{stage}: {name} is in {owner.get(name)!r}, expected {key!r}")
    project = doc.getObject("CorridorRoadProject")
    loose = [o.Name for o in project.Group if not str(getattr(o, TREE_KEY_PROP, "") or "")]
    _assert(not loose, f"{stage}: objects left at the project root: {loose}")


def _build(doc, project):
    alignment = create_sample_v1_alignment(doc, project=project)
    create_sample_v1_profile(doc, project=project, alignment=alignment)
    create_v1_stationing(doc, project=project, alignment=alignment, interval=20.0)
    apply_v1_assembly_subassembly_model(
        document=doc,
        project=project,
        assembly_model=assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
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

        doc.saveAs(path)
        App.closeDocument(doc.Name)
        doc = None

        reopened = App.openDocument(path)
        _check_tree(reopened, "reopen")
        _assert(_facets(reopened) == facets, f"Reopened surfaces differ: {_facets(reopened)} != {facets}")

        apply_v1_corridor_model(document=reopened, project=reopened.getObject("CorridorRoadProject"))
        _check_tree(reopened, "rebuild")
        _assert(_facets(reopened) == facets, f"Rebuilt surfaces differ: {_facets(reopened)} != {facets}")

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
