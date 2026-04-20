# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor FCStd restore smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_fcstd_restore.py
"""

import os
import uuid
import zipfile

import FreeCAD as App

from freecad.Corridor_Road import install_virtual_path_mappings
from freecad.Corridor_Road.corridor_compat import (
    CORRIDOR_CHILD_LINK_PROPERTY,
    CORRIDOR_PROJECT_PROPERTY,
    CORRIDOR_PROXY_TYPE,
)
from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_project import (
    CorridorRoadProject,
    assign_project_corridor,
    ensure_corridor_object,
    resolve_project_corridor,
)


LEGACY_PROXY_MODULE = "objects.obj_corridor_loft"
CANONICAL_PROXY_MODULE = "freecad.Corridor_Road.objects.obj_corridor_loft"


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _close_document(doc):
    if doc is None:
        return
    try:
        App.closeDocument(str(doc.Name))
    except Exception:
        pass


def _open_document(path):
    try:
        return App.openDocument(path, True)
    except TypeError:
        try:
            return App.openDocument(path, hidden=True)
        except TypeError:
            return App.openDocument(path)


def _document_xml_text(path):
    with zipfile.ZipFile(path, "r") as zf:
        return zf.read("Document.xml").decode("utf-8", errors="ignore")


def _make_project_with_corridor(doc_name):
    doc = App.newDocument(doc_name)

    prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(prj)

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)

    compat_child = doc.addObject("App::FeaturePython", "CorridorCompatChild")
    if not hasattr(compat_child, CORRIDOR_CHILD_LINK_PROPERTY):
        compat_child.addProperty("App::PropertyLink", CORRIDOR_CHILD_LINK_PROPERTY, "Smoke", "Corridor link")
    setattr(compat_child, CORRIDOR_CHILD_LINK_PROPERTY, cor)

    assigned = assign_project_corridor(prj, cor)
    _assert(assigned is cor, "Project should accept the created corridor object")

    doc.recompute()
    return doc, prj, cor


def _validate_reopened_document(doc):
    project = next(
        (o for o in list(getattr(doc, "Objects", []) or []) if str(getattr(getattr(o, "Proxy", None), "Type", "") or "") == "CorridorRoadProject"),
        None,
    )
    _assert(project is not None, "Reopened document should contain a CorridorRoadProject proxy")
    _assert(hasattr(project, CORRIDOR_PROJECT_PROPERTY), "Reopened project should retain the canonical corridor link property")
    _assert(not hasattr(project, "CorridorLoft"), "Reopened project should not recreate the legacy hidden CorridorLoft property")

    corridor = resolve_project_corridor(project)
    _assert(corridor is not None, "Reopened project should resolve a corridor object")
    _assert(ensure_corridor_object(corridor) is corridor, "Reopened corridor should still pass compatibility corridor resolution")
    _assert(str(getattr(getattr(corridor, "Proxy", None), "Type", "") or "") == CORRIDOR_PROXY_TYPE, "Reopened corridor proxy type should stay CorridorLoft until proxy retirement")
    _assert(getattr(project, CORRIDOR_PROJECT_PROPERTY, None) is corridor, "Reopened project should keep the canonical corridor link synchronized")

    child_links = [o for o in list(getattr(doc, "Objects", []) or []) if getattr(o, CORRIDOR_CHILD_LINK_PROPERTY, None) is corridor]
    _assert(child_links, "Reopened document should retain child objects linked through ParentCorridorLoft")


def _roundtrip_fcstd(temp_root, doc_name, fcstd_name, proxy_module_path):
    doc = None
    reopened = None
    out_path = os.path.join(temp_root, fcstd_name)
    original_module = CorridorLoft.__module__
    try:
        CorridorLoft.__module__ = proxy_module_path
        doc, _project, _corridor = _make_project_with_corridor(doc_name)
        doc.saveAs(out_path)
    finally:
        CorridorLoft.__module__ = original_module
        _close_document(doc)

    xml_text = _document_xml_text(out_path)
    _assert(proxy_module_path in xml_text, f"Saved FCStd should persist proxy module path '{proxy_module_path}'")

    reopened = _open_document(out_path)
    try:
        _validate_reopened_document(reopened)
    finally:
        _close_document(reopened)


def run():
    install_virtual_path_mappings(eager=True)

    temp_root = os.path.join(os.getcwd(), "tests", "regression")
    token = uuid.uuid4().hex
    canonical_name = f"corridor_restore_canonical_{token}.FCStd"
    legacy_name = f"corridor_restore_legacy_{token}.FCStd"
    try:
        _roundtrip_fcstd(temp_root, "CRCorridorRestoreCanonical", canonical_name, CANONICAL_PROXY_MODULE)
        _roundtrip_fcstd(temp_root, "CRCorridorRestoreLegacy", legacy_name, LEGACY_PROXY_MODULE)
        print("[PASS] Corridor FCStd restore smoke test completed.")
    finally:
        for name in (canonical_name, legacy_name):
            try:
                os.remove(os.path.join(temp_root, name))
            except Exception:
                pass


if __name__ == "__main__":
    run()
