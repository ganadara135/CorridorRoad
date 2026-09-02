"""Assembly/Subassembly editor command for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets  # noqa: F401 - runtime-injected UI collaborator

from ..ui.editors.subassembly_editor import (  # noqa: F401 - runtime-injected UI collaborator
    _AssemblyTableComboBox,
    V1AssemblySubassemblyEditorTaskPanel,
    _AssemblySectionPreviewView,
    configure_assembly_subassembly_editor_task_panel_runtime,
)
from ..services.editing import prepare_assembly_edit

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ..models.source.assembly_model import (  # noqa: F401 - runtime-injected UI collaborator
    ASSEMBLY_SUBASSEMBLY_KINDS,
    ASSEMBLY_SUBASSEMBLY_SIDES,
    AssemblySubassemblyModel,
    SubassemblySectionTemplate,
    TemplateSubassembly,
    normalize_bench_rows,
    parse_subassembly_parameters,
    serialize_subassembly_parameters,
    subassembly_bench_validation_messages,
)
from ..models.source.subassembly_preset_model import SUBASSEMBLY_PRESET_STATUSES  # noqa: F401 - runtime-injected UI collaborator
from ..services.evaluation.subassembly_bench_row_parser import bench_rows_to_dicts, parse_bench_rows
from ..services.builders.applied_section_service import (
    ditch_section_row_local_profile,
    ditch_section_row_validation_messages,
)
from ..services.evaluation import SubassemblyBenchProfileService
from ..objects.obj_alignment import find_v1_alignment
from ..objects.obj_subassembly_assembly import (  # noqa: F401 - runtime-injected UI collaborator
    create_or_update_v1_assembly_subassembly_model_object,
    find_v1_assembly_subassembly_model,
    to_assembly_subassembly_model,
)
from ..objects.obj_subassembly_library import find_v1_subassembly_library, to_subassembly_library
from ..objects.obj_subassembly_preset_library import find_v1_subassembly_preset_library, to_subassembly_preset_library
from .assembly_preset_data import (  # noqa: F401 - runtime-injected UI collaborator
    ASSEMBLY_BENCH_MODES,
    ASSEMBLY_DAYLIGHT_MODES,
    ASSEMBLY_PRESETS,
    DITCH_PARAMETER_FIELDS,
    DITCH_PARAMETER_KEYS,
    DITCH_SHAPE_DEFAULTS,
    DITCH_SHAPES,
    SUBASSEMBLY_KIND_DEFINITION_REFS,
    assembly_preset_names,
)


SUBASSEMBLY_COLUMNS = (
    "Enabled",
    "Subassembly ID",
    "Subassembly Ref",
    "Template Ref",
    "Template Version",
    "Template Status",
    "Side",
    "Index",
    "Target Ref",
    "Notes",
    "Kind",
    "Width",
    "Slope",
    "Thickness",
    "Material",
    "Overrides",
    "Parameters",
    "Source Instance Ref",
)

COL_ENABLED = 0
COL_ID = 1
COL_DEFINITION_REF = 2
COL_PRESET_REF = 3
COL_PRESET_VERSION = 4
COL_PRESET_STATUS = 5
COL_SIDE = 6
COL_INDEX = 7
COL_TARGET_REF = 8
COL_NOTES = 9
COL_KIND = 10
COL_WIDTH = 11
COL_SLOPE = 12
COL_THICKNESS = 13
COL_MATERIAL = 14
COL_OVERRIDES = 15
COL_PARAMETERS = 16
COL_SOURCE_INSTANCE_REF = 17

HIDDEN_SOURCE_COLUMNS = (
    COL_PRESET_REF,
    COL_PRESET_VERSION,
    COL_PRESET_STATUS,
    COL_KIND,
    COL_WIDTH,
    COL_SLOPE,
    COL_THICKNESS,
    COL_MATERIAL,
    COL_OVERRIDES,
    COL_PARAMETERS,
    COL_SOURCE_INSTANCE_REF,
)


def run_v1_assembly_subassembly_editor_command():
    """Open the v1 Assembly/Subassembly editor panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    panel = V1AssemblySubassemblyEditorTaskPanel(document=document)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_assembly_subassembly_model(document)


def apply_v1_assembly_subassembly_model(
    *,
    document=None,
    project=None,
    assembly_model: AssemblySubassemblyModel,
    assembly_obj=None,
    object_name: str | None = None,
):
    """Persist a v1 AssemblySubassemblyModel source object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prepared = prepare_assembly_edit(assembly_model)
    prj = project or find_project(doc)
    if prj is None:
        try:
            prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
        except Exception:
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "Parametric Road Project"
    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    target_name = str(object_name or getattr(assembly_obj, "Name", "") or "V1AssemblySubassemblyModel")
    obj = create_or_update_v1_assembly_subassembly_model_object(
        document=doc,
        project=prj,
        assembly_model=prepared.model,
        object_name=target_name,
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def create_or_update_assembly_subassembly_section_preview(
    *,
    document=None,
    assembly_model: AssemblySubassemblyModel,
    definition_library=None,
    object_name: str = "V1AssemblySubassemblySectionPreview",
):
    """Create a lightweight 3D View cross-section preview from Assembly/Subassembly source rows."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    try:
        import Part  # type: ignore
    except Exception as exc:
        raise RuntimeError("FreeCAD Part workbench is required for Assembly/Subassembly section preview.") from exc
    template = _active_template(assembly_model)
    rows = [row for row in list(getattr(template, "subassembly_rows", []) or []) if bool(getattr(row, "enabled", True))]
    wires = _assembly_section_preview_wires(rows, definition_library=definition_library, part_module=Part)
    if not wires:
        raise RuntimeError("No enabled Assembly/Subassembly rows are available for preview.")
    obj = doc.getObject(object_name)
    if obj is None:
        obj = doc.addObject("Part::Feature", object_name)
    obj.Shape = Part.Compound(wires) if len(wires) > 1 else wires[0]
    obj.Label = "Assembly / Subassembly Section Preview"
    _set_preview_property(obj, "CRRecordKind", "v1_assembly_subassembly_section_preview")
    _set_preview_property(obj, "V1ObjectType", "V1AssemblySubassemblySectionPreview")
    _set_preview_property(obj, "AssemblyId", str(getattr(assembly_model, "assembly_id", "") or ""))
    _set_preview_property(obj, "TemplateId", str(getattr(template, "template_id", "") or "") if template is not None else "")
    _set_preview_integer_property(obj, "SubassemblyCount", len(rows))
    _style_assembly_section_preview_object(obj)
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def assembly_subassembly_preset_model_from_document(
    preset_name: str,
    document=None,
    *,
    project=None,
    alignment=None,
) -> AssemblySubassemblyModel:
    """Build a non-destructive AssemblySubassemblyModel from an Assembly preset."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    preset = ASSEMBLY_PRESETS.get(str(preset_name or "").strip())
    if preset is None:
        raise ValueError(f"Unknown Assembly preset: {preset_name}")
    prj = project or find_project(doc)
    alignment_obj = alignment or find_v1_alignment(doc)
    alignment_id = str(getattr(alignment_obj, "AlignmentId", "") or "")
    template_id = str(preset.get("template_id", "") or "template:subassembly")
    return AssemblySubassemblyModel(
        schema_version=1,
        project_id=_project_id(prj),
        assembly_id=str(preset.get("assembly_id", "") or "assembly:subassembly-main"),
        alignment_id=alignment_id,
        active_template_id=template_id,
        label=str(preset.get("label", "") or str(preset_name or "Assembly / Subassembly")),
        template_rows=[
            SubassemblySectionTemplate(
                template_id=template_id,
                template_kind="roadway",
                template_index=1,
                label=str(preset.get("template_label", "") or template_id),
                subassembly_rows=_preset_subassemblies(preset),
                notes=str(preset.get("note", "") or "Subassembly preset; edit before section generation."),
            )
        ],
    )


class CmdV1AssemblySubassemblyEditor:
    """Open the v1 Assembly/Subassembly source editor."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("typical_section.svg"),
            "MenuText": "Assembly / Subassembly",
            "ToolTip": "Define v1 assembly source using explicit Subassembly rows",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_assembly_subassembly_editor_command()


