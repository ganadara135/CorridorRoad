from objects.obj_project import CorridorRoadProject, ensure_project_properties, find_project


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
    linked = []

    for prop, obj in dict(links or {}).items():
        if obj is None or (not hasattr(prj, prop)):
            continue
        try:
            setattr(prj, prop, obj)
            linked.append(obj)
        except Exception:
            pass

    for prop, obj in dict(links_if_empty or {}).items():
        if obj is None or (not hasattr(prj, prop)):
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
