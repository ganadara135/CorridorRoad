from freecad.Corridor_Road.commands.cmd_generate_cut_fill_calc import (
    run_earthwork_review_command,
)


class _Console:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def PrintWarning(self, text: str) -> None:
        self.messages.append(str(text))


class _App:
    def __init__(self) -> None:
        self.Console = _Console()


def test_run_earthwork_review_command_prefers_v1() -> None:
    app = _App()
    calls: list[str] = []

    def _run_v1() -> None:
        calls.append("v1")

    def _open_v0() -> None:
        calls.append("v0")

    path = run_earthwork_review_command(
        app_module=app,
        gui_module=None,
        run_v1_viewer=_run_v1,
        open_existing_v0_panel=_open_v0,
    )

    assert path == "v1"
    assert calls == ["v1"]
    assert app.Console.messages == []


def test_run_earthwork_review_command_falls_back_to_existing_v0() -> None:
    app = _App()
    calls: list[str] = []

    def _run_v1() -> None:
        calls.append("v1")
        raise RuntimeError("simulated v1 failure")

    def _open_v0() -> None:
        calls.append("v0")

    path = run_earthwork_review_command(
        app_module=app,
        gui_module=None,
        run_v1_viewer=_run_v1,
        open_existing_v0_panel=_open_v0,
    )

    assert path == "v0"
    assert calls == ["v1", "v0"]
    assert app.Console.messages
    assert "existing v0 panel" in app.Console.messages[0]
