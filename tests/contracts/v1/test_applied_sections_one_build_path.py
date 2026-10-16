"""GR-6: Applied Sections have one build path.

Every document is built through one source bundle per Alignment, paired by AlignmentId: a General
Road document is one bundle, an Intersection document one per road. A source that belongs to
another Alignment is never read for this road, which the single-road path used to do by taking
the first object of each kind.
"""

from dataclasses import replace

import FreeCAD as App
import pytest

from freecad.Corridor_Road.v1.commands.cmd_centerline3d import show_v1_centerline3d_preview_object
from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import build_document_applied_section_set
from freecad.Corridor_Road.v1.commands.cmd_project_setup import create_corridorroad_project
from freecad.Corridor_Road.v1.commands.cmd_region_editor import apply_v1_region_model, region_preset_model_from_document
from freecad.Corridor_Road.v1.commands.cmd_subassembly_editor import (
    apply_v1_assembly_subassembly_model,
    assembly_subassembly_preset_model_from_document,
)
from freecad.Corridor_Road.v1.objects.obj_alignment import create_sample_v1_alignment
from freecad.Corridor_Road.v1.objects.obj_profile import create_sample_v1_profile
from freecad.Corridor_Road.v1.objects.obj_region import find_v1_region_model, to_region_model, update_v1_region_model_object
from freecad.Corridor_Road.v1.objects.obj_stationing import create_v1_stationing


def _road_doc(name: str, *, regions: bool = True):
    doc = App.newDocument(name)
    project = create_corridorroad_project(doc)
    alignment = create_sample_v1_alignment(doc, project=project)
    create_sample_v1_profile(doc, project=project, alignment=alignment)
    create_v1_stationing(doc, project=project, alignment=alignment, interval=30.0)
    show_v1_centerline3d_preview_object(doc, project=project)
    apply_v1_assembly_subassembly_model(
        document=doc,
        project=project,
        assembly_model=assembly_subassembly_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
    )
    if regions:
        apply_v1_region_model(
            document=doc,
            project=project,
            region_model=region_preset_model_from_document("Basic Road", doc, project=project, alignment=alignment),
        )
    return doc, project, alignment


def test_a_general_road_is_one_bundle_built_as_the_main_set() -> None:
    doc, project, alignment = _road_doc("CRV1OnePathRoad")
    try:
        applied = build_document_applied_section_set(doc, project=project)

        assert applied.applied_section_set_id == "applied-sections:main"
        assert applied.alignment_id == alignment.AlignmentId
        assert {section.alignment_id for section in applied.sections} == {alignment.AlignmentId}
    finally:
        App.closeDocument(doc.Name)


def test_a_missing_road_source_is_named() -> None:
    doc, project, _alignment = _road_doc("CRV1OnePathMissing", regions=False)
    try:
        with pytest.raises(RuntimeError, match="Required v1 sources are missing: Regions"):
            build_document_applied_section_set(doc, project=project)
    finally:
        App.closeDocument(doc.Name)


def test_a_region_source_of_another_alignment_is_not_read() -> None:
    doc, project, _alignment = _road_doc("CRV1OnePathForeignRegion")
    try:
        region_obj = find_v1_region_model(doc)
        update_v1_region_model_object(region_obj, replace(to_region_model(region_obj), alignment_id="alignment:another-road"))

        with pytest.raises(RuntimeError, match="Required v1 sources are missing: Regions"):
            build_document_applied_section_set(doc, project=project)
    finally:
        App.closeDocument(doc.Name)
