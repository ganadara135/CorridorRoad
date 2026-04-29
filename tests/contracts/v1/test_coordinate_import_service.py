import csv
from pathlib import Path

import FreeCAD as App

from freecad.Corridor_Road.objects.csv_alignment_import import read_alignment_csv, write_alignment_csv
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_properties
from freecad.Corridor_Road.v1.services.builders import TINBuildService
from freecad.Corridor_Road.v1.services.coordinates import (
    alignment_rows_from_local,
    alignment_rows_to_local,
    import_point_to_local,
    resolve_coordinate_export_policy,
    resolve_coordinate_import_policy,
)


def _world_first_project_doc():
    doc = App.newDocument("CRV1CoordinateImportContract")
    project = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(project)
    ensure_project_properties(project)
    project.CoordinateWorkflow = "World-first"
    project.CRSEPSG = "EPSG:5186"
    project.ProjectOriginE = 1000.0
    project.ProjectOriginN = 2000.0
    project.ProjectOriginZ = 10.0
    project.LocalOriginX = 0.0
    project.LocalOriginY = 0.0
    project.LocalOriginZ = 0.0
    project.NorthRotationDeg = 0.0
    return doc, project


def test_world_first_policy_converts_external_csv_points_to_local_model_coordinates() -> None:
    doc, project = _world_first_project_doc()
    try:
        policy = resolve_coordinate_import_policy(project)
        x, y, z = import_point_to_local(project, 1015.0, 2025.0, 13.0)

        assert policy.input_coords == "World"
        assert policy.model_coords == "Local"
        assert (round(x, 6), round(y, 6), round(z, 6)) == (15.0, 25.0, 3.0)
    finally:
        App.closeDocument(doc.Name)


def test_alignment_csv_rows_follow_same_world_first_import_and_export_policy() -> None:
    doc, project = _world_first_project_doc()
    try:
        local_rows, import_policy = alignment_rows_to_local(
            project,
            [(1000.0, 2000.0, 0.0, 0.0), (1010.0, 2020.0, 50.0, 5.0)],
        )
        world_rows, export_policy = alignment_rows_from_local(project, local_rows)

        assert import_policy.input_coords == "World"
        assert local_rows == [(0.0, 0.0, 0.0, 0.0), (10.0, 20.0, 50.0, 5.0)]
        assert export_policy.input_coords == "World"
        assert world_rows == [(1000.0, 2000.0, 0.0, 0.0), (1010.0, 2020.0, 50.0, 5.0)]
    finally:
        App.closeDocument(doc.Name)


def test_alignment_export_policy_can_force_local_or_world_independent_of_project_default() -> None:
    doc, project = _world_first_project_doc()
    try:
        project_default = resolve_coordinate_export_policy(project, output_coords="project")
        forced_local_rows, forced_local = alignment_rows_from_local(
            project,
            [(10.0, 20.0, 50.0, 5.0)],
            output_coords="local",
        )
        forced_world_rows, forced_world = alignment_rows_from_local(
            project,
            [(10.0, 20.0, 50.0, 5.0)],
            output_coords="world",
        )

        assert project_default.output_coords == "World"
        assert forced_local.output_coords == "Local"
        assert forced_local_rows == [(10.0, 20.0, 50.0, 5.0)]
        assert forced_world.output_coords == "World"
        assert forced_world_rows == [(1010.0, 2020.0, 50.0, 5.0)]
    finally:
        App.closeDocument(doc.Name)


def test_alignment_csv_export_writes_coordinate_metadata_that_import_can_read(tmp_path=None) -> None:
    doc, project = _world_first_project_doc()
    csv_path = Path(str(tmp_path or Path.cwd())) / "alignment_world_export_metadata.csv"
    try:
        rows, export_policy = alignment_rows_from_local(
            project,
            [(10.0, 20.0, 50.0, 5.0), (20.0, 30.0, 0.0, 0.0)],
            output_coords="world",
        )
        write_alignment_csv(
            str(csv_path),
            rows,
            x_header="E",
            y_header="N",
            doc_or_project=project,
            coordinate_metadata=export_policy.metadata(),
        )

        loaded = read_alignment_csv(str(csv_path), doc_or_project=project)
        metadata = dict(loaded.get("metadata", {}) or {})
        rows_local, import_policy = alignment_rows_to_local(
            project,
            loaded["rows"],
            input_coords=str(metadata.get("coordinate_input", "") or "auto"),
        )

        assert metadata["coordinate_input"] == "World"
        assert metadata["coordinate_model"] == "Local"
        assert metadata["coordinate_workflow"] == "World-first"
        assert metadata["crs_epsg"] == "EPSG:5186"
        assert import_policy.input_coords == "World"
        assert rows_local == [(10.0, 20.0, 50.0, 5.0), (20.0, 30.0, 0.0, 0.0)]
    finally:
        try:
            csv_path.unlink()
        except Exception:
            pass
        App.closeDocument(doc.Name)


def test_tin_csv_build_stores_local_vertices_and_coordinate_metadata(tmp_path=None) -> None:
    doc, project = _world_first_project_doc()
    csv_path = Path(str(tmp_path or Path.cwd())) / "tin_world_first_points.csv"
    try:
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["easting", "northing", "elevation"])
            writer.writerow([1000.0, 2000.0, 10.0])
            writer.writerow([1010.0, 2000.0, 11.0])
            writer.writerow([1000.0, 2010.0, 12.0])
            writer.writerow([1010.0, 2010.0, 13.0])

        surface = TINBuildService().build_from_csv(
            csv_path,
            project_id="test-project",
            surface_id="tin:world-first",
            doc_or_project=project,
        )
        vertices = {(round(v.x, 6), round(v.y, 6), round(v.z, 6)) for v in surface.vertex_rows}
        quality = {row.kind: row.value for row in surface.quality_rows}

        assert vertices == {(0.0, 0.0, 0.0), (10.0, 0.0, 1.0), (0.0, 10.0, 2.0), (10.0, 10.0, 3.0)}
        assert quality["coordinate_input"] == "World"
        assert quality["coordinate_model"] == "Local"
        assert quality["coordinate_workflow"] == "World-first"
        assert quality["crs_epsg"] == "EPSG:5186"
    finally:
        try:
            csv_path.unlink()
        except Exception:
            pass
        App.closeDocument(doc.Name)
