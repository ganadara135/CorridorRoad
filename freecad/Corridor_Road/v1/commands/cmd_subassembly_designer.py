"""SubAssembly Designer command for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import replace

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtCore, QtGui, QtWidgets

from ..ui.editors.subassembly_designer import (  # noqa: F401 - runtime-injected UI collaborator
    V1SubAssemblyDesignerTaskPanel,
    _DefinitionTableComboBox,
    _ZoomablePreviewView,
    configure_sub_assembly_designer_task_panel_runtime,
)
from ..services.editing import prepare_subassembly_library_edit

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ..models.source.subassembly_definition_model import (
    SUBASSEMBLY_SIDE_BEHAVIORS,
    SubassemblyDefinition,
    SubassemblyLibrary,
    SubassemblyLinkRow,
    SubassemblyParameterRow,
    SubassemblyPointRow,
    SubassemblyShapeRow,
    SubassemblyTargetRow,
)
from ..models.source.subassembly_definition_presets import (
    subassembly_definition_library_from_preset,
    subassembly_definition_preset_names,
)
from ..ui.common.styles import apply_clickable_tab_style  # noqa: F401 - runtime-injected UI collaborator
from ..models.source.assembly_model import (
    AssemblySubassemblyModel,
    SubassemblySectionTemplate,
    TemplateSubassembly,
)
from ..models.source.subassembly_preset_model import (
    SubassemblyPreset,
    SubassemblyPresetLibrary,
)
from ..objects.obj_subassembly_assembly import (
    create_or_update_v1_assembly_subassembly_model_object,
    find_v1_assembly_subassembly_model,
    to_assembly_subassembly_model,
)
from ..objects.obj_subassembly_library import (
    create_or_update_v1_subassembly_library_object,
    find_v1_subassembly_library,
    to_subassembly_library,
)
from ..objects.obj_subassembly_preset_library import (
    create_or_update_v1_subassembly_preset_library_object,
    find_v1_subassembly_preset_library,
    to_subassembly_preset_library,
)
from ..services.evaluation.subassembly_expression_service import SubassemblyExpressionService  # noqa: F401 - runtime-injected UI collaborator
from ..services.evaluation.subassembly_definition_validation_service import SubassemblyDefinitionValidationService  # noqa: F401 - runtime-injected UI collaborator
from ..services.evaluation.subassembly_bench_row_parser import parse_bench_rows


SUBASSEMBLY_DESIGNER_COMMAND_ID = "CorridorRoad_V1SubAssemblyDesigner"

DEFINITION_COLUMNS = (
    "Definition ID",
    "Name",
    "Kind",
    "Category",
    "Side",
    "Parameters",
    "Points",
    "Links",
    "Shapes",
    "Targets",
    "Enabled",
    "Notes",
)

PARAMETER_COLUMNS = ("Parameter ID", "Label", "Value", "Unit", "Required", "Min", "Max", "Notes")
POINT_COLUMNS = ("Point ID", "X Expression", "Z Expression", "Code", "Role", "Connectable", "Notes")
LINK_COLUMNS = ("Link ID", "From Point", "To Point", "Surface Role", "Code", "Material", "Quantity Role", "Notes")
SHAPE_COLUMNS = ("Shape ID", "Point Refs", "Shape Code", "Material", "Quantity Role", "Solid Role", "Closed", "Notes")
TARGET_COLUMNS = ("Target ID", "Target Kind", "Required", "Fallback Policy", "Notes")

SUBASSEMBLY_DESIGNER_KIND_VALUES = (
    "lane",
    "shoulder",
    "median",
    "curb",
    "gutter",
    "sidewalk",
    "bike_lane",
    "green_strip",
    "side_slope",
    "ditch",
    "lined_ditch",
    "barrier",
    "pavement_layer",
    "subbase",
    "structure_interface",
    "intersection_transition",
    "curb_return_transition",
    "custom",
)

SUBASSEMBLY_DESIGNER_CATEGORY_VALUES = (
    "",
    "roadway",
    "pavement",
    "grading",
    "drainage",
    "roadside",
    "structure",
    "earthwork",
    "custom",
)

SUBASSEMBLY_DESIGNER_SIDE_VALUES = tuple(SUBASSEMBLY_SIDE_BEHAVIORS)
SUBASSEMBLY_DESIGNER_ENABLED_VALUES = ("Yes", "No")
SUBASSEMBLY_DESIGNER_MATERIAL_VALUES = (
    "",
    "asphalt",
    "aggregate",
    "concrete",
    "soil",
    "grass",
    "vegetated",
    "stone",
    "masonry",
    "steel",
    "precast_concrete",
    "reinforced_concrete",
    "ditch_lining",
    "drainage_pipe",
    "custom",
)


def run_v1_subassembly_designer_command():
    """Open the v1 SubAssembly Designer panel."""

    if App is None or getattr(App, "ActiveDocument", None) is None:
        raise RuntimeError("No active document.")
    document = App.ActiveDocument
    panel = V1SubAssemblyDesignerTaskPanel(document=document)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return find_v1_subassembly_library(document)


def apply_v1_subassembly_library(
    *,
    document=None,
    project=None,
    library_model: SubassemblyLibrary | None = None,
    object_name: str | None = None,
):
    """Persist a v1 SubassemblyLibrary source object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
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
    model = library_model or subassembly_definition_library_from_preset(
        _first_preset_name(),
        project_id=_project_id(prj),
    )
    prepared = prepare_subassembly_library_edit(model)
    obj = create_or_update_v1_subassembly_library_object(
        document=doc,
        project=prj,
        library_model=prepared.model,
        object_name=str(object_name or "V1SubassemblyLibrary"),
    )
    try:
        doc.recompute()
    except Exception:
        pass
    return obj


