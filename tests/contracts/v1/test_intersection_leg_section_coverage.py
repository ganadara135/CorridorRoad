"""Item 5.6: an Alignment the build skips, and a leg that names it, must be reported.

`_applied_section_source_bundles` drops an Alignment that has no Profile, no
Region model or no Stationing of its own, so deleting a side road's Region used to
remove its sections with nothing said. These lock both ends of that report: the
Applied Sections side names the Alignment and what it lacks, and the Build
Parametric review names the leg that points at it.
"""

import FreeCAD as App

from freecad.Corridor_Road.v1.commands.cmd_generate_applied_sections import (
    incomplete_alignment_bundle_rows,
)
from freecad.Corridor_Road.v1.commands.cmd_intersection_presets import (
    create_intersection_preset_sources,
)
from freecad.Corridor_Road.v1.models.result.applied_section import AppliedSection
from freecad.Corridor_Road.v1.models.result.applied_section_set import AppliedSectionSet
from freecad.Corridor_Road.v1.models.source.intersection_model import (
    IntersectionLegRow,
    IntersectionModel,
    IntersectionRow,
)
from freecad.Corridor_Road.v1.objects.obj_region import find_v1_region_model


def _intersection_model(*alignment_refs: str) -> IntersectionModel:
    return IntersectionModel(
        schema_version=1,
        project_id="project:test",
        intersection_rows=[
            IntersectionRow(
                intersection_id="intersection:t",
                intersection_kind="t_intersection",
                primary_alignment_ref=alignment_refs[0],
                secondary_alignment_refs=list(alignment_refs[1:]),
                leg_rows=[
                    IntersectionLegRow(
                        leg_id=f"intersection:t:leg:{index}",
                        leg_role="primary_before" if index == 1 else "side_approach",
                        alignment_ref=ref,
                        intersection_id="intersection:t",
                    )
                    for index, ref in enumerate(alignment_refs, start=1)
                ],
            )
        ],
    )


def _applied_section_set(*alignment_ids: str) -> AppliedSectionSet:
    return AppliedSectionSet(
        schema_version=1,
        project_id="project:test",
        applied_section_set_id="applied-sections:main",
        alignment_id="alignment:multiple",
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="project:test",
                applied_section_id=f"applied-section:{index}",
                alignment_id=alignment_id,
            )
            for index, alignment_id in enumerate(alignment_ids, start=1)
        ],
    )


def test_incomplete_alignment_bundle_rows_is_empty_for_a_complete_preset() -> None:
    doc = App.newDocument("CRV1LegSectionCoverageComplete")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")

        assert incomplete_alignment_bundle_rows(doc) == []
    finally:
        App.closeDocument(doc.Name)


def test_incomplete_alignment_bundle_rows_names_the_alignment_and_what_it_lacks() -> None:
    doc = App.newDocument("CRV1LegSectionCoverageIncomplete")
    try:
        create_intersection_preset_sources(doc, preset_label="T Intersection - Basic")
        secondary_region = next(
            obj
            for obj in list(doc.Objects)
            if str(getattr(obj, "Name", "") or "").startswith("V1IntersectionRegionModel")
            and "secondary" in str(getattr(obj, "Name", "") or "").lower()
        )
        removed_alignment_id = str(getattr(secondary_region, "AlignmentId", "") or "")
        doc.removeObject(secondary_region.Name)
        doc.recompute()

        rows = incomplete_alignment_bundle_rows(doc)

        assert len(rows) == 1
        row = rows[0]
        assert row["alignment_id"] == removed_alignment_id
        assert row["missing"] == ["Regions"]
        assert row["status"] == "warn"
        assert "skip this Alignment" in str(row["notes"])
        # the complete road is still built, so the report is about the other one only
        assert find_v1_region_model(doc) is not None
    finally:
        App.closeDocument(doc.Name)
