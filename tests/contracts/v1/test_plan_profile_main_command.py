from freecad.Corridor_Road.commands.cmd_review_plan_profile import (
    CmdReviewPlanProfile,
    run_plan_profile_review_command,
)


class _Console:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def PrintWarning(self, text: str) -> None:
        self.warnings.append(str(text))

    def PrintError(self, text: str) -> None:
        self.errors.append(str(text))


class _App:
    def __init__(self) -> None:
        self.Console = _Console()


def test_run_plan_profile_review_command_opens_the_v1_viewer() -> None:
    app = _App()
    calls: list[str] = []

    path = run_plan_profile_review_command(app_module=app, run_v1_viewer=lambda: calls.append("v1"))

    assert path == "v1"
    assert calls == ["v1"]
    assert app.Console.errors == []


def test_review_plan_profile_command_uses_plan_profile_review_icon() -> None:
    resources = CmdReviewPlanProfile().GetResources()

    assert str(resources["Pixmap"]).replace("\\", "/").endswith("plan_profile_review.svg")


def test_a_v1_viewer_failure_is_reported_and_opens_no_v0_editor() -> None:
    # The v0 alignment/profile editors this used to open create legacy proxy objects.
    app = _App()

    def _run_v1() -> None:
        raise RuntimeError("simulated v1 failure")

    path = run_plan_profile_review_command(app_module=app, run_v1_viewer=_run_v1)

    assert path == "error"
    assert app.Console.errors == ["Plan/Profile review was not opened: simulated v1 failure\n"]
