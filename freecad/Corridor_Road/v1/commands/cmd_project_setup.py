"""v1 Project Setup command: units, design standard, CRS and the World/Local origin."""

from __future__ import annotations

from dataclasses import dataclass

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from ...objects.obj_project import CorridorRoadProject, ensure_project_properties, ensure_project_tree
from ..objects.project_setup_adapter import project_setup_draft_from_project, write_project_setup
from ..services.editing.project_setup_service import (
    ProjectSetupDraft,
    locked_coordinate_changes,
    normalize_project_setup_draft,
    project_setup_summary,
)
from ..ui.editors.project_setup_editor import (
    V1ProjectSetupTaskPanel,
    configure_project_setup_task_panel_runtime,
)


PROJECT_SETUP_COMMAND_ID = "CorridorRoad_ProjectSetup"


@dataclass(frozen=True)
class ProjectSetupApplyResult:
    """What Apply did: stored the draft, or refused because it edits a locked coordinate setup."""

    applied: bool
    draft: ProjectSetupDraft
    blocked_fields: tuple[str, ...] = ()
    summary: str = ""


def list_corridorroad_projects(document) -> list[object]:
    """Return the CorridorRoadProject objects of a document, in document order."""

    return [
        obj
        for obj in list(getattr(document, "Objects", []) or [])
        if str(getattr(obj, "Name", "") or "").startswith("CorridorRoadProject")
    ]


def preferred_corridorroad_project(document, selection=()) -> object | None:
    """A selected CorridorRoadProject first, else the document's first one."""

    for obj in list(selection or []):
        if str(getattr(obj, "Name", "") or "").startswith("CorridorRoadProject"):
            return obj
    projects = list_corridorroad_projects(document)
    return projects[0] if projects else None


def apply_v1_project_setup(project, draft: ProjectSetupDraft) -> ProjectSetupApplyResult:
    """Normalize and store one Project Setup edit unless it changes a locked coordinate setup."""

    if project is None:
        raise RuntimeError("No CorridorRoadProject selected.")
    normalized = normalize_project_setup_draft(draft)
    blocked = locked_coordinate_changes(project_setup_draft_from_project(project), normalized)
    if blocked:
        return ProjectSetupApplyResult(applied=False, draft=normalized, blocked_fields=blocked)
    write_project_setup(project, normalized)
    return ProjectSetupApplyResult(applied=True, draft=normalized, summary=project_setup_summary(normalized))


def run_v1_project_setup_command(document=None, *, preferred_project=None, prepare_project: bool = True):
    """Open Project Setup, creating the project root first when the document has none.

    `prepare_project` brings an existing root up to date first, as the Project Setup command
    always has; New Project has just done that, and the tree context menu never did.
    """

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    project = preferred_project or preferred_corridorroad_project(doc, _selection())
    if project is None:
        # imported here: cmd_new_project opens this panel, so it imports this module
        from ...commands.cmd_new_project import create_corridorroad_project

        project = create_corridorroad_project(doc)
        prepare_project = True
    if prepare_project:
        _prepare_project(project)
    panel = V1ProjectSetupTaskPanel(document=doc, preferred_project=project)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


def _prepare_project(project) -> None:
    """Bring an older project root up to the current properties and tree before the panel reads it."""

    try:
        ensure_project_properties(project)
        ensure_project_tree(project, include_references=False)
        CorridorRoadProject.auto_link(project.Document, project)
        project.touch()
        project.Document.recompute()
    except Exception as exc:
        # The panel still opens on the stored values; report why the tree was not refreshed.
        if App is not None:
            App.Console.PrintWarning(f"Project Setup could not refresh {getattr(project, 'Name', '')}: {exc}\n")


def _selection() -> list[object]:
    if Gui is None or not hasattr(Gui, "Selection"):
        return []
    try:
        return list(Gui.Selection.getSelection() or [])
    except Exception:
        return []


# Explicit command/controller callback boundary for the UI-owned task panel.
configure_project_setup_task_panel_runtime(globals())