def load_v1_subassembly_definition_from_active_assembly(
    *,
    document=None,
    subassembly_id: str = "",
) -> SubassemblyDefinition | None:
    """Return a Designer definition resolved from the active Assembly/Subassembly row."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    assembly_obj = find_v1_assembly_subassembly_model(doc)
    assembly_model = to_assembly_subassembly_model(assembly_obj) if assembly_obj is not None else None
    if assembly_model is None:
        return None
    subassembly = _active_assembly_subassembly(assembly_model, subassembly_id=subassembly_id)
    if subassembly is None:
        return None
    library_obj = find_v1_subassembly_library(doc)
    library_model = to_subassembly_library(library_obj) if library_obj is not None else None
    base_definition = None
    definition_ref = str(getattr(subassembly, "definition_ref", "") or "").strip()
    if library_model is not None and definition_ref:
        base_definition = library_model.definition_by_id(definition_ref)
    if base_definition is None:
        base_definition = _definition_from_template_subassembly(subassembly)
    return _definition_with_subassembly_values(base_definition, subassembly)


def apply_v1_subassembly_definition_to_active_assembly(
    *,
    document=None,
    project=None,
    definition: SubassemblyDefinition,
    subassembly_id: str = "",
):
    """Apply one Designer definition to the active Assembly/Subassembly source object."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    assembly_obj = find_v1_assembly_subassembly_model(doc)
    assembly_model = to_assembly_subassembly_model(assembly_obj) if assembly_obj is not None else None
    if assembly_model is None:
        assembly_model = AssemblySubassemblyModel(
            schema_version=1,
            project_id=_project_id(prj),
            assembly_id="assembly:subassembly-main",
            active_template_id="template:main",
            template_rows=[
                SubassemblySectionTemplate(
                    template_id="template:main",
                    template_kind="roadway",
                    template_index=1,
                    label="Main Template",
                    subassembly_rows=[],
                )
            ],
        )
    template_rows = list(getattr(assembly_model, "template_rows", []) or [])
    if not template_rows:
        template_rows = [
            SubassemblySectionTemplate(
                template_id="template:main",
                template_kind="roadway",
                template_index=1,
                label="Main Template",
                subassembly_rows=[],
            )
        ]
    active_template = _active_template_row(assembly_model, template_rows)
    active_template_index = template_rows.index(active_template)
    subassemblies = list(getattr(active_template, "subassembly_rows", []) or [])
    replacement = _template_subassembly_from_definition(
        definition,
        subassembly_id=subassembly_id or _matching_subassembly_id(subassemblies, definition) or f"subassembly:{len(subassemblies) + 1}",
        subassembly_index=_matching_subassembly_index(subassemblies, definition) or len(subassemblies) + 1,
    )
    replaced = False
    for index, row in enumerate(subassemblies):
        if _subassembly_matches_definition(row, definition, subassembly_id=subassembly_id):
            subassemblies[index] = replacement
            replaced = True
            break
    if not replaced:
        subassemblies.append(replacement)
    template_rows[active_template_index] = SubassemblySectionTemplate(
        template_id=active_template.template_id,
        template_kind=active_template.template_kind,
        template_index=active_template.template_index,
        label=active_template.label,
        subassembly_rows=subassemblies,
        notes=active_template.notes,
    )
    updated_model = AssemblySubassemblyModel(
        schema_version=int(getattr(assembly_model, "schema_version", 1) or 1),
        project_id=str(getattr(assembly_model, "project_id", "") or _project_id(prj)),
        label=str(getattr(assembly_model, "label", "") or "Assembly / Subassembly"),
        assembly_id=str(getattr(assembly_model, "assembly_id", "") or "assembly:subassembly-main"),
        alignment_id=str(getattr(assembly_model, "alignment_id", "") or ""),
        active_template_id=str(getattr(assembly_model, "active_template_id", "") or active_template.template_id),
        template_rows=template_rows,
    )
    return create_or_update_v1_assembly_subassembly_model_object(
        document=doc,
        project=prj,
        assembly_model=updated_model,
        object_name=str(getattr(assembly_obj, "Name", "") or "V1AssemblySubassemblyModel"),
    )


def save_v1_subassembly_definition_as_new_preset(
    *,
    document=None,
    project=None,
    definition: SubassemblyDefinition,
):
    """Save one Designer definition as a new project-level Subassembly preset."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    library_obj = find_v1_subassembly_preset_library(doc)
    library_model = to_subassembly_preset_library(library_obj) if library_obj is not None else None
    if library_model is None:
        library_model = SubassemblyPresetLibrary(
            schema_version=1,
            project_id=_project_id(prj),
            library_id="subassembly-preset-library:main",
        )
    rows = list(getattr(library_model, "subassembly_preset_rows", []) or [])
    preset_id = _unique_preset_id(
        _preset_id_from_definition(definition),
        {str(getattr(row, "preset_id", "") or "") for row in rows},
    )
    rows.append(SubassemblyPreset.from_definition(definition, preset_id=preset_id, version="1"))
    updated_library = SubassemblyPresetLibrary(
        schema_version=int(getattr(library_model, "schema_version", 1) or 1),
        project_id=str(getattr(library_model, "project_id", "") or _project_id(prj)),
        label=str(getattr(library_model, "label", "") or "SubAssembly Preset Library"),
        library_id=str(getattr(library_model, "library_id", "") or "subassembly-preset-library:main"),
        subassembly_preset_rows=rows,
        assembly_preset_rows=list(getattr(library_model, "assembly_preset_rows", []) or []),
    )
    return create_or_update_v1_subassembly_preset_library_object(
        document=doc,
        project=prj,
        library_model=updated_library,
        object_name=str(getattr(library_obj, "Name", "") or "V1SubassemblyPresetLibrary"),
    )


def update_v1_subassembly_preset_from_definition(
    *,
    document=None,
    project=None,
    definition: SubassemblyDefinition,
):
    """Update an existing project-level Subassembly preset from one Designer definition."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    library_obj = find_v1_subassembly_preset_library(doc)
    library_model = to_subassembly_preset_library(library_obj) if library_obj is not None else None
    if library_model is None:
        raise RuntimeError("No SubAssembly preset library was found.")
    rows = list(getattr(library_model, "subassembly_preset_rows", []) or [])
    target_id = _preset_id_from_definition(definition)
    target_index = None
    for index, row in enumerate(rows):
        if str(getattr(row, "preset_id", "") or "") == target_id:
            target_index = index
            break
    if target_index is None:
        raise RuntimeError(f"Preset was not found: {target_id}")
    existing = rows[target_index]
    next_version = _next_preset_version(getattr(existing, "version", "1"))
    rows[target_index] = SubassemblyPreset.from_definition(definition, preset_id=target_id, version=next_version)
    updated_library = SubassemblyPresetLibrary(
        schema_version=int(getattr(library_model, "schema_version", 1) or 1),
        project_id=str(getattr(library_model, "project_id", "") or _project_id(prj)),
        label=str(getattr(library_model, "label", "") or "SubAssembly Preset Library"),
        library_id=str(getattr(library_model, "library_id", "") or "subassembly-preset-library:main"),
        subassembly_preset_rows=rows,
        assembly_preset_rows=list(getattr(library_model, "assembly_preset_rows", []) or []),
    )
    return create_or_update_v1_subassembly_preset_library_object(
        document=doc,
        project=prj,
        library_model=updated_library,
        object_name=str(getattr(library_obj, "Name", "") or "V1SubassemblyPresetLibrary"),
    )


