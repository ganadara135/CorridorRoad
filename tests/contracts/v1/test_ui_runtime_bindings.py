import ast
import importlib.util
from pathlib import Path

import FreeCAD as App  # noqa: F401 - FreeCAD must be importable before the workbench modules

import freecad.Corridor_Road.v1.commands.cmd_build_corridor  # noqa: F401 - binds the Build Parametric panel
import freecad.Corridor_Road.v1.commands.cmd_edit_tin  # noqa: F401 - binds the TIN editor panel
import freecad.Corridor_Road.v1.commands.cmd_project_setup  # noqa: F401 - binds the Project Setup panel
from freecad.Corridor_Road.v1.ui.editors import project_setup_editor, tin_editor
from freecad.Corridor_Road.v1.ui.viewers import build_corridor_view

UI_ROOT = Path(build_corridor_view.__file__).resolve().parents[1]
UI_PACKAGE = "freecad.Corridor_Road.v1.ui"


def _relative_imports(path: Path):
    package = ".".join([UI_PACKAGE, *path.relative_to(UI_ROOT).parent.parts]).rstrip(".")
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.level:
            base = package.rsplit(".", node.level - 1)[0] if node.level > 1 else package
            yield node.lineno, f"{base}.{node.module}" if node.module else base


def test_every_relative_import_in_the_ui_package_resolves() -> None:
    # Function-level imports run only when a button is pressed; a module path that does not exist
    # (".cmd_review_tin" inside ui/editors) fails there and nowhere else.
    missing = [
        f"{path.relative_to(UI_ROOT)}:{line} {module}"
        for path in sorted(UI_ROOT.rglob("*.py"))
        for line, module in _relative_imports(path)
        if importlib.util.find_spec(module) is None
    ]
    assert not missing, missing


def test_build_parametric_structure_output_button_uses_the_bound_command(monkeypatch) -> None:
    opened = []
    monkeypatch.setattr(build_corridor_view, "open_structure_output_panel", lambda *, document=None: opened.append(document))
    panel = build_corridor_view.V1BuildCorridorTaskPanel.__new__(build_corridor_view.V1BuildCorridorTaskPanel)
    panel.document = "document"
    panel._summary = type("Summary", (), {"setPlainText": lambda self, text: None})()

    assert panel._open_structure_output_panel() is True
    assert opened == ["document"]


def test_command_modules_bind_the_ui_placeholders() -> None:
    assert callable(build_corridor_view.open_structure_output_panel)
    assert callable(tin_editor.show_v1_tin_review)
    for name in ("apply_v1_project_setup", "list_corridorroad_projects", "project_setup_draft_from_project"):
        assert callable(getattr(project_setup_editor, name)), name
