"""The proxy preload list names every proxy module of the objects package.

A saved document names each object's proxy class by module path. Documents saved under a legacy
module prefix (`CorridorRoad.objects...`, `objects...`) restore only through the aliases that
virtual_paths installs for preloaded modules, so a proxy module missing from the list would open
without its proxy, and the next save would drop it for good.
"""

import ast
from pathlib import Path

from freecad.Corridor_Road import virtual_paths

OBJECTS_DIR = Path(virtual_paths.__file__).resolve().parent / "objects"


def _modules_with_proxy_classes() -> set[str]:
    found = set()
    for path in sorted(OBJECTS_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for node in ast.parse(source).body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    if ".Proxy = self" in (ast.get_source_segment(source, item) or ""):
                        found.add(path.stem)
    return found


def test_every_objects_module_with_a_proxy_class_is_preloaded() -> None:
    assert _modules_with_proxy_classes() == set(virtual_paths._PROXY_OBJECT_MODULES) == {"obj_project"}
