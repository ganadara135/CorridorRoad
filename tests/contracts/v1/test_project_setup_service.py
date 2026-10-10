from dataclasses import fields, replace

from freecad.Corridor_Road.v1.services.editing.project_setup_service import (
    LOCKED_COORDINATE_FIELDS,
    ProjectSetupDraft,
    coordinate_workflow_note,
    crs_preset_note,
    locked_coordinate_changes,
    locked_field_labels,
    normalize_project_setup_draft,
    project_setup_summary,
    recommended_coordinate_workflow,
    unit_policy_note,
)


def test_a_crs_recommends_world_first_and_no_crs_local_first() -> None:
    assert recommended_coordinate_workflow("EPSG:5186") == "World-first"
    assert recommended_coordinate_workflow("  ") == "Local-first"


def test_normalize_stores_known_values_only() -> None:
    draft = normalize_project_setup_draft(
        ProjectSetupDraft(
            design_standard="aashto",
            linear_unit_display="custom",  # display has no custom unit
            linear_unit_import="MM",
            linear_unit_export="feet",
            custom_linear_unit_scale=0.0,
            tin_max_triangles=10,
            crs_epsg=" EPSG:5186 ",
            coordinate_workflow="",
            horizontal_datum=" KGD2002 ",
            coord_setup_status=" ",
        )
    )

    assert draft.design_standard == "AASHTO"
    assert (draft.linear_unit_display, draft.linear_unit_import, draft.linear_unit_export) == ("m", "mm", "m")
    assert draft.custom_linear_unit_scale == 1.0
    assert draft.tin_max_triangles == 1000
    assert draft.crs_epsg == "EPSG:5186"
    assert draft.coordinate_workflow == "World-first"
    assert draft.horizontal_datum == "KGD2002"
    assert draft.coord_setup_status == "Initialized"


def test_normalize_keeps_a_chosen_workflow_that_differs_from_the_recommendation() -> None:
    draft = normalize_project_setup_draft(ProjectSetupDraft(crs_epsg="EPSG:5186", coordinate_workflow="Local-first"))

    assert draft.coordinate_workflow == "Local-first"


def test_lock_blocks_only_coordinate_changes_while_the_setup_stays_locked() -> None:
    stored = ProjectSetupDraft(crs_epsg="EPSG:5186", project_origin_e=1000.0, coord_setup_locked=True)

    unit_edit = replace(stored, linear_unit_display="mm", design_standard="AASHTO")
    origin_edit = replace(stored, project_origin_e=1000.5, north_rotation_deg=1.0)
    unlocking_edit = replace(origin_edit, coord_setup_locked=False)

    assert locked_coordinate_changes(stored, unit_edit) == ()
    assert locked_coordinate_changes(stored, origin_edit) == ("project_origin_e", "north_rotation_deg")
    assert locked_coordinate_changes(stored, unlocking_edit) == ()
    assert locked_coordinate_changes(replace(stored, coord_setup_locked=False), replace(origin_edit, coord_setup_locked=True)) == ()


def test_lock_ignores_float_noise_from_the_stored_properties() -> None:
    stored = ProjectSetupDraft(project_origin_n=2000.0, coord_setup_locked=True)

    assert locked_coordinate_changes(stored, replace(stored, project_origin_n=2000.0 + 1.0e-12)) == ()


def test_every_locked_field_is_a_draft_field_with_a_panel_label() -> None:
    draft_fields = {item.name for item in fields(ProjectSetupDraft)}

    assert set(LOCKED_COORDINATE_FIELDS) <= draft_fields
    assert all(label != name for label, name in zip(locked_field_labels(LOCKED_COORDINATE_FIELDS), LOCKED_COORDINATE_FIELDS))


def test_help_text_explains_storage_units_workflow_and_crs() -> None:
    assert "Stored geometry stays in meters" in unit_policy_note(ProjectSetupDraft())
    assert "0.002500000 meter(s) per custom unit" in unit_policy_note(
        ProjectSetupDraft(linear_unit_import="custom", custom_linear_unit_scale=0.0025)
    )
    assert "World coordinates" in coordinate_workflow_note("World-first", auto_apply=True)
    assert "only guidance" in coordinate_workflow_note("Local-first", auto_apply=False)
    assert crs_preset_note("EPSG:5186").startswith("Preset selected: Korea 2000 / Central Belt 2010")
    assert crs_preset_note("EPSG:9999") == "Custom CRS/EPSG input: EPSG:9999"


def test_summary_reports_what_apply_stored() -> None:
    summary = project_setup_summary(ProjectSetupDraft(crs_epsg="EPSG:5186", coordinate_workflow="World-first"))

    assert summary.startswith("Applied: Display='m'")
    assert "EPSG='EPSG:5186'" in summary
    assert "Workflow='World-first'" in summary
