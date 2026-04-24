from freecad.Corridor_Road.commands.cmd_review_plan_profile import (
    run_plan_profile_review_command,
)


class _Console:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def PrintWarning(self, text: str) -> None:
        self.messages.append(str(text))


class _App:
    def __init__(self) -> None:
        self.Console = _Console()


def test_run_plan_profile_review_command_prefers_v1() -> None:
    app = _App()
    calls: list[str] = []

    def _run_v1() -> None:
        calls.append("v1")

    path = run_plan_profile_review_command(
        app_module=app,
        gui_module=None,
        run_v1_viewer=_run_v1,
        resolve_targets=lambda: (None, None),
        open_existing_v0_alignment_editor=lambda: calls.append("v0_alignment"),
        open_existing_v0_profile_editor=lambda: calls.append("v0_profile"),
    )

    assert path == "v1"
    assert calls == ["v1"]
    assert app.Console.messages == []


def test_run_plan_profile_review_command_falls_back_to_profile_editor() -> None:
    app = _App()
    calls: list[str] = []
    profile_object = object()

    def _run_v1() -> None:
        calls.append("v1")
        raise RuntimeError("simulated v1 failure")

    path = run_plan_profile_review_command(
        app_module=app,
        gui_module=None,
        run_v1_viewer=_run_v1,
        resolve_targets=lambda: (None, profile_object),
        open_existing_v0_alignment_editor=lambda: calls.append("v0_alignment"),
        open_existing_v0_profile_editor=lambda: calls.append("v0_profile"),
    )

    assert path == "v0_profile"
    assert calls == ["v1", "v0_profile"]
    assert app.Console.messages
    assert "existing v0 profile editor" in app.Console.messages[0]


def test_run_plan_profile_review_command_falls_back_to_alignment_editor() -> None:
    app = _App()
    calls: list[str] = []

    def _run_v1() -> None:
        calls.append("v1")
        raise RuntimeError("simulated v1 failure")

    path = run_plan_profile_review_command(
        app_module=app,
        gui_module=None,
        run_v1_viewer=_run_v1,
        resolve_targets=lambda: (None, None),
        open_existing_v0_alignment_editor=lambda: calls.append("v0_alignment"),
        open_existing_v0_profile_editor=lambda: calls.append("v0_profile"),
    )

    assert path == "v0_alignment"
    assert calls == ["v1", "v0_alignment"]
    assert app.Console.messages
    assert "existing v0 alignment editor" in app.Console.messages[0]