def duplicate_v1_subassembly_preset(
    *,
    document=None,
    project=None,
    preset_id: str,
):
    """Duplicate one project-level Subassembly preset as a new source preset."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    library_obj = find_v1_subassembly_preset_library(doc)
    library_model = to_subassembly_preset_library(library_obj) if library_obj is not None else None
    if library_model is None:
        raise RuntimeError("No SubAssembly preset library was found.")
    rows = list(getattr(library_model, "subassembly_preset_rows", []) or [])
    source = None
    for row in rows:
        if str(getattr(row, "preset_id", "") or "") == str(preset_id or "").strip():
            source = row
            break
    if source is None:
        raise RuntimeError(f"Preset was not found: {preset_id}")
    existing_ids = {str(getattr(row, "preset_id", "") or "") for row in rows}
    duplicate_id = _unique_preset_id(f"{source.preset_id}-copy", existing_ids)
    duplicate = replace(
        source,
        preset_id=duplicate_id,
        name=f"{getattr(source, 'name', '') or source.preset_id} Copy",
        version="1",
        notes=(str(getattr(source, "notes", "") or "") + f"\nDuplicated from {source.preset_id}.").strip(),
    )
    updated_library = SubassemblyPresetLibrary(
        schema_version=int(getattr(library_model, "schema_version", 1) or 1),
        project_id=str(getattr(library_model, "project_id", "") or _project_id(prj)),
        label=str(getattr(library_model, "label", "") or "SubAssembly Preset Library"),
        library_id=str(getattr(library_model, "library_id", "") or "subassembly-preset-library:main"),
        subassembly_preset_rows=rows + [duplicate],
        assembly_preset_rows=list(getattr(library_model, "assembly_preset_rows", []) or []),
    )
    return create_or_update_v1_subassembly_preset_library_object(
        document=doc,
        project=prj,
        library_model=updated_library,
        object_name=str(getattr(library_obj, "Name", "") or "V1SubassemblyPresetLibrary"),
    )


def rename_v1_subassembly_preset(
    *,
    document=None,
    project=None,
    preset_id: str,
    new_preset_id: str,
):
    """Rename one project-level Subassembly preset and update Assembly source refs."""

    old_id = str(preset_id or "").strip()
    new_id = str(new_preset_id or "").strip()
    if not old_id:
        raise RuntimeError("Preset id is required.")
    if not new_id:
        raise RuntimeError("New preset id is required.")
    if old_id == new_id:
        raise RuntimeError("New preset id is the same as the current preset id.")
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    library_obj = find_v1_subassembly_preset_library(doc)
    library_model = to_subassembly_preset_library(library_obj) if library_obj is not None else None
    if library_model is None:
        raise RuntimeError("No SubAssembly preset library was found.")
    rows = list(getattr(library_model, "subassembly_preset_rows", []) or [])
    if any(str(getattr(row, "preset_id", "") or "") == new_id for row in rows):
        raise RuntimeError(f"Preset already exists: {new_id}")
    found = False
    renamed_rows = []
    for row in rows:
        if str(getattr(row, "preset_id", "") or "") == old_id:
            renamed_rows.append(replace(row, preset_id=new_id))
            found = True
        else:
            renamed_rows.append(row)
    if not found:
        raise RuntimeError(f"Preset was not found: {old_id}")
    updated_library = SubassemblyPresetLibrary(
        schema_version=int(getattr(library_model, "schema_version", 1) or 1),
        project_id=str(getattr(library_model, "project_id", "") or _project_id(prj)),
        label=str(getattr(library_model, "label", "") or "SubAssembly Preset Library"),
        library_id=str(getattr(library_model, "library_id", "") or "subassembly-preset-library:main"),
        subassembly_preset_rows=renamed_rows,
        assembly_preset_rows=list(getattr(library_model, "assembly_preset_rows", []) or []),
    )
    library_result = create_or_update_v1_subassembly_preset_library_object(
        document=doc,
        project=prj,
        library_model=updated_library,
        object_name=str(getattr(library_obj, "Name", "") or "V1SubassemblyPresetLibrary"),
    )
    assembly_obj = find_v1_assembly_subassembly_model(doc)
    assembly_model = to_assembly_subassembly_model(assembly_obj) if assembly_obj is not None else None
    if assembly_model is not None:
        template_rows = []
        changed = False
        for template in list(getattr(assembly_model, "template_rows", []) or []):
            subassembly_rows = []
            for subassembly in list(getattr(template, "subassembly_rows", []) or []):
                if str(getattr(subassembly, "preset_ref", "") or "") == old_id:
                    subassembly_rows.append(replace(subassembly, preset_ref=new_id))
                    changed = True
                else:
                    subassembly_rows.append(subassembly)
            template_rows.append(replace(template, subassembly_rows=subassembly_rows))
        if changed:
            updated_assembly = replace(assembly_model, template_rows=template_rows)
            create_or_update_v1_assembly_subassembly_model_object(
                document=doc,
                project=prj,
                assembly_model=updated_assembly,
                object_name=str(getattr(assembly_obj, "Name", "") or "V1AssemblySubassemblyModel"),
            )
    return library_result


def delete_v1_subassembly_preset(
    *,
    document=None,
    project=None,
    preset_id: str,
):
    """Delete one project-level Subassembly preset without rewriting Assembly refs."""

    target_id = str(preset_id or "").strip()
    if not target_id:
        raise RuntimeError("Preset id is required.")
    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    library_obj = find_v1_subassembly_preset_library(doc)
    library_model = to_subassembly_preset_library(library_obj) if library_obj is not None else None
    if library_model is None:
        raise RuntimeError("No SubAssembly preset library was found.")
    rows = list(getattr(library_model, "subassembly_preset_rows", []) or [])
    remaining_rows = [row for row in rows if str(getattr(row, "preset_id", "") or "") != target_id]
    if len(remaining_rows) == len(rows):
        raise RuntimeError(f"Preset was not found: {target_id}")
    updated_library = SubassemblyPresetLibrary(
        schema_version=int(getattr(library_model, "schema_version", 1) or 1),
        project_id=str(getattr(library_model, "project_id", "") or _project_id(prj)),
        label=str(getattr(library_model, "label", "") or "SubAssembly Preset Library"),
        library_id=str(getattr(library_model, "library_id", "") or "subassembly-preset-library:main"),
        subassembly_preset_rows=remaining_rows,
        assembly_preset_rows=list(getattr(library_model, "assembly_preset_rows", []) or []),
    )
    return create_or_update_v1_subassembly_preset_library_object(
        document=doc,
        project=prj,
        library_model=updated_library,
        object_name=str(getattr(library_obj, "Name", "") or "V1SubassemblyPresetLibrary"),
    )


def detach_v1_active_assembly_subassembly_as_custom(
    *,
    document=None,
    project=None,
    subassembly_id: str = "",
):
    """Detach one active Assembly/Subassembly row from its preset reference."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    prj = project or find_project(doc)
    assembly_obj = find_v1_assembly_subassembly_model(doc)
    assembly_model = to_assembly_subassembly_model(assembly_obj) if assembly_obj is not None else None
    if assembly_model is None:
        raise RuntimeError("No Assembly/Subassembly model was found.")
    template_rows = list(getattr(assembly_model, "template_rows", []) or [])
    active_template = _active_template_row(assembly_model, template_rows)
    if active_template is None:
        raise RuntimeError("No active Assembly template was found.")
    active_template_index = template_rows.index(active_template)
    subassemblies = list(getattr(active_template, "subassembly_rows", []) or [])
    target = _active_assembly_subassembly(assembly_model, subassembly_id=subassembly_id)
    if target is None:
        raise RuntimeError("No active Subassembly row was found.")
    target_id = str(getattr(target, "subassembly_id", "") or "")
    detached_rows = [
        _detached_template_subassembly(row) if str(getattr(row, "subassembly_id", "") or "") == target_id else row
        for row in subassemblies
    ]
    template_rows[active_template_index] = SubassemblySectionTemplate(
        template_id=active_template.template_id,
        template_kind=active_template.template_kind,
        template_index=active_template.template_index,
        label=active_template.label,
        subassembly_rows=detached_rows,
        notes=active_template.notes,
    )
    updated_model = AssemblySubassemblyModel(
        schema_version=int(getattr(assembly_model, "schema_version", 1) or 1),
        project_id=str(getattr(assembly_model, "project_id", "") or _project_id(prj)),
        label=str(getattr(assembly_model, "label", "") or "Assembly / Subassembly"),
        assembly_id=str(getattr(assembly_model, "assembly_id", "") or "assembly:subassembly-main"),
        alignment_id=str(getattr(assembly_model, "alignment_id", "") or ""),
        active_template_id=str(getattr(assembly_model, "active_template_id", "") or active_template.template_id),
        template_rows=template_rows,
    )
    return create_or_update_v1_assembly_subassembly_model_object(
        document=doc,
        project=prj,
        assembly_model=updated_model,
        object_name=str(getattr(assembly_obj, "Name", "") or "V1AssemblySubassemblyModel"),
    )


