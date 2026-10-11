"""Retired legacy commands stay retired (docsV1/V1_LEGACY_PROXY_MIGRATION_DESIGN.md, phase P2).

The hidden legacy editors opened v0 panels that create legacy proxy objects (HorizontalAlignment,
RegionPlan, TypicalSectionTemplate). Once those classes become restore-only stubs, such an object
could not compute, so no module may register these command ids again.
"""

import ast
from pathlib import Path

import freecad.Corridor_Road as package

PACKAGE_ROOT = Path(package.__file__).resolve().parent
RETIRED_COMMAND_IDS = {
    "CorridorRoad_EditAlignment",
    "CorridorRoad_EditRegions",
    "CorridorRoad_EditTypicalSection",
    # read-only, but kept the v0 alignment panel alive; its v1 successor is CorridorRoad_V1ReviewPlanProfile
    "CorridorRoad_ReviewAlignment",
}


def _registered_command_ids() -> set[str]:
    ids = set()
    for path in PACKAGE_ROOT.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "addCommand"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                ids.add(str(node.args[0].value))
    return ids


def test_retired_legacy_editor_commands_are_not_registered() -> None:
    assert not (RETIRED_COMMAND_IDS & _registered_command_ids())


def test_the_scan_sees_the_commands_that_are_registered() -> None:
    # Guards the scan itself: a refactor that hides addCommand calls would make the test above vacuous.
    assert {"CorridorRoad_ProjectSetup", "CorridorRoad_ReviewPlanProfile"} <= _registered_command_ids()
