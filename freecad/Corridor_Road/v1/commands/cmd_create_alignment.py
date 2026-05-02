"""v1 alignment source creation command."""

from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None

from ...objects.obj_project import (
    CorridorRoadProject,
    ensure_project_properties,
    ensure_project_tree,
    find_project,
)
from ...objects.project_links import link_project
from ..objects.obj_alignment import create_sample_v1_alignment


def create_v1_sample_alignment(*, document=None, project=None):
    """Create one sample v1 alignment and route it into the v1 project tree."""

    doc = document
    if doc is None and App is not None:
        doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        raise RuntimeError("No active document.")

    prj = project or find_project(doc)
    if prj is None:
        try:
            prj = doc.addObject("App::DocumentObjectGroupPython", "CorridorRoadProject")
        except Exception:
            prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        CorridorRoadProject(prj)
        prj.Label = "CorridorRoad Project"

    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    alignment = create_sample_v1_alignment(doc, project=prj, label="Main Alignment")
    link_project(prj, adopt_extra=[alignment])
    try:
        doc.recompute()
    except Exception:
        pass
    return alignment