def _preset_subassemblies(preset: dict) -> list[TemplateSubassembly]:
    rows = []
    for index, row in enumerate(_preset_subassembly_rows(preset), start=1):
        subassembly_id, kind, side, width, slope, thickness, material, notes = row[:8]
        parameters = row[8] if len(row) > 8 else {}
        rows.append(
            TemplateSubassembly(
                subassembly_id=str(subassembly_id),
                kind=kind,
                subassembly_index=index,
                side=side,
                width=width,
                slope=slope,
                thickness=thickness,
                material=material,
                definition_ref=str(row[9] if len(row) > 9 else SUBASSEMBLY_KIND_DEFINITION_REFS.get(str(kind), "") or ""),
                parameters=dict(parameters or {}),
                notes=notes,
                enabled=True,
            )
        )
    return rows


def _preset_subassembly_rows(preset: dict) -> list[tuple]:
    """Return active Subassembly preset rows."""

    rows = list(preset.get("subassemblies", []) or [])
    return [tuple(row) for row in rows]


def _validate_subassembly_model(
    model: AssemblySubassemblyModel,
    *,
    available_definition_ids: set[str] | None = None,
    available_preset_ids: set[str] | None = None,
    preset_versions: dict[str, str] | None = None,
) -> list[str]:
    messages: list[str] = []
    available_refs = set(available_definition_ids or set())
    available_presets = set(available_preset_ids or set())
    version_by_preset = dict(preset_versions or {})
    if not model.assembly_id:
        messages.append("ERROR: assembly_id is required.")
    if not model.template_rows:
        messages.append("ERROR: at least one template row is required.")
    for template in list(model.template_rows or []):
        if not template.template_id:
            messages.append("ERROR: template_id is required.")
        ids = set()
        for subassembly in list(template.subassembly_rows or []):
            if not subassembly.subassembly_id:
                messages.append("ERROR: subassembly_id is required.")
            if subassembly.subassembly_id in ids:
                messages.append(f"ERROR: duplicate subassembly_id {subassembly.subassembly_id}.")
            ids.add(subassembly.subassembly_id)
            if subassembly.definition_ref and subassembly.definition_ref not in available_refs:
                messages.append(
                    f"ERROR: subassembly {subassembly.subassembly_id} references missing definition {subassembly.definition_ref}."
                )
            preset_ref = str(getattr(subassembly, "preset_ref", "") or "").strip()
            preset_version = str(getattr(subassembly, "preset_version", "") or "").strip()
            if preset_ref and preset_ref not in available_presets:
                messages.append(f"WARNING: subassembly {subassembly.subassembly_id} references missing preset {preset_ref}.")
            elif preset_ref and preset_version and version_by_preset.get(preset_ref, preset_version) != preset_version:
                messages.append(
                    f"WARNING: subassembly {subassembly.subassembly_id} preset {preset_ref} is outdated "
                    f"(row={preset_version}, library={version_by_preset.get(preset_ref)})."
                )
            if subassembly.width < 0.0:
                messages.append(f"ERROR: subassembly {subassembly.subassembly_id} width must not be negative.")
            messages.extend(f"WARNING: {message}" for message in ditch_section_row_validation_messages(subassembly))
            messages.extend(f"WARNING: {message}" for message in subassembly_bench_validation_messages(subassembly))
    return messages


def _guess_missing_subassembly_refs_for_panel(panel) -> None:
    filled: list[str] = []
    skipped_existing: list[str] = []
    no_guess: list[str] = []
    table = getattr(panel, "table", None)
    if table is None:
        return
    for row in range(table.rowCount()):
        subassembly_id = _item_text(table, row, COL_ID) or f"subassembly:{row + 1}"
        if _item_text(table, row, COL_DEFINITION_REF):
            skipped_existing.append(subassembly_id)
            continue
        guessed_ref = _guess_subassembly_definition_ref(
            getattr(panel, "document", None),
            subassembly_id,
            kind=_item_text(table, row, COL_KIND),
            side=_item_text(table, row, COL_SIDE),
        )
        if not guessed_ref:
            no_guess.append(subassembly_id)
            continue
        _set_combo_text(table, row, COL_DEFINITION_REF, guessed_ref)
        try:
            panel._style_subassembly_row(row)
        except Exception:
            pass
        filled.append(f"{subassembly_id} -> {guessed_ref}")
    try:
        panel._refresh_selected_detail()
    except Exception:
        pass
    parts = [
        "Guessed missing Subassembly Refs.",
        "Warning: guesses are based on Subassembly ID text and may be inaccurate. Review before Apply.",
        f"filled: {len(filled)}",
    ]
    if filled:
        parts.append("assigned: " + ", ".join(filled[:6]) + (f", +{len(filled) - 6} more" if len(filled) > 6 else ""))
    if skipped_existing:
        parts.append("kept existing: " + ", ".join(skipped_existing[:6]) + (f", +{len(skipped_existing) - 6} more" if len(skipped_existing) > 6 else ""))
    if no_guess:
        parts.append("no confident guess: " + ", ".join(no_guess[:6]) + (f", +{len(no_guess) - 6} more" if len(no_guess) > 6 else ""))
    summary = getattr(panel, "summary", None)
    if summary is not None and hasattr(summary, "setPlainText"):
        summary.setPlainText("\n".join(parts))


