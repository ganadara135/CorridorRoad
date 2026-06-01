import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    V1_TREE_EXCHANGE_PACKAGES,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.v1.exchange.landxml_import import scan_landxml_file
from freecad.Corridor_Road.v1.objects.obj_landxml_import import create_or_update_v1_landxml_import_object


def test_landxml_import_provenance_object_routes_to_exchange_packages() -> None:
    doc = App.newDocument("CRV1LandXMLImportProvenance")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        tree = ensure_project_tree(project, include_references=False)
        result = scan_landxml_file("tests/samples/landxml_civil3d_alignment_profile_surface.xml")

        obj = create_or_update_v1_landxml_import_object(
            doc,
            project=project,
            result=result,
            created_refs=["Alignment: Main Road CL"],
        )

        assert obj.V1ObjectType == "LandXMLImport"
        assert obj.CRRecordKind == "v1_landxml_import"
        assert obj.SourcePath.endswith("landxml_civil3d_alignment_profile_surface.xml")
        assert obj.SupportedProducer is True
        assert obj.AlignmentCount == 1
        assert obj.ProfileCount == 1
        assert obj.SurfaceCount == 1
        assert obj.CgPointCount == 2
        assert list(obj.CreatedObjectRefs) == ["Alignment: Main Road CL"]
        assert any("landxml_civil3d_source_detected" in row for row in list(obj.DiagnosticRows))
        assert obj.Name in {str(getattr(child, "Name", "") or "") for child in list(tree[V1_TREE_EXCHANGE_PACKAGES].Group)}

        updated = create_or_update_v1_landxml_import_object(
            doc,
            project=project,
            result=result,
            created_refs=["Alignment: Main Road CL", "Profile: FG Main"],
        )
        assert updated is obj
        assert list(updated.CreatedObjectRefs) == ["Alignment: Main Road CL", "Profile: FG Main"]
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] LandXML import provenance object tests completed.")
