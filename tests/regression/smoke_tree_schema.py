# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""Parametric Road v1-only project-tree smoke test.

Run with:
    FreeCADCmd -c "exec(open(r'tests/regression/smoke_tree_schema.py', 'r', encoding='utf-8').read())"

Ramp is outside the active product scope and Watertight Solid development is
paused, so this baseline smoke intentionally does not require either subtree.
Compatibility coverage for persisted legacy objects belongs in focused tests.
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    TREE_KEY_PROP,
    V1_TREE_AI_ASSIST,
    V1_TREE_ALIGNMENT_PROFILE,
    V1_TREE_ALIGNMENTS,
    V1_TREE_APPLIED_SECTIONS,
    V1_TREE_ASSEMBLIES,
    V1_TREE_BUILD_PARAMETRIC_OUTPUTS,
    V1_TREE_CORRIDOR_MODEL,
    V1_TREE_DESIGN_TIN,
    V1_TREE_DRAINAGE,
    V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS,
    V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW,
    V1_TREE_EXISTING_GROUND_TIN_RESULT,
    V1_TREE_EXISTING_GROUND_TIN_SOURCE,
    V1_TREE_INTERSECTIONS,
    V1_TREE_OUTPUTS_EXCHANGE,
    V1_TREE_PROFILES,
    V1_TREE_PROJECT_SETUP,
    V1_TREE_QUANTITIES,
    V1_TREE_QUANTITIES_EARTHWORK,
    V1_TREE_REGIONS,
    V1_TREE_REVIEW,
    V1_TREE_SOURCE_DATA,
    V1_TREE_STATIONS,
    V1_TREE_STRUCTURES,
    V1_TREE_SUPERELEVATION,
    V1_TREE_SURFACES,
    CorridorRoadProject,
    ensure_project_tree,
    route_to_v1_tree,
)


def _assert(condition, message):
    if not condition:
        raise Exception(message)


def _group(obj):
    return list(getattr(obj, "Group", []) or [])


def _tree_key(obj):
    return str(getattr(obj, TREE_KEY_PROP, "") or "")


def _tree_folders(project):
    output = []
    seen = set()

    def walk(owner):
        for child in _group(owner):
            name = str(getattr(child, "Name", "") or "")
            if name in seen:
                continue
            seen.add(name)
            if _tree_key(child):
                output.append(child)
                walk(child)

    walk(project)
    return output


def _owners(project, child):
    return [owner for owner in [project] + _tree_folders(project) if child in _group(owner)]


def _add_string_property(obj, name, value):
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyString", name, "Smoke", "v1 tree routing smoke value")
    setattr(obj, name, str(value))


def _route_case(document, project, tree, *, name, expected_key, record_kind=""):
    obj = document.addObject("App::FeaturePython", name)
    if record_kind:
        _add_string_property(obj, "CRRecordKind", record_kind)
    owner = route_to_v1_tree(project, obj)
    _assert(owner == tree[expected_key], f"{name} route mismatch: expected={expected_key}")
    owners = _owners(project, obj)
    _assert(len(owners) == 1, f"{name} must have exactly one tree owner, got={len(owners)}")
    _assert(owners[0] == tree[expected_key], f"{name} owner mismatch after routing")
    return obj


def run():
    document = App.newDocument("CRV1TreeSmoke")
    try:
        project = document.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        project.Label = "Parametric Road Project"
        tree = ensure_project_tree(project, include_references=False)

        required_roots = (
            V1_TREE_PROJECT_SETUP,
            V1_TREE_SOURCE_DATA,
            V1_TREE_ALIGNMENT_PROFILE,
            V1_TREE_SURFACES,
            V1_TREE_CORRIDOR_MODEL,
            V1_TREE_DRAINAGE,
            V1_TREE_STRUCTURES,
            V1_TREE_QUANTITIES_EARTHWORK,
            V1_TREE_REVIEW,
            V1_TREE_OUTPUTS_EXCHANGE,
            V1_TREE_AI_ASSIST,
        )
        for key in required_roots:
            _assert(tree.get(key) is not None, f"Missing v1 root folder: {key}")

        root_labels = [str(getattr(row, "Label", "") or "") for row in _group(project)]
        for retired_label in ("01_Inputs", "02_Alignments", "04_Analysis"):
            _assert(retired_label not in root_labels, f"Retired legacy root was recreated: {retired_label}")

        alignment_children = [str(getattr(row, "Label", "") or "") for row in _group(tree[V1_TREE_ALIGNMENT_PROFILE])]
        _assert(
            alignment_children[:4] == ["Alignments", "Stations", "Profiles", "Superelevation"],
            f"Alignment/Profile subtree order mismatch: {alignment_children[:4]}",
        )

        _route_case(document, project, tree, name="V1AlignmentSmoke", expected_key=V1_TREE_ALIGNMENTS)
        _route_case(document, project, tree, name="V1StationingSmoke", expected_key=V1_TREE_STATIONS)
        _route_case(document, project, tree, name="V1ProfileSmoke", expected_key=V1_TREE_PROFILES)
        _route_case(document, project, tree, name="V1SuperelevationSourceSmoke", expected_key=V1_TREE_SUPERELEVATION)
        _route_case(document, project, tree, name="V1AssemblyModelSmoke", expected_key=V1_TREE_ASSEMBLIES)
        _route_case(document, project, tree, name="V1RegionModelSmoke", expected_key=V1_TREE_REGIONS)
        _route_case(document, project, tree, name="V1AppliedSectionSetSmoke", expected_key=V1_TREE_APPLIED_SECTIONS)
        _route_case(document, project, tree, name="V1CorridorModelSmoke", expected_key=V1_TREE_CORRIDOR_MODEL)
        _route_case(document, project, tree, name="V1SurfaceModelSmoke", expected_key=V1_TREE_DESIGN_TIN)
        _route_case(document, project, tree, name="V1StructureModelSmoke", expected_key=V1_TREE_STRUCTURES)
        _route_case(document, project, tree, name="V1QuantityModelSmoke", expected_key=V1_TREE_QUANTITIES)

        _route_case(
            document,
            project,
            tree,
            name="IntersectionSourceSmoke",
            expected_key=V1_TREE_INTERSECTIONS,
            record_kind="v1_intersection_model",
        )
        _route_case(
            document,
            project,
            tree,
            name="DrainageSourceSmoke",
            expected_key=V1_TREE_DRAINAGE,
            record_kind="v1_drainage_model",
        )
        _route_case(
            document,
            project,
            tree,
            name="TINSourceSmoke",
            expected_key=V1_TREE_EXISTING_GROUND_TIN_SOURCE,
            record_kind="tin_surface_source",
        )
        _route_case(
            document,
            project,
            tree,
            name="TINResultSmoke",
            expected_key=V1_TREE_EXISTING_GROUND_TIN_RESULT,
            record_kind="tin_surface_result",
        )
        _route_case(
            document,
            project,
            tree,
            name="TINPreviewSmoke",
            expected_key=V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW,
            record_kind="tin_mesh_preview",
        )
        _route_case(
            document,
            project,
            tree,
            name="TINDiagnosticsSmoke",
            expected_key=V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS,
            record_kind="tin_diagnostics",
        )
        _route_case(
            document,
            project,
            tree,
            name="CorridorPreviewSmoke",
            expected_key=V1_TREE_BUILD_PARAMETRIC_OUTPUTS,
            record_kind="v1_corridor_surface_preview",
        )

        document.recompute()
        print("[PASS] Parametric Road v1-only project-tree smoke test completed.")
    finally:
        App.closeDocument(document.Name)


if __name__ == "__main__":
    run()