def _active_template(model: AssemblySubassemblyModel) -> SubassemblySectionTemplate | None:
    rows = list(getattr(model, "template_rows", []) or [])
    if not rows:
        return None
    active_id = str(getattr(model, "active_template_id", "") or "").strip()
    for row in rows:
        if str(getattr(row, "template_id", "") or "") == active_id:
            return row
    return rows[0]


def _assembly_section_preview_wires(rows: list[TemplateSubassembly], *, definition_library=None, part_module=None) -> list[object]:
    if App is None or part_module is None:
        return []
    wires = []
    for segment in _assembly_section_preview_segments(rows, definition_library=definition_library):
        topline = list(segment.get("topline", []) or [])
        if len(topline) >= 2:
            for start, end in zip(topline, topline[1:]):
                if start != end:
                    wires.extend(_assembly_section_preview_segment_wires(part_module, start, end, end, start))
            continue
        top_start, top_end, bottom_end, bottom_start = segment["points"]
        wires.extend(_assembly_section_preview_segment_wires(part_module, top_start, top_end, bottom_end, bottom_start))
    return wires


def _assembly_section_preview_segments(rows: list[TemplateSubassembly], *, definition_library=None) -> list[dict[str, object]]:
    segments: list[dict[str, object]] = []
    edge_by_side = {"left": (0.0, 0.0), "right": (0.0, 0.0)}
    ordered_rows = sorted(
        list(rows or []),
        key=lambda row: (int(getattr(row, "subassembly_index", 0) or 0), str(getattr(row, "subassembly_id", "") or "")),
    )
    for row in ordered_rows:
        side = str(getattr(row, "side", "") or "center").strip().lower()
        if side == "both":
            sides = ("left", "right")
        elif side in {"left", "right"}:
            sides = (side,)
        else:
            sides = ("left",)
        for side_label in sides:
            start_offset, start_z = edge_by_side.get(side_label, (0.0, 0.0))
            segment = _assembly_section_preview_segment(row, side_label=side_label, start_offset=start_offset, start_z=start_z, definition_library=definition_library)
            if segment is None:
                continue
            segments.append({"row": row, "side": side_label, **segment})
            edge_by_side[side_label] = segment["end"]
    return segments


def _assembly_section_preview_segment(row: TemplateSubassembly, *, side_label: str, start_offset: float, start_z: float, definition_library=None):
    definition = _definition_by_ref_in_library(definition_library, str(getattr(row, "definition_ref", "") or ""))
    if definition is not None:
        segment = _assembly_section_preview_definition_segment(
            row,
            definition,
            side_label=side_label,
            start_offset=start_offset,
            start_z=start_z,
        )
        if segment is not None:
            return segment
    params = _assembly_section_preview_parameters(row, definition_library=definition_library)
    kind = str(getattr(row, "kind", "") or "").strip().lower().replace("-", "_")
    if kind == "ditch":
        segment = _assembly_section_preview_ditch_segment(
            row,
            side_label=side_label,
            start_offset=start_offset,
            start_z=start_z,
        )
        if segment is not None:
            return segment
    if kind == "side_slope":
        segment = _assembly_section_preview_side_slope_segment(
            row,
            side_label=side_label,
            start_offset=start_offset,
            start_z=start_z,
        )
        if segment is not None:
            return segment
    width = _float(params.get("width", getattr(row, "width", 0.0)), 0.0)
    if kind == "side_slope":
        width = _float(params.get("side_slope_width", width), width)
    if width <= 1.0e-9:
        return None
    slope = _float(params.get("slope", params.get("default_slope", getattr(row, "slope", 0.0))), 0.0)
    thickness = abs(_float(params.get("thickness", getattr(row, "thickness", 0.0)), 0.0))
    if thickness <= 1.0e-9 and kind in {"lane", "shoulder", "bike_lane", "sidewalk", "median"}:
        thickness = 0.2
    direction = 1.0 if side_label == "left" else -1.0
    end_offset = float(start_offset) + direction * width
    end_z = float(start_z) + width * slope
    bottom_start = (float(start_offset), float(start_z) - thickness)
    bottom_end = (end_offset, end_z - thickness)
    top_start = (float(start_offset), float(start_z))
    top_end = (end_offset, end_z)
    return {
        "points": (top_start, top_end, bottom_end, bottom_start),
        "topline": (top_start, top_end),
        "end": top_end,
    }


def _assembly_section_preview_ditch_segment(
    row: TemplateSubassembly,
    *,
    side_label: str,
    start_offset: float,
    start_z: float,
):
    local_profile = ditch_section_row_local_profile(row)
    if len(local_profile) < 2:
        return None
    direction = 1.0 if side_label == "left" else -1.0
    points = tuple(
        (
            float(start_offset) + direction * float(local_offset),
            float(start_z) + float(z_delta),
        )
        for local_offset, z_delta, _role in local_profile
    )
    if len(points) < 2:
        return None
    return {
        "points": points,
        "topline": points,
        "end": points[-1],
    }


def _assembly_section_preview_side_slope_segment(
    row: TemplateSubassembly,
    *,
    side_label: str,
    start_offset: float,
    start_z: float,
):
    segments = SubassemblyBenchProfileService().evaluate(row).segment_rows
    if not segments:
        return None
    direction = 1.0 if side_label == "left" else -1.0
    points: list[tuple[float, float]] = [(float(start_offset), float(start_z))]
    offset = float(start_offset)
    z = 0.0
    for segment in segments:
        width = max(_float(segment.width, 0.0), 0.0)
        if width <= 1.0e-9:
            continue
        slope = _float(segment.slope, 0.0)
        offset += direction * width
        z += slope * width
        points.append((offset, z))
    if len(points) < 2:
        return None
    return {
        "points": tuple(points),
        "topline": tuple(points),
        "end": points[-1],
    }


