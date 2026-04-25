import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_AI_ASSIST,
    V1_TREE_AI_CHECKS,
    V1_TREE_AI_GENERATED_ALTERNATIVES,
    V1_TREE_AI_SUGGESTIONS,
    V1_TREE_AI_USER_DECISIONS,
    V1_TREE_ALIGNMENT_PROFILE,
    V1_TREE_ALIGNMENTS,
    V1_TREE_APPLIED_SECTIONS,
    V1_TREE_ASSEMBLIES,
    V1_TREE_BOOKMARKS,
    V1_TREE_CULVERTS,
    V1_TREE_DITCHES,
    V1_TREE_CORRIDOR_MODEL,
    V1_TREE_DRAINAGE,
    V1_TREE_DXF,
    V1_TREE_EXISTING_GROUND_TIN,
    V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS,
    V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW,
    V1_TREE_EXISTING_GROUND_TIN_RESULT,
    V1_TREE_EXISTING_GROUND_TIN_SOURCE,
    V1_TREE_INTERSECTIONS,
    V1_TREE_INLETS,
    V1_TREE_IFC,
    V1_TREE_ISSUES,
    V1_TREE_LANDXML,
    V1_TREE_OUTPUTS_EXCHANGE,
    V1_TREE_EXCHANGE_PACKAGES,
    V1_TREE_PROJECT_SETUP,
    V1_TREE_QUANTITIES_EARTHWORK,
    V1_TREE_RAMPS,
    V1_TREE_REGIONS,
    V1_TREE_REVIEW,
    V1_TREE_REPORTS,
    V1_TREE_SECTION_REVIEW,
    V1_TREE_SHEETS,
    V1_TREE_SOURCE_DATA,
    V1_TREE_STATIONS,
    V1_TREE_STRUCTURES,
    V1_TREE_SURFACES,
    V1_TREE_SURVEY_POINTS,
    V1_TREE_TIN_REVIEW,
    V1_TREE_PLAN_PROFILE_REVIEW,
    V1_TREE_PROFILES,
    CorridorRoadProject,
    ensure_project_tree,
    resolve_v1_target_container,
    route_to_v1_tree,
)


def _new_project_doc():
    doc = App.newDocument("CRV1ProjectTreeContract")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "CorridorRoad Project"
    return doc, project


def test_ensure_project_tree_creates_v1_root_groups() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)

        for key in (
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
        ):
            assert key in tree
            assert tree[key] is not None
    finally:
        App.closeDocument(doc.Name)


def test_ensure_project_tree_uses_v1_only_root_groups() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)

        labels = {str(getattr(obj, "Label", "") or "") for obj in list(getattr(project, "Group", []) or [])}
        assert "01_Inputs" not in labels
        assert "02_Alignments" not in labels
        assert "04_Analysis" not in labels
        assert tree[V1_TREE_SOURCE_DATA].Label == "01_Source Data"
        assert tree[V1_TREE_SURFACES].Label == "03_Surfaces"
    finally:
        App.closeDocument(doc.Name)


def test_ensure_project_tree_creates_tin_source_result_preview_diagnostics_groups() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)

        assert tree[V1_TREE_SURVEY_POINTS].Label == "Survey Points"
        assert tree[V1_TREE_EXISTING_GROUND_TIN].Label == "Existing Ground TIN"
        assert tree[V1_TREE_EXISTING_GROUND_TIN_SOURCE].Label == "Source"
        assert tree[V1_TREE_EXISTING_GROUND_TIN_RESULT].Label == "TIN Result"
        assert tree[V1_TREE_EXISTING_GROUND_TIN_MESH_PREVIEW].Label == "Mesh Preview"
        assert tree[V1_TREE_EXISTING_GROUND_TIN_DIAGNOSTICS].Label == "Diagnostics"
    finally:
        App.closeDocument(doc.Name)


def test_ensure_project_tree_creates_corridor_network_first_class_groups() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)

        assert tree[V1_TREE_RAMPS].Label == "Ramps"
        assert tree[V1_TREE_INTERSECTIONS].Label == "Intersections"
        assert tree[V1_TREE_DRAINAGE].Label == "05_Drainage"
        assert tree[V1_TREE_APPLIED_SECTIONS].Label == "Applied Sections"
    finally:
        App.closeDocument(doc.Name)


def test_resolve_v1_target_container_routes_corridor_network_objects() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        cases = [
            ("RampModel", V1_TREE_RAMPS),
            ("IntersectionModel", V1_TREE_INTERSECTIONS),
            ("AssemblyTemplate", V1_TREE_ASSEMBLIES),
            ("RegionPlan", V1_TREE_REGIONS),
            ("SectionSet", V1_TREE_APPLIED_SECTIONS),
        ]
        for object_name, key in cases:
            obj = doc.addObject("App::FeaturePython", object_name)
            assert resolve_v1_target_container(project, obj) == tree[key]
    finally:
        App.closeDocument(doc.Name)


