from pathlib import Path

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_ALIGNMENTS,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.exchange.landxml_alignment_mapper import (
    alignment_model_from_landxml_candidate,
    create_or_update_alignment_from_landxml_candidate,
)
from freecad.Corridor_Road.v1.exchange.landxml_import import scan_landxml_file
from freecad.Corridor_Road.v1.objects.obj_alignment import to_alignment_model


SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def _new_project_doc():
    doc = App.newDocument("CRV1LandXMLAlignmentMapper")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    project.Label = "Parametric Road Project"
    return doc, project


def test_landxml_alignment_candidate_maps_to_alignment_model() -> None:
    result = scan_landxml_file(SAMPLES / "landxml_civil3d_alignment_profile_surface.xml")

    model = alignment_model_from_landxml_candidate(result.alignments[0], project_id="test-project")

    assert model.project_id == "test-project"
    assert model.alignment_id == "alignment:Main-Road-CL"
    assert model.label == "Main Road CL"
    assert [row.kind for row in model.geometry_sequence] == ["tangent", "circular_curve"]
    assert model.geometry_sequence[0].station_start == 0.0
    assert model.geometry_sequence[0].station_end == 50.0
    assert model.geometry_sequence[1].station_start == 50.0
    assert model.geometry_sequence[1].station_end == 70.0


def test_create_or_update_alignment_from_landxml_candidate_routes_to_v1_tree() -> None:
    doc, project = _new_project_doc()
    try:
        tree = ensure_project_tree(project, include_references=False)
        result = scan_landxml_file(SAMPLES / "landxml_civil3d_alignment_profile_surface.xml")

        obj = create_or_update_alignment_from_landxml_candidate(doc, result.alignments[0], project=project)

        assert obj.AlignmentId == "alignment:Main-Road-CL"
        assert obj.Label == "Main Road CL"
        assert list(obj.ElementKinds) == ["tangent", "circular_curve"]
        assert list(obj.StationStarts) == [0.0, 50.0]
        assert list(obj.StationEnds) == [50.0, 70.0]
        assert obj.Name in {str(getattr(child, "Name", "") or "") for child in list(tree[V1_TREE_ALIGNMENTS].Group)}
        model = to_alignment_model(obj)
        assert model is not None
        assert model.alignment_id == "alignment:Main-Road-CL"

        updated = create_or_update_alignment_from_landxml_candidate(doc, result.alignments[0], project=project)
        assert updated is obj
        assert len([o for o in doc.Objects if str(getattr(o, "AlignmentId", "") or "") == "alignment:Main-Road-CL"]) == 1
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] LandXML alignment mapper tests completed.")