def _assembly_section_preview_definition_segment(
    row: TemplateSubassembly,
    definition,
    *,
    side_label: str,
    start_offset: float,
    start_z: float,
):
    try:
        from ..services.evaluation.subassembly_expression_service import SubassemblyExpressionService
    except Exception:
        return None
    params = _assembly_section_preview_parameters(row, definition_library=None)
    try:
        evaluation = SubassemblyExpressionService().evaluate_definition(definition, parameter_overrides=params)
    except Exception:
        return None
    evaluated_points = {
        str(getattr(point, "point_id", "") or "").strip(): point
        for point in list(getattr(evaluation, "point_rows", []) or [])
        if str(getattr(point, "point_id", "") or "").strip()
    }
    if not evaluated_points:
        return None
    direction = 1.0 if side_label == "left" else -1.0

    def placed(point_id: str) -> tuple[float, float] | None:
        point = evaluated_points.get(str(point_id or "").strip())
        if point is None:
            return None
        return (
            float(start_offset) + direction * float(getattr(point, "x", 0.0) or 0.0),
            float(start_z) + float(getattr(point, "z", 0.0) or 0.0),
        )

    topline: list[tuple[float, float]] = []
    for link in list(getattr(definition, "link_rows", []) or []):
        start = placed(str(getattr(link, "start_point_ref", "") or ""))
        end = placed(str(getattr(link, "end_point_ref", "") or ""))
        if start is None or end is None:
            continue
        if not topline or topline[-1] != start:
            topline.append(start)
        topline.append(end)
    if not topline:
        for point in sorted(evaluated_points.values(), key=lambda item: float(getattr(item, "x", 0.0) or 0.0)):
            value = placed(str(getattr(point, "point_id", "") or ""))
            if value is not None:
                topline.append(value)
    topline = _unique_preview_points(topline)
    if len(topline) < 2:
        return None
    polygon_points = _assembly_section_preview_definition_polygon(definition, placed)
    if len(polygon_points) < 3:
        polygon_points = tuple(topline)
    end = max(topline, key=lambda point: abs(float(point[0]) - float(start_offset)))
    return {
        "points": tuple(polygon_points),
        "topline": tuple(topline),
        "end": end,
    }


def _assembly_section_preview_definition_polygon(definition, placed) -> tuple[tuple[float, float], ...]:
    for shape in list(getattr(definition, "shape_rows", []) or []):
        points = [
            placed(point_ref)
            for point_ref in list(getattr(shape, "point_refs", []) or [])
        ]
        output = _unique_preview_points([point for point in points if point is not None])
        if len(output) >= 3:
            return tuple(output)
    return ()


def _unique_preview_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    output: list[tuple[float, float]] = []
    for point in list(points or []):
        if output and abs(output[-1][0] - point[0]) <= 1.0e-9 and abs(output[-1][1] - point[1]) <= 1.0e-9:
            continue
        output.append(point)
    return output


def _assembly_section_preview_parameters(row: TemplateSubassembly, *, definition_library=None) -> dict[str, object]:
    params = {}
    definition = _definition_by_ref_in_library(definition_library, str(getattr(row, "definition_ref", "") or ""))
    if definition is not None:
        for parameter in list(getattr(definition, "parameter_rows", []) or []):
            key = str(getattr(parameter, "parameter_id", "") or "").strip()
            if key:
                params[key] = getattr(parameter, "value", "")
    params.update(dict(getattr(row, "parameters", {}) or {}))
    params.update(dict(getattr(row, "parameter_overrides", {}) or {}))
    if "width" not in params:
        params["width"] = getattr(row, "width", 0.0)
    if "slope" not in params:
        params["slope"] = getattr(row, "slope", 0.0)
    if "thickness" not in params:
        params["thickness"] = getattr(row, "thickness", 0.0)
    return params


def _definition_by_ref_in_library(library, definition_ref: str):
    ref = str(definition_ref or "").strip()
    if not ref or library is None:
        return None
    for row in list(getattr(library, "definition_rows", []) or []):
        if str(getattr(row, "definition_id", "") or "").strip() == ref:
            return row
    return None


def _assembly_section_preview_segment_wires(part_module, top_start, top_end, bottom_end, bottom_start) -> list[object]:
    vectors = [_preview_vector(top_start), _preview_vector(top_end), _preview_vector(bottom_end), _preview_vector(bottom_start), _preview_vector(top_start)]
    wires = []
    for start, end in ((vectors[0], vectors[1]), (vectors[1], vectors[2]), (vectors[2], vectors[3]), (vectors[3], vectors[0])):
        if _same_preview_vector(start, end):
            continue
        wires.append(part_module.makeLine(start, end))
    return wires


def _preview_vector(point: tuple[float, float]):
    return App.Vector(float(point[0]), 0.0, float(point[1]))


def _same_preview_vector(first, second, tolerance: float = 1.0e-9) -> bool:
    try:
        return (
            abs(float(first.x) - float(second.x)) <= tolerance
            and abs(float(first.y) - float(second.y)) <= tolerance
            and abs(float(first.z) - float(second.z)) <= tolerance
        )
    except Exception:
        return False


def _style_assembly_section_preview_object(obj) -> None:
    view = getattr(obj, "ViewObject", None)
    if view is None:
        return
    try:
        view.LineColor = (0.05, 0.85, 1.0)
        view.PointColor = (1.0, 0.8, 0.1)
        view.LineWidth = 3.0
        view.PointSize = 5.0
        view.Visibility = True
    except Exception:
        pass


def _set_preview_property(obj, name: str, value: object) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyString", name, "CorridorRoad")
        except Exception:
            return
    try:
        setattr(obj, name, str(value or ""))
    except Exception:
        pass


def _set_preview_integer_property(obj, name: str, value: int) -> None:
    if not hasattr(obj, name):
        try:
            obj.addProperty("App::PropertyInteger", name, "CorridorRoad")
        except Exception:
            return
    try:
        setattr(obj, name, int(value or 0))
    except Exception:
        pass


def _item_text(table, row: int, col: int) -> str:
    widget = table.cellWidget(row, col)
    if widget is not None and hasattr(widget, "currentText"):
        return str(widget.currentText() or "").strip()
    item = table.item(row, col)
    return str(item.text() if item is not None else "").strip()


def _set_table_item_text(table, row: int, col: int, value: object) -> None:
    item = table.item(row, col)
    if item is None:
        item = QtWidgets.QTableWidgetItem("")
        table.setItem(row, col, item)
    item.setText(str(value or ""))


