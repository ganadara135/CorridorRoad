"""Shared selection-context helpers for CorridorRoad v1 command bridges."""

from __future__ import annotations


def selected_section_target(gui_module, document):
    """Resolve the preferred v1 AppliedSectionSet and station from the current GUI selection."""

    if gui_module is None or document is None:
        return None, None
    try:
        selection = list(gui_module.Selection.getSelection() or [])
    except Exception:
        selection = []
    for obj in selection:
        if obj is None:
            continue
        try:
            if str(getattr(obj, "V1ObjectType", "") or "") == "V1AppliedSectionSet":
                return obj, None
        except Exception:
            pass
        try:
            if str(getattr(getattr(obj, "Proxy", None), "Type", "") or "") == "V1AppliedSectionSet":
                return obj, None
        except Exception:
            pass
    return None, None


def selected_alignment_profile_target(gui_module, document):
    """Resolve preferred alignment/profile objects from the current GUI selection."""

    if gui_module is None or document is None:
        return None, None
    try:
        selection = list(gui_module.Selection.getSelection() or [])
    except Exception:
        selection = []

    preferred_alignment = None
    preferred_profile = None
    for obj in selection:
        if obj is None:
            continue
        proxy_type = ""
        try:
            proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
        except Exception:
            proxy_type = ""
        v1_object_type = str(getattr(obj, "V1ObjectType", "") or "")
        if preferred_alignment is None and proxy_type in {"HorizontalAlignment", "V1Alignment"}:
            preferred_alignment = obj
        if preferred_alignment is None and v1_object_type == "V1Alignment":
            preferred_alignment = obj
        if preferred_profile is None and proxy_type in {"VerticalAlignment", "V1Profile"}:
            preferred_profile = obj
        if preferred_profile is None and v1_object_type == "V1Profile":
            preferred_profile = obj
        if preferred_alignment is None:
            linked_alignment = getattr(obj, "Alignment", None)
            if linked_alignment is not None:
                preferred_alignment = linked_alignment
        if preferred_profile is None:
            linked_profile = getattr(obj, "VerticalAlignment", None)
            if linked_profile is not None:
                preferred_profile = linked_profile
    return preferred_alignment, preferred_profile