class CmdV1SubAssemblyDesigner:
    """FreeCAD command wrapper for the SubAssembly Designer."""

    def GetResources(self):  # noqa: N802 - FreeCAD API name
        return {
            "Pixmap": icon_path("subassembly_designer.svg"),
            "MenuText": "SubAssembly Designer",
            "ToolTip": "Create and manage reusable v1 Subassembly definitions.",
        }

    def IsActive(self):  # noqa: N802 - FreeCAD API name
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):  # noqa: N802 - FreeCAD API name
        try:
            run_v1_subassembly_designer_command()
        except Exception as exc:
            if QtWidgets is not None:
                try:
                    QtWidgets.QMessageBox.warning(None, "SubAssembly Designer", str(exc))
                    return
                except Exception:
                    pass
            raise


def _project_id(project) -> str:
    if project is None:
        return "corridorroad-v1"
    return str(getattr(project, "ProjectId", "") or getattr(project, "Name", "") or "corridorroad-v1")


def _assembly_subassembly_row_labels(document) -> list[str]:
    assembly_obj = find_v1_assembly_subassembly_model(document)
    assembly_model = to_assembly_subassembly_model(assembly_obj) if assembly_obj is not None else None
    template = _active_template_row(assembly_model, list(getattr(assembly_model, "template_rows", []) or [])) if assembly_model is not None else None
    rows = list(getattr(template, "subassembly_rows", []) or []) if template is not None else []
    if not rows:
        return ["Auto: first enabled Assembly row"]
    labels = ["Auto: first enabled Assembly row"]
    preset_versions = _designer_subassembly_preset_version_map(document)
    for row in rows:
        subassembly_id = str(getattr(row, "subassembly_id", "") or "").strip()
        kind = str(getattr(row, "kind", "") or "subassembly").strip()
        side = str(getattr(row, "side", "") or "").strip()
        preset_ref = str(getattr(row, "preset_ref", "") or "").strip()
        preset_version = str(getattr(row, "preset_version", "") or "").strip()
        preset_status = str(getattr(row, "preset_status", "") or "").strip()
        definition_ref = str(getattr(row, "definition_ref", "") or "").strip()
        ref = preset_ref or definition_ref
        suffix = f" | {ref}" if ref else ""
        if preset_ref:
            status = _designer_display_preset_status(
                preset_ref=preset_ref,
                preset_version=preset_version,
                preset_status=preset_status,
                preset_versions=preset_versions,
            )
            library_version = str(preset_versions.get(preset_ref, "") or "")
            if status == "preset_outdated" and library_version and preset_version:
                version = f" v{preset_version}->{library_version}"
            else:
                version = f" v{preset_version}" if preset_version else ""
            suffix += f" | {status}{version}"
        labels.append(f"{subassembly_id or 'subassembly'} | {kind} | {side or '-'}{suffix}")
    return labels


def _designer_has_assembly_object(document) -> bool:
    return find_v1_assembly_subassembly_model(document) is not None


def _designer_subassembly_preset_version_map(document) -> dict[str, str]:
    library_obj = find_v1_subassembly_preset_library(document)
    library = to_subassembly_preset_library(library_obj) if library_obj is not None else None
    if library is None:
        return {}
    return {
        str(getattr(row, "preset_id", "") or ""): str(getattr(row, "version", "") or "")
        for row in list(getattr(library, "subassembly_preset_rows", []) or [])
        if str(getattr(row, "preset_id", "") or "")
    }


def _designer_preset_library_summary_text(document) -> str:
    rows = _designer_preset_library_rows(document)
    if rows is None:
        return "Advanced Subassembly Template Library: none yet. Use Save as Reusable Subassembly Template to create one."
    if not rows:
        return "Advanced Subassembly Template Library: 0 Reusable Subassembly Templates."
    preview = []
    for row in rows[:4]:
        preset_id = str(getattr(row, "preset_id", "") or "").strip() or "preset"
        version = str(getattr(row, "version", "") or "").strip()
        preview.append(f"{preset_id} v{version}" if version else preset_id)
    extra = f", +{len(rows) - 4} more" if len(rows) > 4 else ""
    return f"Advanced Subassembly Template Library: {len(rows)} Reusable Subassembly Template(s) | " + ", ".join(preview) + extra


def _designer_preset_library_rows(document):
    library_obj = find_v1_subassembly_preset_library(document)
    library = to_subassembly_preset_library(library_obj) if library_obj is not None else None
    if library is None:
        return None
    return list(getattr(library, "subassembly_preset_rows", []) or [])


def _designer_preset_by_id(document, preset_id: str):
    target = str(preset_id or "").strip()
    if not target:
        return None
    for preset in _designer_preset_library_rows(document) or []:
        if str(getattr(preset, "preset_id", "") or "") == target:
            return preset
    return None


