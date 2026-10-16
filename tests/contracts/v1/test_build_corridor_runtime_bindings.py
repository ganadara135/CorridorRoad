"""The Build Parametric panel receives its collaborators from the command module's globals.

The panel module declares each one as a `name = None` placeholder, and
`configure_build_corridor_task_panel_runtime(globals())` replaces them. A collaborator moved out of
the command (GR-7) must still be importable from it, or the panel calls None.
"""

import re
from pathlib import Path

import freecad.Corridor_Road.v1.commands.cmd_build_corridor as build_corridor_command
import freecad.Corridor_Road.v1.ui.viewers.build_corridor_view as build_corridor_view

VIEW_SOURCE = Path(build_corridor_view.__file__).read_text(encoding="utf-8")


def test_every_panel_placeholder_is_bound_from_the_command() -> None:
    placeholders = re.findall(r"^(\w+) = None$", VIEW_SOURCE, re.M)

    assert placeholders
    assert [name for name in placeholders if not hasattr(build_corridor_command, name)] == []
    assert [name for name in placeholders if getattr(build_corridor_view, name) is None] == []
