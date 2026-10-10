"""UI-independent Project Setup rules for CorridorRoad v1.

The Project object stores units, design standard, CRS and the World/Local origin. These rules
decide what a Project Setup edit means before anything is written: the coordinate workflow a CRS
recommends, which locked coordinate fields an edit would change, and the help text the panel
shows. They read no FreeCAD document and construct no Qt widget.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ....objects import design_standards as _standards
from ....objects import unit_policy as _units


COORDINATE_WORKFLOWS = ("World-first", "Local-first", "Custom")
SETUP_STATUS_CHOICES = ("Uninitialized", "Initialized", "Validated")
DEFAULT_TIN_MAX_TRIANGLES = 250000
MIN_TIN_MAX_TRIANGLES = 1000

# (label, code, description). The empty first row is the "custom or blank" entry.
CRS_PRESETS = (
    ("", "", ""),
    ("WGS 84 (EPSG:4326)", "EPSG:4326", "Global geographic coordinates"),
    ("WGS 84 / Pseudo-Mercator (EPSG:3857)", "EPSG:3857", "Common web map projection"),
    ("WGS 84 / UTM zone 51N (EPSG:32651)", "EPSG:32651", "UTM zone 51N"),
    ("WGS 84 / UTM zone 52N (EPSG:32652)", "EPSG:32652", "UTM zone 52N"),
    ("WGS 84 / UTM zone 53N (EPSG:32653)", "EPSG:32653", "UTM zone 53N"),
    ("Korea 2000 / Central Belt (EPSG:5181)", "EPSG:5181", "Korea local projected CRS"),
    ("Korea 2000 / West Belt 2010 (EPSG:5185)", "EPSG:5185", "Korea local projected CRS"),
    ("Korea 2000 / Central Belt 2010 (EPSG:5186)", "EPSG:5186", "Korea local projected CRS"),
    ("Korea 2000 / East Belt 2010 (EPSG:5187)", "EPSG:5187", "Korea local projected CRS"),
)

# Comparing origins read back from float properties: equal within the precision they are stored at.
_COORDINATE_TOLERANCE = 1.0e-9


@dataclass(frozen=True)
class ProjectSetupDraft:
    """One Project Setup edit. Lengths are meters; the rotation is degrees."""

    design_standard: str = _standards.DEFAULT_STANDARD
    linear_unit_display: str = _units.DEFAULT_LINEAR_UNIT
    linear_unit_import: str = _units.DEFAULT_LINEAR_UNIT
    linear_unit_export: str = _units.DEFAULT_LINEAR_UNIT
    custom_linear_unit_scale: float = _units.DEFAULT_CUSTOM_LINEAR_SCALE
    tin_max_triangles: int = DEFAULT_TIN_MAX_TRIANGLES
    crs_epsg: str = ""
    coordinate_workflow: str = "Local-first"
    auto_apply_coordinate_recommendations: bool = True
    horizontal_datum: str = ""
    vertical_datum: str = ""
    project_origin_e: float = 0.0
    project_origin_n: float = 0.0
    project_origin_z: float = 0.0
    local_origin_x: float = 0.0
    local_origin_y: float = 0.0
    local_origin_z: float = 0.0
    north_rotation_deg: float = 0.0
    coord_setup_locked: bool = False
    coord_setup_status: str = "Uninitialized"


# The fields "Lock coordinate setup" protects. Units and the design standard stay editable.
LOCKED_COORDINATE_FIELDS = (
    "crs_epsg",
    "horizontal_datum",
    "vertical_datum",
    "coordinate_workflow",
    "auto_apply_coordinate_recommendations",
    "project_origin_e",
    "project_origin_n",
    "project_origin_z",
    "local_origin_x",
    "local_origin_y",
    "local_origin_z",
    "north_rotation_deg",
)


def recommended_coordinate_workflow(crs_epsg: str) -> str:
    """A project with a CRS works in World coordinates; one without works in Local coordinates."""

    return "World-first" if str(crs_epsg or "").strip() else "Local-first"


def normalize_project_setup_draft(draft: ProjectSetupDraft) -> ProjectSetupDraft:
    """Return the draft as it is stored: known units and standard, a valid workflow and status."""

    crs_epsg = str(draft.crs_epsg or "").strip()
    workflow = str(draft.coordinate_workflow or "").strip()
    if workflow not in COORDINATE_WORKFLOWS:
        workflow = recommended_coordinate_workflow(crs_epsg)
    status = str(draft.coord_setup_status or "").strip() or "Initialized"
    custom_scale = float(draft.custom_linear_unit_scale)
    if custom_scale <= 0.0:
        custom_scale = _units.DEFAULT_CUSTOM_LINEAR_SCALE
    return replace(
        draft,
        design_standard=_standards.normalize_standard(draft.design_standard, default=_standards.DEFAULT_STANDARD),
        linear_unit_display=_linear_unit(draft.linear_unit_display, _units.DISPLAY_LINEAR_UNITS),
        linear_unit_import=_linear_unit(draft.linear_unit_import, _units.LINEAR_UNITS),
        linear_unit_export=_linear_unit(draft.linear_unit_export, _units.LINEAR_UNITS),
        custom_linear_unit_scale=custom_scale,
        tin_max_triangles=max(MIN_TIN_MAX_TRIANGLES, int(draft.tin_max_triangles)),
        crs_epsg=crs_epsg,
        coordinate_workflow=workflow,
        auto_apply_coordinate_recommendations=bool(draft.auto_apply_coordinate_recommendations),
        horizontal_datum=str(draft.horizontal_datum or "").strip(),
        vertical_datum=str(draft.vertical_datum or "").strip(),
        coord_setup_locked=bool(draft.coord_setup_locked),
        coord_setup_status=status,
    )


def locked_coordinate_changes(current: ProjectSetupDraft, draft: ProjectSetupDraft) -> tuple[str, ...]:
    """Return the locked coordinate fields the draft would change.

    Nothing is blocked when the stored setup is unlocked, or when the draft unlocks it: clearing
    "Lock coordinate setup" is how a user edits a locked setup.
    """

    if not current.coord_setup_locked or not draft.coord_setup_locked:
        return ()
    changed = []
    for name in LOCKED_COORDINATE_FIELDS:
        before = getattr(current, name)
        after = getattr(draft, name)
        if isinstance(before, float) or isinstance(after, float):
            if abs(float(before) - float(after)) > _COORDINATE_TOLERANCE:
                changed.append(name)
        elif before != after:
            changed.append(name)
    return tuple(changed)


def unit_policy_note(draft: ProjectSetupDraft) -> str:
    """Explain the unit settings: storage stays in meters whatever the user units are."""

    note = (
        "Stored geometry stays in meters. Display Unit controls task-panel/report formatting. "
        "Default Import Unit is used when incoming files or pasted values do not declare a unit. "
        "Default Export Unit controls CSV/report output formatting."
    )
    if uses_custom_linear_unit(draft):
        return note + f" Custom conversion uses {float(draft.custom_linear_unit_scale):.9f} meter(s) per custom unit."
    return note + " Standard project units use built-in meter/millimeter conversions."


def uses_custom_linear_unit(draft: ProjectSetupDraft) -> bool:
    return "custom" in (str(draft.linear_unit_import).lower(), str(draft.linear_unit_export).lower())


def coordinate_workflow_note(workflow: str, *, auto_apply: bool) -> str:
    """Explain what the coordinate workflow makes the import panels default to."""

    if workflow == "World-first":
        note = "Recommended input mode: World coordinates. Terrain and alignment panels will default to World mode."
    elif workflow == "Local-first":
        note = "Recommended input mode: Local coordinates. Terrain and alignment panels will default to Local mode."
    else:
        note = "Recommended input mode: Custom. Task panels keep their own coordinate choice unless changed manually."
    if not auto_apply:
        note += " Auto-apply is off, so this is only guidance."
    return note


def crs_preset_note(crs_epsg: str) -> str:
    """Name the preset a CRS code belongs to, or say it is a custom code."""

    code = str(crs_epsg or "").strip()
    for label, preset_code, description in CRS_PRESETS:
        if preset_code and preset_code == code:
            return f"Preset selected: {label}" + (f" - {description}" if description else "")
    if code:
        return f"Custom CRS/EPSG input: {code}"
    return "Select a common preset or enter a custom CRS/EPSG code."


def project_setup_summary(draft: ProjectSetupDraft) -> str:
    """One line recording what Apply stored."""

    return (
        f"Applied: Display='{draft.linear_unit_display}', Import='{draft.linear_unit_import}', "
        f"Export='{draft.linear_unit_export}', CustomScale={float(draft.custom_linear_unit_scale):.9f}, "
        f"Standard='{draft.design_standard}', EPSG='{draft.crs_epsg}', Workflow='{draft.coordinate_workflow}', "
        f"TINLimit={int(draft.tin_max_triangles)}, NorthRot={float(draft.north_rotation_deg):.6f}, "
        f"Locked={bool(draft.coord_setup_locked)}"
    )


def locked_field_labels(field_names) -> tuple[str, ...]:
    """Panel labels for locked field names, in panel order."""

    return tuple(_FIELD_LABELS.get(name, name) for name in field_names)


_FIELD_LABELS = {
    "crs_epsg": "CRS / EPSG",
    "horizontal_datum": "Horizontal Datum",
    "vertical_datum": "Vertical Datum",
    "coordinate_workflow": "Coordinate Workflow",
    "auto_apply_coordinate_recommendations": "Auto-apply recommended modes",
    "project_origin_e": "Project Origin E",
    "project_origin_n": "Project Origin N",
    "project_origin_z": "Project Origin Z",
    "local_origin_x": "Local Origin X",
    "local_origin_y": "Local Origin Y",
    "local_origin_z": "Local Origin Z",
    "north_rotation_deg": "North Rotation",
}


def _linear_unit(value: str, allowed) -> str:
    text = str(value or "").strip().lower()
    return text if text in allowed else _units.DEFAULT_LINEAR_UNIT


__all__ = [
    "COORDINATE_WORKFLOWS",
    "CRS_PRESETS",
    "DEFAULT_TIN_MAX_TRIANGLES",
    "LOCKED_COORDINATE_FIELDS",
    "MIN_TIN_MAX_TRIANGLES",
    "ProjectSetupDraft",
    "SETUP_STATUS_CHOICES",
    "coordinate_workflow_note",
    "crs_preset_note",
    "locked_coordinate_changes",
    "locked_field_labels",
    "normalize_project_setup_draft",
    "project_setup_summary",
    "recommended_coordinate_workflow",
    "unit_policy_note",
    "uses_custom_linear_unit",
]
