from freecad.Corridor_Road.v1.ui.common import clear_ui_context, get_ui_context, run_legacy_command


class _FakeControl:
    def __init__(self):
        self.closed = False

    def closeDialog(self):
        self.closed = True


class _FakeGui:
    def __init__(self):
        self.Control = _FakeControl()
        self.Selection = _FakeSelection()
        self.ran = []

    def runCommand(self, command_name: str, arg: int):
        self.ran.append((command_name, arg))


class _FakeSelection:
    def __init__(self):
        self.cleared = False
        self.added = []

    def clearSelection(self):
        self.cleared = True

    def addSelection(self, *args):
        self.added.append(args)


class _FakeDocument:
    def __init__(self, name: str):
        self.Name = name


class _FakeObject:
    def __init__(self, document_name: str, object_name: str):
        self.Document = _FakeDocument(document_name)
        self.Name = object_name


def test_run_legacy_command_closes_dialog_and_runs_command() -> None:
    clear_ui_context()
    gui = _FakeGui()
    obj = _FakeObject("DemoDoc", "HorizontalAlignment001")

    success, message = run_legacy_command(
        "CorridorRoad_EditAlignment",
        gui_module=gui,
        objects_to_select=[obj],
        context_payload={"source": "test", "station": 10.0},
    )

    assert success is True
    assert "CorridorRoad_EditAlignment" in message
    assert gui.Control.closed is True
    assert gui.ran == [("CorridorRoad_EditAlignment", 0)]
    assert gui.Selection.cleared is True
    assert gui.Selection.added == [(obj,)]
    assert get_ui_context()["source"] == "test"
    assert get_ui_context()["station"] == 10.0


def test_run_legacy_command_reports_missing_gui() -> None:
    class _MissingGui:
        pass

    success, message = run_legacy_command("CorridorRoad_EditAlignment", gui_module=_MissingGui())

    assert success is False
    assert "Could not open" in message
