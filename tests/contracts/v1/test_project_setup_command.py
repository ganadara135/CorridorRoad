import FreeCAD as App

from freecad.Corridor_Road.commands import cmd_new_project
from freecad.Corridor_Road.commands import cmd_project_setup


def _project_roots(doc):
    return [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if str(getattr(obj, "Name", "") or "").startswith("CorridorRoadProject")
    ]


class _CapturedControl:
    def __init__(self):
        self.panels = []

    def showDialog(self, panel):
        self.panels.append(panel)


def _install_control():
    original_control = getattr(cmd_project_setup.Gui, "Control", None)
    original_had_control = hasattr(cmd_project_setup.Gui, "Control")
    control = _CapturedControl()
    cmd_project_setup.Gui.Control = control
    return original_had_control, original_control, control


def _restore_control(original_had_control, original_control) -> None:
    if original_had_control:
        cmd_project_setup.Gui.Control = original_control
    else:
        delattr(cmd_project_setup.Gui, "Control")


def test_project_setup_command_uses_combined_label_and_project_setup_icon() -> None:
    resources = cmd_project_setup.CmdProjectSetup().GetResources()
    legacy_resources = cmd_new_project.CmdNewProject().GetResources()

    assert resources["MenuText"] == "New/Project Setup"
    assert str(resources["Pixmap"]).replace("\\", "/").endswith("project_setup.svg")
    assert legacy_resources["MenuText"] == "New/Project Setup"
    assert str(legacy_resources["Pixmap"]).replace("\\", "/").endswith("project_setup.svg")


def test_project_setup_command_creates_project_when_document_has_none() -> None:
    doc = App.newDocument("CRProjectSetupCombinedCommand")
    original_had_control, original_control, control = _install_control()
    try:
        cmd_project_setup.CmdProjectSetup().Activated()

        projects = _project_roots(doc)
        assert len(projects) == 1
        assert control.panels
        assert control.panels[0]._preferred is projects[0]
    finally:
        _restore_control(original_had_control, original_control)
        App.closeDocument(doc.Name)


def test_project_setup_command_reuses_existing_project() -> None:
    doc = App.newDocument("CRProjectSetupCombinedCommandExisting")
    original_had_control, original_control, control = _install_control()
    try:
        cmd_project_setup.CmdProjectSetup().Activated()
        first_project = _project_roots(doc)[0]

        cmd_project_setup.CmdProjectSetup().Activated()

        projects = _project_roots(doc)
        assert projects == [first_project]
        assert control.panels[-1]._preferred is first_project
    finally:
        _restore_control(original_had_control, original_control)
        App.closeDocument(doc.Name)
