# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

def _iter_objects(doc):
    if doc is None:
        return []
    try:
        return list(getattr(doc, "Objects", []) or [])
    except Exception:
        return []


def is_proxy_type(obj, type_name: str) -> bool:
    if obj is None:
        return False
    try:
        return bool(getattr(obj, "Proxy", None)) and str(getattr(obj.Proxy, "Type", "")) == str(type_name)
    except Exception:
        return False


def is_name_prefixed(obj, prefixes) -> bool:
    if obj is None:
        return False
    if isinstance(prefixes, str):
        prefixes = (prefixes,)
    try:
        nm = str(getattr(obj, "Name", "") or "")
    except Exception:
        return False
    return any(nm.startswith(str(p)) for p in (prefixes or ()))


def find_first(doc, proxy_type: str = None, name_prefixes=None, predicate=None):
    objs = _iter_objects(doc)
    if proxy_type:
        for o in objs:
            if is_proxy_type(o, proxy_type):
                if predicate is None or bool(predicate(o)):
                    return o
    if name_prefixes:
        for o in objs:
            if is_name_prefixed(o, name_prefixes):
                if predicate is None or bool(predicate(o)):
                    return o
    return None


def find_all(doc, proxy_type: str = None, name_prefixes=None, predicate=None):
    out = []
    seen = set()
    objs = _iter_objects(doc)
    if proxy_type:
        for o in objs:
            if is_proxy_type(o, proxy_type):
                if predicate is None or bool(predicate(o)):
                    out.append(o)
                    seen.add(getattr(o, "Name", id(o)))
    if name_prefixes:
        for o in objs:
            key = getattr(o, "Name", id(o))
            if key in seen:
                continue
            if is_name_prefixed(o, name_prefixes):
                if predicate is None or bool(predicate(o)):
                    out.append(o)
                    seen.add(key)
    return out


def find_project(doc):
    return find_first(doc, name_prefixes=("CorridorRoadProject",))
