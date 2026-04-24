"""Legacy command handoff helpers for CorridorRoad v1 preview panels."""

from __future__ import annotations

try:
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD GUI is not available in tests.
    Gui = None

from .ui_state import set_ui_context


def run_legacy_command(
    command_name: str,
    *,
    gui_module=None,
    close_dialog: bool = True,
    objects_to_select: list[object] | None = None,
    context_payload: dict[str, object] | None = None,
) -> tuple[bool, str]:
    """Run one registered legacy GUI command and return a status tuple."""

    gui = gui_module or Gui
    if gui is None:
        return False, f"FreeCAD GUI is not available for `{command_name}`."

    try:
        if context_payload is not None:
            set_ui_context(**dict(context_payload))
        if objects_to_select:
            _sync_selection(gui, list(objects_to_select))
        if close_dialog and hasattr(gui, "Control"):
            try:
                gui.Control.closeDialog()
            except Exception:
                pass
        gui.runCommand(command_name, 0)
        return True, f"Opened `{command_name}`."
    except Exception as exc:
        return False, f"Could not open `{command_name}`: {exc}"


def _sync_selection(gui, objects_to_select: list[object]) -> None:
    """Best-effort sync of the GUI selection to one object list."""

    selection = getattr(gui, "Selection", None)
    if selection is None:
        return
    try:
        selection.clearSelection()
    except Exception:
        pass

    for obj in objects_to_select:
        if obj is None:
            continue
        if _try_add_selection(selection, obj):
            continue


def _try_add_selection(selection, obj) -> bool:
    """Try a few selection API shapes until one works."""

    try:
        selection.addSelection(obj)
        return True
    except Exception:
        pass

    document = getattr(obj, "Document", None)
    document_name = str(getattr(document, "Name", "") or "")
    object_name = str(getattr(obj, "Name", "") or "")

    if document_name and object_name:
        try:
            selection.addSelection(document_name, object_name)
            return True
        except Exception:
            pass
        try:
            selection.addSelection(document_name, object_name, "", 0.0, 0.0, 0.0)
            return True
        except Exception:
            pass

    return False
