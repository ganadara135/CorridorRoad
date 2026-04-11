# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

from freecad.Corridor_Road.objects.obj_project import get_coordinate_setup, get_coordinate_workflow


def get_epsg_status(doc_or_obj=None, cst=None):
    if cst is None:
        cst = get_coordinate_setup(doc_or_obj)
    epsg = str(cst.get("CRSEPSG", "") or "").strip()
    status = str(cst.get("CoordSetupStatus", "Uninitialized") or "Uninitialized")
    return epsg, status


def coord_hint_text(doc_or_obj):
    cst = get_coordinate_setup(doc_or_obj)
    epsg, status = get_epsg_status(cst=cst)
    workflow = get_coordinate_workflow(doc_or_obj)
    rot = float(cst.get("NorthRotationDeg", 0.0) or 0.0)
    e0 = float(cst.get("ProjectOriginE", 0.0) or 0.0)
    n0 = float(cst.get("ProjectOriginN", 0.0) or 0.0)
    x0 = float(cst.get("LocalOriginX", 0.0) or 0.0)
    y0 = float(cst.get("LocalOriginY", 0.0) or 0.0)
    return (
        f"CRS: {epsg if epsg else 'N/A'} / Status: {status} / "
        f"Workflow: {workflow} / "
        f"North rot: {rot:.3f} deg / World origin (E/N): {e0:.3f}, {n0:.3f} / "
        f"Local origin (X/Y): {x0:.3f}, {y0:.3f}"
    )


def should_default_world_mode(doc_or_obj):
    cst = get_coordinate_setup(doc_or_obj)
    workflow = get_coordinate_workflow(doc_or_obj)
    if bool(cst.get("AutoApplyCoordinateRecommendations", True)):
        if workflow == "World-first":
            return True
        if workflow == "Local-first":
            return False
    epsg, status = get_epsg_status(cst=cst)
    return (status != "Uninitialized") or bool(epsg)