def _designer_preset_difference_keys(definition: SubassemblyDefinition, preset) -> list[str]:
    changed: list[str] = []
    current_parameters = _definition_parameter_values(definition)
    default_parameters = dict(getattr(preset, "parameter_defaults", {}) or {})
    for key, value in current_parameters.items():
        if str(value) != str(default_parameters.get(key, "")):
            changed.append(f"parameter:{key}")
    point_roles = dict(getattr(preset, "point_roles", {}) or {})
    for point in list(getattr(definition, "point_rows", []) or []):
        point_id = str(getattr(point, "point_id", "") or "").strip()
        if point_id and str(getattr(point, "role", "") or "") != str(point_roles.get(point_id, "")):
            changed.append(f"point_role:{point_id}")
    link_roles = dict(getattr(preset, "link_roles", {}) or {})
    surface_roles = dict(getattr(preset, "surface_roles", {}) or {})
    quantity_roles = dict(getattr(preset, "quantity_roles", {}) or {})
    for link in list(getattr(definition, "link_rows", []) or []):
        link_id = str(getattr(link, "link_id", "") or "").strip()
        code = str(getattr(link, "code", "") or "").strip()
        surface_role = str(getattr(link, "surface_role", "") or "")
        quantity_role = str(getattr(link, "quantity_role", "") or "")
        if link_id and surface_role != str(link_roles.get(link_id, "")):
            changed.append(f"link_role:{link_id}")
        if code and surface_role != str(surface_roles.get(code, "")):
            changed.append(f"surface_role:{code}")
        if link_id and quantity_role != str(quantity_roles.get(link_id, "")):
            changed.append(f"quantity_role:{link_id}")
    shape_roles = dict(getattr(preset, "shape_roles", {}) or {})
    for shape in list(getattr(definition, "shape_rows", []) or []):
        shape_id = str(getattr(shape, "shape_id", "") or "").strip()
        solid_role = str(getattr(shape, "solid_role", "") or "")
        if shape_id and solid_role != str(shape_roles.get(shape_id, "")):
            changed.append(f"shape_role:{shape_id}")
    target_specs = dict(getattr(preset, "target_specs", {}) or {})
    for target in list(getattr(definition, "target_rows", []) or []):
        target_id = str(getattr(target, "target_id", "") or "").strip()
        spec = _designer_target_spec_text(target)
        if target_id and spec != str(target_specs.get(target_id, "")):
            changed.append(f"target:{target_id}")
    return changed


def _designer_target_spec_text(target) -> str:
    target_kind = str(getattr(target, "target_kind", "") or "").strip()
    required = "required" if bool(getattr(target, "required", False)) else "optional"
    fallback_policy = str(getattr(target, "fallback_policy", "") or "").strip()
    return "|".join((target_kind, required, fallback_policy))


def _designer_preset_history_text(preset) -> str:
    version = str(getattr(preset, "version", "") or "").strip()
    notes = str(getattr(preset, "notes", "") or "").strip()
    history_lines = [line.strip() for line in notes.splitlines() if line.strip().lower().startswith("duplicated from")]
    if history_lines:
        suffix = f"; current v{version}" if version else ""
        return history_lines[-1] + suffix
    return f"current v{version}" if version else "current"


def _designer_assembly_rows_referencing_preset(document, preset_id: str) -> list[str]:
    target = str(preset_id or "").strip()
    if not target:
        return []
    assembly_obj = find_v1_assembly_subassembly_model(document)
    assembly_model = to_assembly_subassembly_model(assembly_obj) if assembly_obj is not None else None
    if assembly_model is None:
        return []
    labels = []
    for template in list(getattr(assembly_model, "template_rows", []) or []):
        template_id = str(getattr(template, "template_id", "") or "template").strip()
        for subassembly in list(getattr(template, "subassembly_rows", []) or []):
            if str(getattr(subassembly, "preset_ref", "") or "") != target:
                continue
            subassembly_id = str(getattr(subassembly, "subassembly_id", "") or "subassembly").strip()
            labels.append(f"{template_id}:{subassembly_id}")
    return labels


def _designer_display_preset_status(
    *,
    preset_ref: str,
    preset_version: str,
    preset_status: str,
    preset_versions: dict[str, str],
) -> str:
    status = str(preset_status or "").strip() or "linked"
    if status == "modified":
        return status
    library_version = str(dict(preset_versions or {}).get(str(preset_ref or "").strip(), "") or "")
    if not library_version:
        return "missing_preset"
    row_version = str(preset_version or "").strip()
    if row_version and row_version != library_version:
        return "preset_outdated"
    if status in {"", "missing_preset", "preset_outdated", "outdated"}:
        return "linked"
    return status


def _selected_assembly_subassembly_id(combo) -> str:
    if combo is None:
        return ""
    text = str(combo.currentText() or "").strip()
    if not text or text.startswith("Auto:"):
        return ""
    return text.split("|", 1)[0].strip()


def _active_assembly_subassembly(
    assembly_model: AssemblySubassemblyModel,
    *,
    subassembly_id: str = "",
) -> TemplateSubassembly | None:
    template = _active_template_row(assembly_model, list(getattr(assembly_model, "template_rows", []) or []))
    if template is None:
        return None
    rows = list(getattr(template, "subassembly_rows", []) or [])
    target = str(subassembly_id or "").strip()
    if target:
        for row in rows:
            if str(getattr(row, "subassembly_id", "") or "") == target:
                return row
    for row in rows:
        if bool(getattr(row, "enabled", True)):
            return row
    return rows[0] if rows else None


def _active_template_row(
    assembly_model: AssemblySubassemblyModel,
    template_rows: list[SubassemblySectionTemplate],
) -> SubassemblySectionTemplate | None:
    if not template_rows:
        return None
    active_id = str(getattr(assembly_model, "active_template_id", "") or "").strip()
    for row in template_rows:
        if str(getattr(row, "template_id", "") or "") == active_id:
            return row
    return template_rows[0]


def _definition_from_template_subassembly(subassembly: TemplateSubassembly) -> SubassemblyDefinition:
    definition_ref = str(getattr(subassembly, "definition_ref", "") or "").strip()
    subassembly_id = str(getattr(subassembly, "subassembly_id", "") or "").strip()
    kind = str(getattr(subassembly, "kind", "") or "lane")
    return SubassemblyDefinition(
        definition_id=definition_ref or f"subassembly-definition:{subassembly_id or kind}",
        name=str(getattr(subassembly, "notes", "") or subassembly_id or kind).strip() or kind,
        kind=kind,
        side_behavior=str(getattr(subassembly, "side", "") or "agnostic"),
        parameter_rows=tuple(_parameter_rows_from_template_subassembly(subassembly)),
        enabled=bool(getattr(subassembly, "enabled", True)),
        notes=str(getattr(subassembly, "notes", "") or ""),
    )


def _definition_with_subassembly_values(
    definition: SubassemblyDefinition,
    subassembly: TemplateSubassembly,
) -> SubassemblyDefinition:
    values = _template_parameter_values(subassembly)
    parameter_rows = []
    seen = set()
    for row in tuple(getattr(definition, "parameter_rows", ()) or ()):
        key = str(getattr(row, "parameter_id", "") or "").strip()
        if key:
            seen.add(key)
        parameter_rows.append(
            SubassemblyParameterRow(
                parameter_id=row.parameter_id,
                label=row.label,
                value=values.get(key, row.value),
                unit=row.unit,
                min_value=row.min_value,
                max_value=row.max_value,
                required=row.required,
                notes=row.notes,
            )
        )
    for key, value in values.items():
        if key in seen:
            continue
        parameter_rows.append(SubassemblyParameterRow(parameter_id=key, label=key, value=value))
    return SubassemblyDefinition(
        definition_id=definition.definition_id,
        name=definition.name,
        kind=definition.kind,
        category=definition.category,
        side_behavior=definition.side_behavior,
        parameter_rows=tuple(parameter_rows),
        point_rows=definition.point_rows,
        link_rows=definition.link_rows,
        shape_rows=definition.shape_rows,
        target_rows=definition.target_rows,
        enabled=definition.enabled,
        notes=definition.notes,
    )


