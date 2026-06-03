import FreeCAD as App
from pathlib import Path

from freecad.Corridor_Road.init_gui import corridorroad_workflow_command_groups
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject
from freecad.Corridor_Road.objects.obj_project import V1_TREE_EXCHANGE_PACKAGES, ensure_project_tree
from freecad.Corridor_Road.v1.commands.cmd_landxml_import import (
    CmdV1ImportLandXML,
    LANDXML_IMPORT_COMMAND_ID,
    NEXT_WORKFLOW_TEXT,
    import_landxml_file_into_document,
    landxml_preset_names,
    landxml_preset_path,
)
from freecad.Corridor_Road.v1.exchange.landxml_import import scan_landxml_file


def test_landxml_import_command_resources_are_civil3d_specific() -> None:
    resources = CmdV1ImportLandXML().GetResources()

    assert resources["MenuText"] == "Import LandXML"
    assert "Civil 3D" in resources["ToolTip"]
    assert str(resources["Pixmap"]).replace("\\", "/").endswith("landxml_import.svg")


def test_landxml_import_next_workflow_text_stops_at_build_sections() -> None:
    assert NEXT_WORKFLOW_TEXT.startswith("Next workflow: LandXML Import -> Stations")
    assert "Build Sections" in NEXT_WORKFLOW_TEXT
    assert "Build Parametric" not in NEXT_WORKFLOW_TEXT
    assert "Watertight" not in NEXT_WORKFLOW_TEXT


def test_landxml_import_command_is_in_outputs_exchange_group() -> None:
    groups = corridorroad_workflow_command_groups()

    assert LANDXML_IMPORT_COMMAND_ID in groups["output"]
    assert groups["output"].index("CorridorRoad_OutputsExchange") < groups["output"].index(LANDXML_IMPORT_COMMAND_ID)


def test_landxml_import_civil3d_preset_file_is_scannable() -> None:
    names = landxml_preset_names()
    path = landxml_preset_path("Civil 3D Starter Road")

    assert "Civil 3D Starter Road" in names
    assert Path(path).exists()
    result = scan_landxml_file(path)
    assert result.summary.supported_producer is True
    assert result.summary.alignment_count == 1
    assert result.summary.profile_count == 1
    assert result.summary.surface_count == 1
    assert result.summary.cgpoint_count == 14
    assert len(result.alignments[0].elements) == 7
    assert len(result.profiles[0].points) == 9
    assert len(result.surfaces[0].points) == 48
    assert len(result.surfaces[0].faces) == 70


def test_landxml_import_function_imports_sample_file() -> None:
    doc = App.newDocument("CRV1LandXMLImportCommand")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        tree = ensure_project_tree(project, include_references=False)
        created = import_landxml_file_into_document(
            "tests/samples/landxml_civil3d_alignment_profile_surface.xml",
            doc,
            project=project,
        )

        assert created is not None
        assert any(str(getattr(obj, "AlignmentId", "") or "") == "alignment:Main-Road-CL" for obj in doc.Objects)
        assert any(str(getattr(obj, "ProfileId", "") or "") == "profile:FG-Main" for obj in doc.Objects)
        assert any(str(getattr(obj, "SurfaceModelId", "") or "") == "surface-model:tin:Existing-Ground" for obj in doc.Objects)
        provenance = [obj for obj in doc.Objects if str(getattr(obj, "CRRecordKind", "") or "") == "v1_landxml_import"]
        assert len(provenance) == 1
        assert provenance[0].DetectedProducer.startswith("Autodesk Civil 3D")
        assert provenance[0].SupportedProducer is True
        assert provenance[0].AlignmentCount == 1
        assert provenance[0].ProfileCount == 1
        assert provenance[0].SurfaceCount == 1
        assert provenance[0].Name in {str(getattr(child, "Name", "") or "") for child in list(tree[V1_TREE_EXCHANGE_PACKAGES].Group)}
    finally:
        App.closeDocument(doc.Name)


def test_landxml_import_function_blocks_unsupported_producer() -> None:
    doc = App.newDocument("CRV1LandXMLImportUnsupported")
    try:
        project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(project)
        result = scan_landxml_file("tests/samples/landxml_unknown_producer.xml")

        assert result is not None
        assert result.summary.supported_producer is False
        try:
            import_landxml_file_into_document("tests/samples/landxml_unknown_producer.xml", doc, project=project)
        except ValueError as exc:
            assert "Only Autodesk Civil 3D LandXML" in str(exc)
        else:
            raise AssertionError("Unsupported LandXML producer should be blocked.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] LandXML import command tests completed.")
