# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, ensure_project_properties, ensure_project_tree, find_project


def _iter_unique(objs):
    out = []
    seen = set()
    for o in list(objs or []):
        if o is None:
            continue
        key = getattr(o, "Name", None) or str(id(o))
        if key in seen:
            continue
        seen.add(key)
        out.append(o)
    return out


def resolve_project(doc_or_project):
    if doc_or_project is None:
        return None
    if hasattr(doc_or_project, "Objects"):
        return find_project(doc_or_project)
    return doc_or_project


def link_project(project_obj, links=None, links_if_empty=None, adopt_extra=None):
    prj = resolve_project(project_obj)
    if prj is None:
        return None

    ensure_project_properties(prj)
    ensure_project_tree(prj, include_references=False)
    linked = []

    for prop, obj in dict(links or {}).items():
        if obj is None or (not hasattr(prj, prop)):
            continue
        if str(prop) == "Alignment":
            try:
                pt = str(prj.getTypeIdOfProperty("Alignment") or "")
            except Exception:
                pt = ""
            if "Hidden" not in pt:
                # Prevent tree duplication in environments lacking PropertyLinkHidden migration.
                continue
        try:
            setattr(prj, prop, obj)
            linked.append(obj)
        except Exception:
            pass

    for prop, obj in dict(links_if_empty or {}).items():
        if obj is None or (not hasattr(prj, prop)):
            continue
        if str(prop) == "Alignment":
            try:
                pt = str(prj.getTypeIdOfProperty("Alignment") or "")
            except Exception:
                pt = ""
            if "Hidden" not in pt:
                continue
        try:
            if getattr(prj, prop, None) is None:
                setattr(prj, prop, obj)
                linked.append(obj)
        except Exception:
            pass

    for child in _iter_unique(list(linked) + list(adopt_extra or [])):
        try:
            CorridorRoadProject.adopt(prj, child)
        except Exception:
            pass
    return prj