def _template_subassembly_from_definition(
    definition: SubassemblyDefinition,
    *,
    subassembly_id: str,
    subassembly_index: int,
) -> TemplateSubassembly:
    parameters = _definition_parameter_values(definition)
    return TemplateSubassembly(
        subassembly_id=str(subassembly_id or "").strip(),
        kind=str(getattr(definition, "kind", "") or "lane"),
        subassembly_index=int(subassembly_index or 0),
        side=_side_from_definition(getattr(definition, "side_behavior", "")),
        width=_float_parameter(parameters, "width", _float_parameter(parameters, "side_slope_width", 0.0)),
        slope=_float_parameter(parameters, "slope", _float_parameter(parameters, "default_slope", 0.0)),
        thickness=_float_parameter(parameters, "thickness", 0.0),
        material=str(parameters.get("material", "") or ""),
        definition_ref=str(getattr(definition, "definition_id", "") or ""),
        preset_ref=_preset_id_from_definition(definition),
        preset_version="1",
        preset_status="linked",
        source_instance_ref=str(subassembly_id or "").strip(),
        parameters=parameters,
        notes=str(getattr(definition, "name", "") or ""),
        enabled=bool(getattr(definition, "enabled", True)),
    )


def _parameter_rows_from_template_subassembly(subassembly: TemplateSubassembly) -> list[SubassemblyParameterRow]:
    values = _template_parameter_values(subassembly)
    return [SubassemblyParameterRow(parameter_id=key, label=key, value=value) for key, value in values.items()]


def _template_parameter_values(subassembly: TemplateSubassembly) -> dict[str, object]:
    values = dict(getattr(subassembly, "parameters", {}) or {})
    values.update(dict(getattr(subassembly, "parameter_overrides", {}) or {}))
    if "width" not in values:
        values["width"] = float(getattr(subassembly, "width", 0.0) or 0.0)
    if "slope" not in values:
        values["slope"] = float(getattr(subassembly, "slope", 0.0) or 0.0)
    if "thickness" not in values:
        values["thickness"] = float(getattr(subassembly, "thickness", 0.0) or 0.0)
    if str(getattr(subassembly, "material", "") or "") and "material" not in values:
        values["material"] = str(getattr(subassembly, "material", "") or "")
    return values


def _definition_parameter_values(definition: SubassemblyDefinition) -> dict[str, object]:
    return {
        str(getattr(row, "parameter_id", "") or "").strip(): getattr(row, "value", "")
        for row in tuple(getattr(definition, "parameter_rows", ()) or ())
        if str(getattr(row, "parameter_id", "") or "").strip()
    }


def _definition_from_subassembly_preset(preset) -> SubassemblyDefinition:
    preset_id = str(getattr(preset, "preset_id", "") or "").strip()
    definition_ref = str(getattr(preset, "definition_ref", "") or "").strip()
    definition_id = definition_ref or _definition_id_from_preset_id(preset_id)
    kind = str(getattr(preset, "kind", "") or "lane").strip() or "lane"
    parameter_rows = tuple(
        SubassemblyParameterRow(parameter_id=str(key), label=str(key), value=value)
        for key, value in dict(getattr(preset, "parameter_defaults", {}) or {}).items()
    )
    point_rows = tuple(
        SubassemblyPointRow(
            point_id=str(point_id),
            role=str(role),
            notes=f"Loaded from preset {preset_id}",
        )
        for point_id, role in dict(getattr(preset, "point_roles", {}) or {}).items()
    )
    link_rows = tuple(
        SubassemblyLinkRow(
            link_id=str(link_id),
            start_point_ref="",
            end_point_ref="",
            surface_role=str(surface_role),
            quantity_role=str(dict(getattr(preset, "quantity_roles", {}) or {}).get(link_id, "")),
            notes=f"Loaded from preset {preset_id}",
        )
        for link_id, surface_role in dict(getattr(preset, "link_roles", {}) or {}).items()
    )
    shape_rows = tuple(
        SubassemblyShapeRow(
            shape_id=str(shape_id),
            solid_role=str(solid_role),
            notes=f"Loaded from preset {preset_id}",
        )
        for shape_id, solid_role in dict(getattr(preset, "shape_roles", {}) or {}).items()
    )
    target_rows = tuple(
        _target_row_from_preset_spec(str(target_id), str(spec))
        for target_id, spec in dict(getattr(preset, "target_specs", {}) or {}).items()
    )
    notes = str(getattr(preset, "notes", "") or "")
    return SubassemblyDefinition(
        definition_id=definition_id,
        name=str(getattr(preset, "name", "") or preset_id or definition_id),
        kind=kind,
        category="preset",
        side_behavior="both",
        parameter_rows=parameter_rows,
        point_rows=point_rows,
        link_rows=link_rows,
        shape_rows=shape_rows,
        target_rows=target_rows,
        notes=(notes + "\n" if notes else "") + f"Loaded from Reusable Subassembly Template {preset_id}.",
    )


def _definition_id_from_preset_id(preset_id: str) -> str:
    text = str(preset_id or "").strip()
    if text.startswith("subassembly-preset:"):
        return "subassembly-definition:" + text.split(":", 1)[1]
    if text.startswith("subassembly-definition:"):
        return text
    return f"subassembly-definition:{_safe_preset_token(text or 'custom')}"


def _target_row_from_preset_spec(target_id: str, spec: str) -> SubassemblyTargetRow:
    parts = [part.strip() for part in str(spec or "").split("|")]
    target_kind = parts[0] if len(parts) > 0 and parts[0] else "terrain_daylight"
    required = _truthy(parts[1], default=False) if len(parts) > 1 else False
    fallback_policy = parts[2] if len(parts) > 2 else ""
    return SubassemblyTargetRow(
        target_id=str(target_id or "target"),
        target_kind=target_kind,
        required=required,
        fallback_policy=fallback_policy,
        notes="Loaded from preset target spec.",
    )


def _matching_subassembly_id(subassemblies: list[TemplateSubassembly], definition: SubassemblyDefinition) -> str:
    for row in subassemblies:
        if _subassembly_matches_definition(row, definition):
            return str(getattr(row, "subassembly_id", "") or "")
    return ""


def _matching_subassembly_index(subassemblies: list[TemplateSubassembly], definition: SubassemblyDefinition) -> int:
    for row in subassemblies:
        if _subassembly_matches_definition(row, definition):
            return int(getattr(row, "subassembly_index", 0) or 0)
    return 0


def _subassembly_matches_definition(
    subassembly: TemplateSubassembly,
    definition: SubassemblyDefinition,
    *,
    subassembly_id: str = "",
) -> bool:
    target_id = str(subassembly_id or "").strip()
    if target_id and str(getattr(subassembly, "subassembly_id", "") or "") == target_id:
        return True
    definition_id = str(getattr(definition, "definition_id", "") or "").strip()
    if definition_id and str(getattr(subassembly, "definition_ref", "") or "") == definition_id:
        return True
    return str(getattr(subassembly, "kind", "") or "") == str(getattr(definition, "kind", "") or "")