def _set_combo_text(table, row: int, col: int, value: object) -> None:
    widget = table.cellWidget(row, col)
    text = str(value or "").strip()
    if widget is not None and hasattr(widget, "findText") and hasattr(widget, "setCurrentIndex"):
        index = widget.findText(text)
        if index < 0 and text and hasattr(widget, "addItem"):
            widget.addItem(text)
            index = widget.findText(text)
        if index >= 0:
            widget.setCurrentIndex(index)
        return
    _set_table_item_text(table, row, col, text)


def _preset_status_display(subassembly: TemplateSubassembly) -> str:
    status = str(getattr(subassembly, "preset_status", "") or "").strip()
    if status:
        return status
    return "linked" if str(getattr(subassembly, "preset_ref", "") or "").strip() else "snapshot"


def _preset_status_legend_text() -> str:
    return (
        "Template status colors: "
        "linked=green, modified=yellow, snapshot=gray, missing=red, outdated=orange. "
        "Refresh updates linked outdated template rows; Detach keeps a local custom snapshot."
    )


def _subassembly_library_model(document):
    library_obj = find_v1_subassembly_library(document)
    return to_subassembly_library(library_obj) if library_obj is not None else None


def _subassembly_preset_library_model(document):
    library_obj = find_v1_subassembly_preset_library(document)
    return to_subassembly_preset_library(library_obj) if library_obj is not None else None


def _subassembly_definition_ref_values(document) -> list[str]:
    library = _subassembly_library_model(document)
    values = [""]
    if library is not None:
        values.extend(str(row.definition_id) for row in list(getattr(library, "definition_rows", []) or []) if str(row.definition_id))
    return values


def _subassembly_definition_ref_set(document) -> set[str]:
    return {value for value in _subassembly_definition_ref_values(document) if value}


def _guess_subassembly_definition_ref(document, subassembly_id: str, *, kind: str = "", side: str = "") -> str:
    candidates = _subassembly_definition_guess_candidates(document)
    if not candidates:
        return ""
    wanted_tokens = _guess_tokens(subassembly_id)
    kind_tokens = _guess_tokens(kind)
    side_tokens = [token for token in _guess_tokens(side) if token not in {"center", "both"}]
    best_ref = ""
    best_score = 0
    for candidate in candidates:
        candidate_ref = str(candidate.get("definition_id", "") or "").strip()
        if not candidate_ref:
            continue
        candidate_text = str(candidate.get("search_text", "") or candidate_ref)
        candidate_tokens = set(_guess_tokens(candidate_text))
        candidate_compact = _compact_guess_text(candidate_text)
        subassembly_compact = _compact_guess_text(subassembly_id)
        score = 0
        if subassembly_compact and subassembly_compact in candidate_compact:
            score += 90
        for token in wanted_tokens:
            if token in candidate_tokens:
                score += 12
            elif token and token in candidate_compact:
                score += 6
        for token in kind_tokens:
            if token in candidate_tokens:
                score += 24
            elif token and token in candidate_compact:
                score += 12
        for token in side_tokens:
            if token in candidate_tokens:
                score += 3
        if score > best_score:
            best_score = score
            best_ref = candidate_ref
    return best_ref if best_score >= 12 else ""


def _subassembly_definition_guess_candidates(document) -> list[dict[str, str]]:
    library = _subassembly_library_model(document)
    if library is None:
        return [{"definition_id": value, "search_text": value} for value in _subassembly_definition_ref_values(document) if value]
    candidates: list[dict[str, str]] = []
    for row in list(getattr(library, "definition_rows", []) or []):
        definition_id = str(getattr(row, "definition_id", "") or "").strip()
        if not definition_id:
            continue
        search_parts = [
            definition_id,
            getattr(row, "name", ""),
            getattr(row, "kind", ""),
            getattr(row, "category", ""),
            getattr(row, "side", ""),
            getattr(row, "notes", ""),
        ]
        candidates.append(
            {
                "definition_id": definition_id,
                "search_text": " ".join(str(part or "") for part in search_parts),
            }
        )
    return candidates


def _guess_tokens(value: object) -> list[str]:
    text = str(value or "").strip().lower()
    for separator in (":", ";", ",", ".", "/", "\\", "-", "_", "(", ")", "[", "]", "{", "}"):
        text = text.replace(separator, " ")
    return [token for token in text.split() if token and token not in {"subassembly", "definition", "preset", "basic"}]


def _compact_guess_text(value: object) -> str:
    return "".join(_guess_tokens(value))


def _subassembly_preset_ref_values(document) -> list[str]:
    library = _subassembly_preset_library_model(document)
    values = [""]
    if library is not None:
        values.extend(
            str(row.preset_id)
            for row in list(getattr(library, "subassembly_preset_rows", []) or [])
            if str(row.preset_id)
        )
    return values


def _subassembly_preset_ref_set(document) -> set[str]:
    return {value for value in _subassembly_preset_ref_values(document) if value}


def _subassembly_preset_for_ref(document, preset_ref: str):
    ref = str(preset_ref or "").strip()
    if not ref:
        return None
    library = _subassembly_preset_library_model(document)
    if library is None:
        return None
    return library.subassembly_preset_by_id(ref)


def _subassembly_preset_version_map(document) -> dict[str, str]:
    library = _subassembly_preset_library_model(document)
    if library is None:
        return {}
    return {
        str(getattr(row, "preset_id", "") or ""): str(getattr(row, "version", "") or "")
        for row in list(getattr(library, "subassembly_preset_rows", []) or [])
        if str(getattr(row, "preset_id", "") or "")
    }


def _apply_preset_defaults_to_row(table, row: int, preset, *, clear_overrides: bool) -> None:
    parameters = dict(getattr(preset, "parameter_defaults", {}) or {})
    kind = str(getattr(preset, "kind", "") or _item_text(table, row, COL_KIND) or "lane")
    _set_table_item_text(table, row, COL_KIND, kind)
    definition_ref = str(getattr(preset, "definition_ref", "") or "").strip()
    if definition_ref:
        _set_combo_text(table, row, COL_DEFINITION_REF, definition_ref)
    _set_table_item_text(table, row, COL_PRESET_VERSION, str(getattr(preset, "version", "") or ""))
    _set_combo_text(table, row, COL_PRESET_STATUS, "linked")
    _set_table_item_text(
        table,
        row,
        COL_WIDTH,
        _format_float(_first_numeric_parameter(parameters, ("width", "side_slope_width"), _float(_item_text(table, row, COL_WIDTH)))),
    )
    _set_table_item_text(
        table,
        row,
        COL_SLOPE,
        _format_float(_first_numeric_parameter(parameters, ("slope", "default_slope"), _float(_item_text(table, row, COL_SLOPE)))),
    )
    _set_table_item_text(
        table,
        row,
        COL_THICKNESS,
        _format_float(_first_numeric_parameter(parameters, ("thickness",), _float(_item_text(table, row, COL_THICKNESS)))),
    )
    if "material" in parameters:
        _set_table_item_text(table, row, COL_MATERIAL, str(parameters.get("material", "") or ""))
    if clear_overrides:
        _set_table_item_text(table, row, COL_PARAMETERS, serialize_subassembly_parameters(parameters))
        _set_table_item_text(table, row, COL_OVERRIDES, "")
    else:
        merged_parameters = dict(parameters)
        merged_parameters.update(parse_subassembly_parameters(_item_text(table, row, COL_PARAMETERS)))
        _set_table_item_text(table, row, COL_PARAMETERS, serialize_subassembly_parameters(merged_parameters))
    if not _item_text(table, row, COL_SOURCE_INSTANCE_REF):
        _set_table_item_text(table, row, COL_SOURCE_INSTANCE_REF, _item_text(table, row, COL_ID))


