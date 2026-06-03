from pathlib import Path

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_PROFILES,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.exchange.landxml_alignment_mapper import (
    create_or_update_alignment_from_landxml_candidate,
)
from freecad.Corridor_Road.v1.exchange.landxml_import import scan_landxml_file
from freecad.Corridor_Road.v1.exchange.landxml_profile_mapper import (
    create_or_update_profile_from_landxml_candidate,
    profile_model_from_landxml_candidate,
)
from freecad.Corridor_Road.v1.objects.obj_profile import to_profile_model


SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def _new_project_doc():
    doc = App.newDocument("CRV1LandXMLProfileMapper")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "Parametric Road Project"
    return doc, project


def test_landxml_profile_candidate_maps_to_profile_model() -> None:
    result = scan_landxml_file(SAMPLES / "landxml_civil3d_alignment_profile_surface.xml")

    model = profile_model_from_landxml_candidate(result.profiles[0], project_id="test-project")

    assert model.project_id == "test-project"
    assert model.profile_id == "profile:FG-Main"
    assert model.alignment_id == "alignment:Main-Road-CL"
    assert model.label == "FG Main"
    assert [row.station for row in model.control_rows] == [0.0, 50.0, 70.0]
    assert [row.elevation for row in model.control_rows] == [10.0, 11.0, 10.5]


def test_create_or_update_profile_from_landxml_candidate_routes_to_v1_tree() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        result = scan_landxml_file(SAMPLES / "landxml_civil3d_alignment_profile_surface.xml")
        alignment = create_or_update_alignment_from_landxml_candidate(doc, result.alignments[0], project=project)

        profile = create_or_update_profile_from_landxml_candidate(doc, result.profiles[0], project=project)

        assert profile.ProfileId == "profile:FG-Main"
        assert profile.AlignmentId == alignment.AlignmentId
        assert profile.Label == "FG Main"
        assert list(profile.ControlStations) == [0.0, 50.0, 70.0]
        assert list(profile.ControlElevations) == [10.0, 11.0, 10.5]
        assert profile.Name in {str(getattr(child, "Name", "") or "") for child in list(tree[V1_TREE_PROFILES].Group)}
        model = to_profile_model(profile)
        assert model is not None
        assert model.profile_id == "profile:FG-Main"
        assert model.alignment_id == "alignment:Main-Road-CL"

        updated = create_or_update_profile_from_landxml_candidate(doc, result.profiles[0], project=project)
        assert updated is profile
        assert len([o for o in doc.Objects if str(getattr(o, "ProfileId", "") or "") == "profile:FG-Main"]) == 1
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] LandXML profile mapper tests completed.")