def _side_from_definition(side_behavior: object) -> str:
    text = str(side_behavior or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"left", "right", "center", "both"}:
        return text
    return "both"


def _float_parameter(values: dict[str, object], key: str, default: float = 0.0) -> float:
    try:
        return float(values.get(key, default) or default)
    except Exception:
        return float(default)


def _detached_template_subassembly(subassembly: TemplateSubassembly) -> TemplateSubassembly:
    return TemplateSubassembly(
        subassembly_id=str(getattr(subassembly, "subassembly_id", "") or ""),
        kind=str(getattr(subassembly, "kind", "") or "lane"),
        subassembly_index=int(getattr(subassembly, "subassembly_index", 0) or 0),
        side=str(getattr(subassembly, "side", "") or "center"),
        width=float(getattr(subassembly, "width", 0.0) or 0.0),
        slope=float(getattr(subassembly, "slope", 0.0) or 0.0),
        thickness=float(getattr(subassembly, "thickness", 0.0) or 0.0),
        material=str(getattr(subassembly, "material", "") or ""),
        target_ref=str(getattr(subassembly, "target_ref", "") or ""),
        definition_ref=str(getattr(subassembly, "definition_ref", "") or ""),
        preset_ref="",
        preset_version="",
        preset_status="snapshot",
        source_instance_ref=str(getattr(subassembly, "source_instance_ref", "") or ""),
        parameter_overrides=dict(getattr(subassembly, "parameter_overrides", {}) or {}),
        parameters=dict(getattr(subassembly, "parameters", {}) or {}),
        point_code_rules=tuple(getattr(subassembly, "point_code_rules", ()) or ()),
        link_code_rules=tuple(getattr(subassembly, "link_code_rules", ()) or ()),
        shape_code_rules=tuple(getattr(subassembly, "shape_code_rules", ()) or ()),
        notes=str(getattr(subassembly, "notes", "") or ""),
        enabled=bool(getattr(subassembly, "enabled", True)),
    )


def _preset_id_from_definition(definition: SubassemblyDefinition) -> str:
    definition_id = str(getattr(definition, "definition_id", "") or "").strip()
    name = str(getattr(definition, "name", "") or "").strip()
    raw = definition_id or name or "subassembly-preset"
    if raw.startswith("subassembly-preset:"):
        return raw
    if raw.startswith("subassembly-definition:"):
        raw = raw.split(":", 1)[1]
    return f"subassembly-preset:{_safe_preset_token(raw)}"


def _unique_preset_id(base_id: str, existing_ids: set[str]) -> str:
    base = str(base_id or "subassembly-preset:custom").strip() or "subassembly-preset:custom"
    if base not in existing_ids:
        return base
    index = 2
    while f"{base}-{index}" in existing_ids:
        index += 1
    return f"{base}-{index}"


def _next_preset_version(value: object) -> str:
    text = str(value or "1").strip()
    try:
        return str(int(text) + 1)
    except Exception:
        return f"{text}.1" if text else "2"


def _safe_preset_token(value: object) -> str:
    text = str(value or "custom").strip().lower().replace(" ", "-").replace("_", "-")
    safe = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in text)
    safe = "-".join(part for part in safe.split("-") if part)
    return safe or "custom"