def _subassembly_definition_for_ref(document, definition_ref: str):
    ref = str(definition_ref or "").strip()
    if not ref:
        return None
    library = _subassembly_library_model(document)
    if library is None:
        return None
    return library.definition_by_id(ref)


def _definition_override_rows(definition, overrides: dict[str, object]) -> list[tuple[str, object]]:
    override_values = dict(overrides or {})
    rows = []
    for parameter in list(getattr(definition, "parameter_rows", []) or []):
        key = str(getattr(parameter, "parameter_id", "") or "").strip()
        if not key:
            continue
        rows.append((key, override_values.get(key, getattr(parameter, "value", ""))))
    for key, value in sorted(override_values.items()):
        if not any(existing_key == key for existing_key, _existing_value in rows):
            rows.append((key, value))
    return rows


def _definition_parameter_defaults(definition) -> dict[str, object]:
    if definition is None:
        return {}
    return {
        str(getattr(parameter, "parameter_id", "") or "").strip(): getattr(parameter, "value", "")
        for parameter in list(getattr(definition, "parameter_rows", []) or [])
        if str(getattr(parameter, "parameter_id", "") or "").strip()
    }


def _override_value_changed(key: object, value: object, default: object) -> bool:
    key_text = str(key or "").strip()
    if key_text == "bench_rows":
        return _normalize_bench_rows_text(value) != _normalize_bench_rows_text(default)
    return str(value or "").strip() != str(default or "").strip()


def _definition_preview_text(definition, overrides: dict[str, object]) -> str:
    if definition is None:
        return ""
    values = {
        str(getattr(row, "parameter_id", "") or ""): getattr(row, "value", "")
        for row in list(getattr(definition, "parameter_rows", []) or [])
        if str(getattr(row, "parameter_id", "") or "")
    }
    values.update(dict(overrides or {}))
    lines = [
        f"definition_ref: {getattr(definition, 'definition_id', '')}",
        f"kind: {getattr(definition, 'kind', '')}, side_behavior: {getattr(definition, 'side_behavior', '')}",
        "",
        "parameters:",
    ]
    if values:
        lines.extend(f"- {key} = {value}" for key, value in sorted(values.items()))
    else:
        lines.append("- none")
    lines.append("")
    lines.append("points:")
    point_rows = list(getattr(definition, "point_rows", []) or [])
    if point_rows:
        lines.extend(
            f"- {getattr(row, 'point_id', '')} | x={getattr(row, 'x_expr', '')} | z={getattr(row, 'z_expr', '')} | code={getattr(row, 'code', '')}"
            for row in point_rows
        )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("links:")
    link_rows = list(getattr(definition, "link_rows", []) or [])
    if link_rows:
        lines.extend(
            f"- {getattr(row, 'link_id', '')} | {getattr(row, 'start_point_ref', '')}->{getattr(row, 'end_point_ref', '')} | surface_role={getattr(row, 'surface_role', '')}"
            for row in link_rows
        )
    else:
        lines.append("- none")
    return "\n".join(lines)


def _detail_parameter_rows(kind: object, parameters: dict[str, object]) -> list[tuple[str, object]]:
    params = dict(parameters or {})
    kind_text = str(kind or "").strip().lower().replace("-", "_")
    if kind_text == "ditch":
        shape = str(params.get("shape", "") or "trapezoid").strip().lower().replace("-", "_")
        shape = shape if shape in DITCH_SHAPES else "trapezoid"
        keys = ["shape"] + [key for key, _label in DITCH_PARAMETER_FIELDS if key != "shape"]
        return [(key, params.get(key, shape if key == "shape" else "")) for key in keys]
    if kind_text == "side_slope":
        rows = normalize_bench_rows(params.get("bench_rows", []))
        return [
            ("bench_mode", params.get("bench_mode", "none")),
            ("bench_rows", _compact_bench_rows(rows)),
            ("repeat_first_bench_to_daylight", "1" if _truthy(params.get("repeat_first_bench_to_daylight")) else "0"),
            ("daylight_mode", params.get("daylight_mode", "terrain")),
            ("daylight_search_step", params.get("daylight_search_step", "")),
            ("daylight_max_width", params.get("daylight_max_width", "")),
            ("daylight_max_width_delta", params.get("daylight_max_width_delta", "")),
            ("daylight_max_triangles", params.get("daylight_max_triangles", "")),
            ("cut_slope", params.get("cut_slope", "")),
            ("fill_slope", params.get("fill_slope", "")),
        ]
    if kind_text in {"lane", "shoulder"}:
        return [
            ("default_crossfall", params.get("default_crossfall", "")),
            ("superelevation_target", params.get("superelevation_target", "auto")),
            ("point_codes", params.get("point_codes", "")),
            ("link_codes", params.get("link_codes", "")),
            ("surface_role", params.get("surface_role", "design")),
        ]
    if kind_text in {"pavement_layer", "subbase"}:
        return [
            ("layer_width_source", params.get("layer_width_source", "parent")),
            ("shape_code", params.get("shape_code", "")),
            ("solid_family", params.get("solid_family", kind_text)),
            ("quantity_behavior", params.get("quantity_behavior", "volume")),
        ]
    return sorted(params.items())


def _detail_parameters(table) -> dict[str, object]:
    output: dict[str, object] = {}
    for row in range(table.rowCount()):
        key = _item_text(table, row, 0)
        value = _item_text(table, row, 1)
        if not key or not str(value).strip():
            continue
        output[key] = value
    return output