def test_resolve_v1_target_container_routes_alignment_profile_objects() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        cases = [
            ("V1Alignment", V1_TREE_ALIGNMENTS),
            ("HorizontalAlignment", V1_TREE_ALIGNMENTS),
            ("V1Profile", V1_TREE_PROFILES),
            ("VerticalAlignment", V1_TREE_PROFILES),
            ("ProfileBundle", V1_TREE_PROFILES),
            ("V1Stationing", V1_TREE_STATIONS),
            ("Stationing", V1_TREE_STATIONS),
        ]
        for object_name, key in cases:
            obj = doc.addObject("App::FeaturePython", object_name)
            assert resolve_v1_target_container(project, obj) == tree[key]
    finally:
        App.closeDocument(doc.Name)


def test_resolve_v1_target_container_routes_drainage_objects() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        cases = [
            ("DrainageModel", V1_TREE_DRAINAGE),
            ("DitchModel", V1_TREE_DITCHES),
            ("CulvertModel", V1_TREE_CULVERTS),
            ("InletModel", V1_TREE_INLETS),
        ]
        for object_name, key in cases:
            obj = doc.addObject("App::FeaturePython", object_name)
            assert resolve_v1_target_container(project, obj) == tree[key]
    finally:
        App.closeDocument(doc.Name)


def test_route_to_v1_tree_adds_object_to_preferred_folder() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        ramp = doc.addObject("App::FeaturePython", "RampModel")

        folder = route_to_v1_tree(project, ramp)

        assert folder == tree[V1_TREE_RAMPS]
        assert ramp.Name in _group_names(tree[V1_TREE_RAMPS])
    finally:
        App.closeDocument(doc.Name)


def test_route_to_v1_tree_places_v1_alignment_under_v1_alignments() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        alignment = doc.addObject("App::FeaturePython", "V1Alignment")

        folder = route_to_v1_tree(project, alignment)

        assert folder == tree[V1_TREE_ALIGNMENTS]
        assert alignment.Name in _group_names(tree[V1_TREE_ALIGNMENTS])
        assert "02_Alignments" not in {
            str(getattr(obj, "Label", "") or "")
            for obj in list(getattr(project, "Group", []) or [])
        }
    finally:
        App.closeDocument(doc.Name)


def test_resolve_v1_target_container_routes_review_objects() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        cases = [
            ("PlanProfileReview", V1_TREE_PLAN_PROFILE_REVIEW),
            ("SectionReview", V1_TREE_SECTION_REVIEW),
            ("TINReview", V1_TREE_TIN_REVIEW),
            ("ReviewIssue", V1_TREE_ISSUES),
            ("ReviewBookmark", V1_TREE_BOOKMARKS),
        ]
        for object_name, key in cases:
            obj = doc.addObject("App::FeaturePython", object_name)
            assert resolve_v1_target_container(project, obj) == tree[key]
    finally:
        App.closeDocument(doc.Name)


def test_resolve_v1_target_container_routes_output_exchange_objects() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        cases = [
            ("SheetOutput", V1_TREE_SHEETS),
            ("ReportOutput", V1_TREE_REPORTS),
            ("DXFExport", V1_TREE_DXF),
            ("LandXMLExport", V1_TREE_LANDXML),
            ("IFCExport", V1_TREE_IFC),
            ("ExchangePackage", V1_TREE_EXCHANGE_PACKAGES),
        ]
        for object_name, key in cases:
            obj = doc.addObject("App::FeaturePython", object_name)
            assert resolve_v1_target_container(project, obj) == tree[key]
    finally:
        App.closeDocument(doc.Name)


def test_resolve_v1_target_container_routes_ai_assist_objects() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        cases = [
            ("AISuggestion", V1_TREE_AI_SUGGESTIONS),
            ("AICheck", V1_TREE_AI_CHECKS),
            ("AIGeneratedAlternative", V1_TREE_AI_GENERATED_ALTERNATIVES),
            ("AIUserDecision", V1_TREE_AI_USER_DECISIONS),
        ]
        for object_name, key in cases:
            obj = doc.addObject("App::FeaturePython", object_name)
            assert resolve_v1_target_container(project, obj) == tree[key]
    finally:
        App.closeDocument(doc.Name)


def _group_names(folder) -> set[str]:
    return {str(getattr(obj, "Name", "") or "") for obj in list(getattr(folder, "Group", []) or [])}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] v1 project tree redesign contract tests completed.")