def _confirm_action(parent, title: str, message: str) -> bool:
    try:
        result = QtWidgets.QMessageBox.question(
            parent,
            title,
            message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return result == QtWidgets.QMessageBox.Yes
    except Exception:
        return True


def _shared_template_update_choice(parent, title: str, message: str) -> str:
    try:
        box = QtWidgets.QMessageBox(parent)
        box.setWindowTitle(title)
        box.setText(message)
        update_button = box.addButton("Update Shared Subassembly Template", QtWidgets.QMessageBox.AcceptRole)
        copy_button = box.addButton("Save as Custom Copy", QtWidgets.QMessageBox.ActionRole)
        cancel_button = box.addButton(QtWidgets.QMessageBox.Cancel)
        box.setDefaultButton(cancel_button)
        box.exec_()
        clicked = box.clickedButton()
        if clicked is update_button:
            return "update"
        if clicked is copy_button:
            return "copy"
        return "cancel"
    except Exception:
        return "update"


def _first_preset_name() -> str:
    names = subassembly_definition_preset_names()
    return names[0] if names else "Starter Road Primitives"


def _read_only_flags(item):
    try:
        return item.flags() & ~QtCore.Qt.ItemIsEditable
    except Exception:
        return item.flags()


def _definition_count_columns() -> set[int]:
    return {5, 6, 7, 8, 9}


def _style_definition_count_item(item) -> None:
    try:
        item.setBackground(QtGui.QBrush(QtGui.QColor(32, 41, 56)))
        item.setForeground(QtGui.QBrush(QtGui.QColor(240, 244, 250)))
        item.setData(QtCore.Qt.BackgroundRole, QtGui.QBrush(QtGui.QColor(32, 41, 56)))
        item.setData(QtCore.Qt.ForegroundRole, QtGui.QBrush(QtGui.QColor(240, 244, 250)))
    except Exception:
        pass


def _new_table(columns: tuple[str, ...]):
    table = QtWidgets.QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def _append_table_row(table, values: tuple[object, ...]) -> None:
    row = table.rowCount()
    table.insertRow(row)
    for column, value in enumerate(values):
        table.setItem(row, column, QtWidgets.QTableWidgetItem(str(value)))


def _decorate_parameter_row(table, row: int, parameter_id: object) -> None:
    parameter = str(parameter_id or "").strip()
    if not parameter:
        return
    tooltip = ""
    if parameter == "bench_rows":
        tooltip = "Format: drop,width,slope,post_slope; drop,width,slope,post_slope"
        try:
            table.setRowHeight(int(row), max(int(table.rowHeight(int(row))), 34))
        except Exception:
            pass
    elif parameter in {
        "bench_mode",
        "bench_width",
        "bench_slope",
        "pre_bench_width",
        "post_slope_width",
        "post_slope",
        "repeat_first_bench_to_daylight",
    }:
        tooltip = "Side-slope bench parameter."
    elif parameter.startswith("daylight_") or parameter == "daylight_mode":
        tooltip = "Daylight search or fallback parameter."
    if not tooltip:
        return
    for column in range(table.columnCount()):
        item = table.item(int(row), column)
        if item is None:
            continue
        item.setToolTip(tooltip)


def _table_text(table, row: int, column: int) -> str:
    try:
        widget = table.cellWidget(int(row), int(column))
    except Exception:
        widget = None
    if widget is not None and hasattr(widget, "currentText"):
        try:
            return str(widget.currentText() or "").strip()
        except Exception:
            return ""
    try:
        item = table.item(int(row), int(column))
    except Exception:
        return ""
    return "" if item is None else str(item.text() or "").strip()


def _parameter_rows_from_table(table) -> list[SubassemblyParameterRow]:
    rows: list[SubassemblyParameterRow] = []
    for row in range(table.rowCount()):
        parameter_id = _table_text(table, row, 0)
        if not parameter_id:
            continue
        rows.append(
            SubassemblyParameterRow(
                parameter_id=parameter_id,
                label=_table_text(table, row, 1),
                value=_table_text(table, row, 2),
                unit=_table_text(table, row, 3),
                required=_truthy(_table_text(table, row, 4)),
                min_value=_table_text(table, row, 5),
                max_value=_table_text(table, row, 6),
                notes=_table_text(table, row, 7),
            )
        )
    return rows


def _point_rows_from_table(table) -> list[SubassemblyPointRow]:
    rows: list[SubassemblyPointRow] = []
    for row in range(table.rowCount()):
        point_id = _table_text(table, row, 0)
        if not point_id:
            continue
        rows.append(
            SubassemblyPointRow(
                point_id=point_id,
                x_expr=_table_text(table, row, 1) or "0.0",
                z_expr=_table_text(table, row, 2) or "0.0",
                code=_table_text(table, row, 3),
                role=_table_text(table, row, 4),
                connectable=_truthy(_table_text(table, row, 5)),
                notes=_table_text(table, row, 6),
            )
        )
    return rows


def _link_rows_from_table(table) -> list[SubassemblyLinkRow]:
    rows: list[SubassemblyLinkRow] = []
    for row in range(table.rowCount()):
        link_id = _table_text(table, row, 0)
        if not link_id:
            continue
        rows.append(
            SubassemblyLinkRow(
                link_id=link_id,
                start_point_ref=_table_text(table, row, 1),
                end_point_ref=_table_text(table, row, 2),
                surface_role=_table_text(table, row, 3),
                code=_table_text(table, row, 4),
                material=_table_text(table, row, 5),
                quantity_role=_table_text(table, row, 6),
                notes=_table_text(table, row, 7),
            )
        )
    return rows


def _shape_rows_from_table(table) -> list[SubassemblyShapeRow]:
    rows: list[SubassemblyShapeRow] = []
    for row in range(table.rowCount()):
        shape_id = _table_text(table, row, 0)
        if not shape_id:
            continue
        rows.append(
            SubassemblyShapeRow(
                shape_id=shape_id,
                point_refs=_split_refs(_table_text(table, row, 1)),
                shape_code=_table_text(table, row, 2),
                material=_table_text(table, row, 3),
                quantity_role=_table_text(table, row, 4),
                solid_role=_table_text(table, row, 5),
                closed=_truthy(_table_text(table, row, 6), default=True),
                notes=_table_text(table, row, 7),
            )
        )
    return rows


def _target_rows_from_table(table) -> list[SubassemblyTargetRow]:
    rows: list[SubassemblyTargetRow] = []
    for row in range(table.rowCount()):
        target_id = _table_text(table, row, 0)
        if not target_id:
            continue
        rows.append(
            SubassemblyTargetRow(
                target_id=target_id,
                target_kind=_table_text(table, row, 1),
                required=_truthy(_table_text(table, row, 2)),
                fallback_policy=_table_text(table, row, 3),
                notes=_table_text(table, row, 4),
            )
        )
    return rows


def _split_refs(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in str(text or "").replace(";", ",").split(",") if part.strip())


def _truthy(value: object, *, default: bool = False) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return bool(default)
    return text in {"1", "true", "yes", "y", "on"}


def _parameter_value(parameter) -> str:
    value = str(getattr(parameter, "value", "") or "")
    unit = str(getattr(parameter, "unit", "") or "")
    return f"{value} {unit}".strip()


def _preview_pen_for_link(link, default_pen, slope_pen, bench_pen):
    code = str(getattr(link, "code", "") or "").lower()
    link_id = str(getattr(link, "link_id", "") or "").lower()
    role = str(getattr(link, "surface_role", "") or "").lower()
    if "bench" in code or "bench" in link_id:
        return bench_pen
    if "slope" in code or "slope" in link_id or role == "slope_face_surface":
        return slope_pen
    return default_pen


def _surface_role_preview_hint(definition: SubassemblyDefinition) -> str:
    link_roles: dict[str, int] = {}
    for link in list(getattr(definition, "link_rows", []) or []):
        role = str(getattr(link, "surface_role", "") or "").strip()
        if role:
            link_roles[role] = link_roles.get(role, 0) + 1
    solid_roles: dict[str, int] = {}
    for shape in list(getattr(definition, "shape_rows", []) or []):
        role = str(getattr(shape, "solid_role", "") or "").strip()
        if role:
            solid_roles[role] = solid_roles.get(role, 0) + 1
    parts = []
    if link_roles:
        parts.append("links=" + ", ".join(f"{role}:{count}" for role, count in sorted(link_roles.items())))
    if solid_roles:
        parts.append("solids=" + ", ".join(f"{role}:{count}" for role, count in sorted(solid_roles.items())))
    if not parts:
        parts.append("none assigned")
    expected_roles = _expected_surface_roles_for_kind(str(getattr(definition, "kind", "") or ""))
    missing_roles = [role for role in expected_roles if role not in link_roles and role not in solid_roles]
    if missing_roles:
        parts.append("missing expected=" + ", ".join(missing_roles))
    return "Surface roles: " + " | ".join(parts)


def _expected_surface_roles_for_kind(kind: str) -> tuple[str, ...]:
    normalized = str(kind or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {"lane", "shoulder"}:
        return ("design_surface", "subgrade_surface")
    if normalized == "ditch":
        return ("drainage_surface",)
    if normalized == "side_slope":
        return ("slope_face_surface",)
    return ()


def _bench_rows_preview_hint(definition: SubassemblyDefinition) -> str:
    if str(getattr(definition, "kind", "") or "") != "side_slope":
        return ""
    parameters = {
        str(getattr(row, "parameter_id", "") or ""): str(getattr(row, "value", "") or "")
        for row in list(getattr(definition, "parameter_rows", []) or [])
    }
    bench_mode = parameters.get("bench_mode", "").strip().lower()
    bench_rows = parameters.get("bench_rows", "").strip()
    if not bench_mode or bench_mode == "none":
        return ""
    if not bench_rows:
        return "Bench rows: empty. Use drop,width,slope,post_slope."
    parse_result = parse_bench_rows(bench_rows, source_id=f"{definition.definition_id}:bench_rows")
    if parse_result.status == "error":
        return f"Bench rows: invalid ({len(parse_result.diagnostic_rows)} diagnostic(s))."
    return f"Bench rows: {len(parse_result.rows)} row(s). Format is drop,width,slope,post_slope."


def _diagnostic_summary(rows) -> str:
    diagnostics = list(rows or [])
    if not diagnostics:
        return "Preview ready."
    lines = [f"Diagnostics: {len(diagnostics)}"]
    for row in diagnostics[:6]:
        lines.append(f"{row.severity}:{row.kind}: {row.message}")
    if len(diagnostics) > 6:
        lines.append(f"+{len(diagnostics) - 6} more")
    return "\n".join(lines)


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


configure_sub_assembly_designer_task_panel_runtime(globals())


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand(SUBASSEMBLY_DESIGNER_COMMAND_ID, CmdV1SubAssemblyDesigner())
