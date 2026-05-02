from freecad.Corridor_Road.commands.cmd_import_pointcloud_tin import (
    run_pointcloud_tin_command,
)


class _Console:
    def __init__(self):
        self.warnings = []

    def PrintWarning(self, message):
        self.warnings.append(message)


class _App:
    def __init__(self):
        self.Console = _Console()


def test_run_pointcloud_tin_command_prefers_v1() -> None:
    calls = []

    path = run_pointcloud_tin_command(
        app_module=_App(),
        gui_module=None,
        run_v1_review=lambda extra_context=None: calls.append(("v1", extra_context)),
        select_csv_path=lambda: "",
    )

    assert path == "v1"
    assert calls == [("v1", None)]


def test_run_pointcloud_tin_command_passes_selected_csv_context() -> None:
    calls = []
    csv_path = r"tests\samples\pointcloud_utm_realistic_hilly.csv"

    path = run_pointcloud_tin_command(
        app_module=_App(),
        gui_module=None,
        run_v1_review=lambda extra_context=None: calls.append(extra_context),
        select_csv_path=lambda: csv_path,
    )

    assert path == "v1"
    assert calls[0]["csv_path"] == csv_path
    assert calls[0]["surface_id"] == "tin:pointcloud_utm_realistic_hilly"


def test_run_pointcloud_tin_command_falls_back_to_placeholder() -> None:
    app = _App()

    def _fail():
        raise RuntimeError("boom")

    path = run_pointcloud_tin_command(
        app_module=app,
        gui_module=None,
        run_v1_review=_fail,
        select_csv_path=lambda: "",
    )

    assert path == "fallback"
    assert "v1 TIN review unavailable" in app.Console.warnings[0]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] PointCloud TIN main command contract tests completed.")
