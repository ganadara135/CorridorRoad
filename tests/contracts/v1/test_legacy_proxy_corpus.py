"""Legacy proxy restore contract (docsV1/V1_LEGACY_PROXY_MIGRATION_DESIGN.md, phases P0 and P1).

A saved document names each object's Proxy class by module path. If that module cannot be
imported, the object opens without its proxy, and the next save drops the reference for good
(design section 3). These checks keep every legacy proxy module preloaded, and prove on a corpus
written by the legacy classes that opening and saving a document loses no proxy reference, proxy
state or property.
"""

import ast
import tempfile
from pathlib import Path

import FreeCAD as App
import pytest

from freecad.Corridor_Road import install_virtual_path_mappings, virtual_paths
from legacy_proxy_corpus import (
    CANONICAL_OBJECTS,
    CORPUS_DOCUMENTS,
    CORPUS_DIR,
    GUI_DOCUMENT,
    GUI_MANIFEST_PATH,
    LEGACY_PROXY_CLASSES,
    MANIFEST_PATH,
    document_snapshot,
    stored_proxies,
)

OBJECTS_DIR = Path(virtual_paths.__file__).resolve().parent / "objects"

# The GUI runtime: init_gui installs the eager mappings at startup, before any document opens.
# Headless FreeCADCmd stops at the basic level (init.py), where a legacy-prefixed proxy restores
# as a second copy of its module instead of the canonical one.
install_virtual_path_mappings(eager=True)


def _proxy_classes_by_module() -> dict[str, set[str]]:
    """Classes whose __init__ assigns `.Proxy = self`, per module of the objects package."""

    found: dict[str, set[str]] = {}
    for path in sorted(OBJECTS_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for node in ast.parse(source).body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    if ".Proxy = self" in (ast.get_source_segment(source, item) or ""):
                        found.setdefault(path.stem, set()).add(node.name)
    return found


def _manifest() -> dict:
    import json

    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _gui_manifest() -> dict:
    import json

    return json.loads(GUI_MANIFEST_PATH.read_text(encoding="utf-8"))


def _recorded(file_name: str) -> dict:
    return _gui_manifest() if file_name == GUI_DOCUMENT else _manifest()["documents"][file_name]


def test_every_objects_module_with_a_proxy_class_is_preloaded() -> None:
    # Legacy-prefixed documents restore through aliases of preloaded modules only (design 4.2).
    assert set(_proxy_classes_by_module()) == set(virtual_paths._PROXY_OBJECT_MODULES)


def test_the_corpus_covers_every_legacy_proxy_class() -> None:
    expected = {
        (module, name)
        for module, names in _proxy_classes_by_module().items()
        for name in names
        if not name.startswith("ViewProvider") and module != "obj_project"
    }
    assert {(module, name) for module, name, _base in LEGACY_PROXY_CLASSES} == expected

    for file_name, _prefix in CORPUS_DOCUMENTS:
        stored = _manifest()["documents"][file_name]["stored_proxies"]
        assert {(entry["module"].rsplit(".", 1)[1], entry["class"]) for entry in stored.values()} == expected


def test_the_gui_corpus_stores_every_view_provider_and_passed_its_gui_round_trip() -> None:
    # View providers live in GuiDocument.xml, which only a GUI session writes; build_gui ran the
    # reopen-and-save cycles there and recorded the result.
    recorded = _gui_manifest()
    assert recorded["gui_round_trip"] == "pass"
    assert {(entry["module"].rsplit(".", 1)[1], entry["class"]) for entry in recorded["stored_view_providers"].values()} == {
        (module, f"ViewProvider{name}") for module, name, _base in LEGACY_PROXY_CLASSES
    }


@pytest.mark.parametrize("file_name", [name for name, _prefix in CORPUS_DOCUMENTS] + [GUI_DOCUMENT])
def test_a_corpus_document_survives_two_open_and_save_cycles(file_name) -> None:
    recorded = _recorded(file_name)
    path = str(CORPUS_DIR / file_name)
    with tempfile.TemporaryDirectory() as folder:
        for cycle in (1, 2):
            doc = App.openDocument(path)
            try:
                assert document_snapshot(doc) == recorded["objects"], f"cycle {cycle}: restored values differ"
                path = str(Path(folder) / f"cycle{cycle}.FCStd")
                doc.saveAs(path)
            finally:
                App.closeDocument(doc.Name)

            resaved = stored_proxies(path)
            assert resaved.keys() == recorded["stored_proxies"].keys()
            for name, entry in recorded["stored_proxies"].items():
                module_name = entry["module"].rsplit(".", 1)[1]
                # A legacy-prefixed proxy is written back under the canonical path; nothing else changes.
                assert resaved[name] == {
                    "module": f"{CANONICAL_OBJECTS}.{module_name}",
                    "class": entry["class"],
                    "value": entry["value"],
                }, f"cycle {cycle}: {name}"


def test_plan_profile_review_reads_no_legacy_alignment_or_profile() -> None:
    # Decision 4: the viewer reads v1 sources only, so a document holding only legacy objects
    # builds no document preview (the command then shows the demo preview, as for an empty one).
    from freecad.Corridor_Road.v1.commands.cmd_review_plan_profile import build_document_plan_profile_preview

    doc = App.openDocument(str(CORPUS_DIR / "legacy_chain.FCStd"))
    try:
        assert doc.getObject("HorizontalAlignment") is not None
        assert build_document_plan_profile_preview(doc) is None
    finally:
        App.closeDocument(doc.Name)