def _merge_detail_parameters(kind: object, existing: dict[str, object], edited: dict[str, object]) -> dict[str, object]:
    kind_text = str(kind or "").strip().lower().replace("-", "_")
    output = dict(existing or {})
    if kind_text == "ditch":
        for key in DITCH_PARAMETER_KEYS:
            output.pop(key, None)
        shape = str(edited.get("shape", "") or "trapezoid").strip().lower().replace("-", "_")
        output["shape"] = shape if shape in DITCH_SHAPES else "trapezoid"
        for key, _label in DITCH_PARAMETER_FIELDS:
            value = str(edited.get(key, "") or "").strip()
            if key != "shape" and value:
                output[key] = value
        return output
    if kind_text == "side_slope":
        for key in (
            "bench_mode",
            "bench_rows",
            "repeat_first_bench_to_daylight",
            "daylight_mode",
            "daylight_search_step",
            "daylight_max_width",
            "daylight_max_width_delta",
            "daylight_max_triangles",
            "cut_slope",
            "fill_slope",
        ):
            output.pop(key, None)
        mode = str(edited.get("bench_mode", "") or "none").strip().lower().replace("-", "_")
        output["bench_mode"] = mode if mode in ASSEMBLY_BENCH_MODES else "none"
        rows = normalize_bench_rows(edited.get("bench_rows", ""))
        if rows:
            output["bench_rows"] = rows
            output["bench_mode"] = "rows" if output["bench_mode"] == "none" else output["bench_mode"]
        if _truthy(edited.get("repeat_first_bench_to_daylight")):
            output["repeat_first_bench_to_daylight"] = True
        daylight_mode = str(edited.get("daylight_mode", "") or "").strip().lower().replace("-", "_")
        if daylight_mode and daylight_mode in ASSEMBLY_DAYLIGHT_MODES:
            output["daylight_mode"] = daylight_mode
        for key in ("daylight_search_step", "daylight_max_width", "daylight_max_width_delta", "daylight_max_triangles", "cut_slope", "fill_slope"):
            value = str(edited.get(key, "") or "").strip()
            if value:
                output[key] = value
        return output
    for key, value in dict(edited or {}).items():
        key_text = str(key or "").strip()
        if key_text and str(value).strip():
            output[key_text] = value
    return output


def _replace_detail_rows(table, rows: list[tuple[str, object]]) -> None:
    table.setRowCount(0)
    for key, value in rows:
        row = table.rowCount()
        table.insertRow(row)
        key_item = QtWidgets.QTableWidgetItem(str(key))
        key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
        table.setItem(row, 0, key_item)
        table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(value or "")))


def _detail_value(table, key: str) -> str:
    for row in range(table.rowCount()):
        if _item_text(table, row, 0) == key:
            return _item_text(table, row, 1)
    return ""


def _set_detail_value(table, key: str, value: object) -> None:
    for row in range(table.rowCount()):
        if _item_text(table, row, 0) == key:
            _set_table_item_text(table, row, 1, value)
            return
    row = table.rowCount()
    table.insertRow(row)
    key_item = QtWidgets.QTableWidgetItem(str(key))
    key_item.setFlags(key_item.flags() & ~QtCore.Qt.ItemIsEditable)
    table.setItem(row, 0, key_item)
    table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(value or "")))


def _compact_bench_rows(rows: list[dict[str, object]]) -> str:
    parts = []
    for row in _parsed_bench_row_dicts(rows):
        parts.append(
            ",".join(
                [
                    str(row.get("drop", 0.0)),
                    str(row.get("width", 0.0)),
                    str(row.get("slope", 0.0)),
                    str(row.get("post_slope", 0.0)),
                ]
            )
        )
    return "; ".join(parts)


def _normalize_bench_rows_text(value: object) -> str:
    return _compact_bench_rows(_parsed_bench_row_dicts(value))


def _parsed_bench_row_dicts(value: object) -> list[dict[str, object]]:
    result = parse_bench_rows(value)
    if result.rows:
        return bench_rows_to_dicts(result.rows)
    return normalize_bench_rows(value)


def _ditch_detail_note(parameters: dict[str, object]) -> str:
    shape = str(dict(parameters or {}).get("shape", "") or "trapezoid")
    depth = str(dict(parameters or {}).get("depth", "") or "")
    bottom = str(dict(parameters or {}).get("bottom_width", "") or "")
    parts = [f"{shape} ditch"]
    if bottom:
        parts.append(f"bottom={bottom}")
    if depth:
        parts.append(f"depth={depth}")
    return "; ".join(parts)


def _bench_detail_note(parameters: dict[str, object]) -> str:
    rows = normalize_bench_rows(dict(parameters or {}).get("bench_rows", []))
    if not rows:
        return "side slope"
    repeat = " repeat-to-daylight" if _truthy(dict(parameters or {}).get("repeat_first_bench_to_daylight")) else ""
    return f"side slope bench rows={len(rows)}{repeat}"


def _subassembly_preview_text(
    *,
    subassembly_id: str,
    kind: str,
    side: str,
    width: float,
    slope: float,
    thickness: float,
    material: str,
    parameters: dict[str, object],
) -> str:
    kind_text = str(kind or "").strip().lower().replace("-", "_")
    side_text = str(side or "center").strip().lower().replace("-", "_") or "center"
    params = dict(parameters or {})
    lines = [
        f"subassembly_ref: {subassembly_id}",
        f"kind: {kind_text}, side: {side_text}, width={float(width):.3f}, slope={float(slope):.4f}, thickness={float(thickness):.3f}",
    ]
    if material:
        lines.append(f"material: {material}")
    lines.append("")
    lines.extend(_preview_points(subassembly_id, kind_text, side_text, width, slope, params))
    lines.append("")
    lines.extend(_preview_links(subassembly_id, kind_text, side_text, material, params))
    lines.append("")
    lines.extend(_preview_shapes(subassembly_id, kind_text, side_text, thickness, material, params))
    diagnostics = _preview_diagnostics(subassembly_id, kind_text, width, params)
    if diagnostics:
        lines.append("")
        lines.append("diagnostics:")
        lines.extend(f"- {message}" for message in diagnostics)
    return "\n".join(lines)


def _physical_body_contract_summary(
    *,
    subassembly_id: str,
    kind: object,
    thickness: float,
    material: str,
    parameters: dict[str, object],
) -> str:
    """Return a concise UX summary of physical-body contract readiness."""

    kind_text = str(kind or "").strip().lower().replace("-", "_")
    params = dict(parameters or {})
    shape_capable = kind_text in {"pavement_layer", "subbase", "lane", "shoulder"}
    if not shape_capable:
        return "Physical-body contract: n/a for this Subassembly kind."
    shape_code = str(params.get("shape_code", "") or f"{kind_text}_body").strip()
    solid_family = str(params.get("solid_family", "") or kind_text).strip()
    material_text = str(material or "").strip()
    has_thickness = float(thickness or 0.0) > 0.0
    missing = []
    if not has_thickness:
        missing.append("thickness")
    if not material_text:
        missing.append("material")
    if not shape_code:
        missing.append("shape_code")
    if not solid_family:
        missing.append("solid_family")
    status = "ready" if not missing else "incomplete"
    details = (
        f"shape_code={shape_code or '-'}, solid_family={solid_family or '-'}, "
        f"material={material_text or '-'}, thickness={float(thickness or 0.0):.3f}"
    )
    if missing:
        details = f"{details}, missing={','.join(missing)}"
    return f"Physical-body contract: {status} ({details})"


def _preview_points(subassembly_id: str, kind: str, side: str, width: float, slope: float, params: dict[str, object]) -> list[str]:
    prefix = _id_tail(subassembly_id)
    if kind == "ditch":
        shape = str(params.get("shape", "") or "trapezoid")
        return [
            "points:",
            f"- point:{prefix}:inner_edge | code=ditch_inner | offset=0.000",
            f"- point:{prefix}:invert | code=ditch_invert | shape={shape}",
            f"- point:{prefix}:outer_edge | code=ditch_outer | offset={float(width):.3f}",
        ]
    if kind == "side_slope":
        rows = normalize_bench_rows(params.get("bench_rows", []))
        output = [
            "points:",
            f"- point:{prefix}:hinge | code=slope_hinge | offset=0.000",
        ]
        for index, row in enumerate(rows, start=1):
            output.append(f"- point:{prefix}:bench_{index} | code=slope_bench | width={float(row.get('width', 0.0) or 0.0):.3f}")
        output.append(f"- point:{prefix}:daylight | code=slope_daylight | offset={float(width):.3f}")
        return output
    if kind in {"lane", "shoulder"}:
        return [
            "points:",
            f"- point:{prefix}:start | code={kind}_start | offset=0.000",
            f"- point:{prefix}:end | code={kind}_end | offset={float(width):.3f} | dz={float(width) * float(slope):.3f}",
        ]
    if kind in {"pavement_layer", "subbase"}:
        return [
            "points:",
            f"- point:{prefix}:top_left | code={kind}_top",
            f"- point:{prefix}:top_right | code={kind}_top",
            f"- point:{prefix}:bottom_right | code={kind}_bottom",
            f"- point:{prefix}:bottom_left | code={kind}_bottom",
        ]
    return [
        "points:",
        f"- point:{prefix}:start | code={kind}_start",
        f"- point:{prefix}:end | code={kind}_end",
    ]


def _preview_links(subassembly_id: str, kind: str, side: str, material: str, params: dict[str, object]) -> list[str]:
    prefix = _id_tail(subassembly_id)
    if kind == "ditch":
        role = "drainage_surface"
        return [
            "links:",
            f"- link:{prefix}:inner_to_invert | code=ditch_side | surface_role={role}",
            f"- link:{prefix}:invert_to_outer | code=ditch_side | surface_role={role}",
        ]
    if kind == "side_slope":
        role = "slope_face"
        return [
            "links:",
            f"- link:{prefix}:slope_face | code=slope_face | surface_role={role}",
        ]
    if kind in {"lane", "shoulder"}:
        role = str(params.get("surface_role", "") or "design")
        return [
            "links:",
            f"- link:{prefix}:top | code={kind}_top | surface_role={role}",
        ]
    if kind in {"pavement_layer", "subbase"}:
        return [
            "links:",
            f"- link:{prefix}:top | code={kind}_top | surface_role=subgrade",
            f"- link:{prefix}:bottom | code={kind}_bottom | surface_role=material_boundary",
        ]
    return [
        "links:",
        f"- link:{prefix}:main | code={kind}_link | surface_role=design",
    ]


def _preview_shapes(
    subassembly_id: str,
    kind: str,
    side: str,
    thickness: float,
    material: str,
    params: dict[str, object],
) -> list[str]:
    prefix = _id_tail(subassembly_id)
    if kind in {"pavement_layer", "subbase", "lane", "shoulder"} and float(thickness or 0.0) > 0.0:
        family = str(params.get("solid_family", "") or kind)
        return [
            "shapes:",
            f"- shape:{prefix}:body | code={kind}_body | solid_family={family} | material={material or '-'}",
        ]
    if kind == "ditch":
        shape = str(params.get("shape", "") or "trapezoid")
        lining = str(params.get("lining_thickness", "") or "")
        if lining:
            return [
                "shapes:",
                f"- shape:{prefix}:lining | code=ditch_lining | shape={shape} | material={material or '-'}",
            ]
    return [
        "shapes:",
        "- none for this first-slice source preview",
    ]


def _preview_diagnostics(subassembly_id: str, kind: str, width: float, params: dict[str, object]) -> list[str]:
    messages: list[str] = []
    if float(width or 0.0) < 0.0:
        messages.append(f"{subassembly_id}: width must not be negative.")
    if kind == "ditch":
        shape = str(params.get("shape", "") or "trapezoid").strip().lower().replace("-", "_")
        if shape not in DITCH_SHAPES:
            messages.append(f"{subassembly_id}: unknown ditch shape {shape}.")
        if not str(params.get("depth", "") or "").strip():
            messages.append(f"{subassembly_id}: ditch depth is not defined.")
    if kind == "side_slope":
        rows = normalize_bench_rows(params.get("bench_rows", []))
        if str(params.get("bench_mode", "") or "").strip().lower() == "rows" and not rows:
            messages.append(f"{subassembly_id}: bench_mode is rows but no valid bench_rows exist.")
    return messages


def _id_tail(value: object) -> str:
    text = str(value or "").strip()
    if ":" in text:
        return text.split(":")[-1]
    return text or "subassembly"


def _format_float(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "0.000"


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _first_numeric_parameter(parameters: dict[str, object], keys: tuple[str, ...], default: float = 0.0) -> float:
    for key in keys:
        if key in dict(parameters or {}):
            return _float(dict(parameters or {}).get(key), default)
    return _float(default)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _project_id(project) -> str:
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


configure_assembly_subassembly_editor_task_panel_runtime(globals())


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EditAssemblySubassembly", CmdV1AssemblySubassemblyEditor())
