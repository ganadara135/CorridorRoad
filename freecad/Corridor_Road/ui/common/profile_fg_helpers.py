# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

from freecad.Corridor_Road.objects.doc_query import find_first, find_project
from freecad.Corridor_Road.objects.project_links import link_project

PROFILE_BUNDLE_LABEL = "Profiles (Data/EG)"
OLD_PROFILE_BUNDLE_LABEL = "Profiles (EG/FG)"


def normalize_profile_bundle_label(bundle):
    if bundle is None:
        return
    try:
        if str(getattr(bundle, "Label", "")) == OLD_PROFILE_BUNDLE_LABEL:
            bundle.Label = PROFILE_BUNDLE_LABEL
    except Exception:
        pass


def find_stationing(doc):
    return find_first(doc, name_prefixes=("Stationing",))


def find_profile_bundle(doc):
    b = find_first(doc, name_prefixes=("ProfileBundle",))
    normalize_profile_bundle_label(b)
    return b


def find_vertical_alignment(doc):
    return find_first(doc, name_prefixes=("VerticalAlignment",))


def find_fg_display(doc):
    fg = find_first(doc, proxy_type="FGDisplay")
    if fg is not None:
        return fg
    # Label fallback for legacy objects
    return find_first(doc, predicate=lambda o: str(getattr(o, "Label", "")) == "Finished Grade (FG)")


def ensure_fg_display(doc, va):
    fg = find_fg_display(doc)
    if fg is not None:
        try:
            if va is not None and getattr(fg, "SourceVA", None) is None:
                fg.SourceVA = va
        except Exception:
            pass
        try:
            prj = find_project(doc)
            if prj is not None:
                link_project(prj, adopt_extra=[fg, va])
        except Exception:
            pass
        return fg

    fg = doc.addObject("Part::FeaturePython", "FinishedGradeFG")
    from freecad.Corridor_Road.objects.obj_fg_display import FGDisplay, ViewProviderFGDisplay

    FGDisplay(fg)
    if getattr(fg, "ViewObject", None) is not None:
        ViewProviderFGDisplay(fg.ViewObject)
    fg.Label = "Finished Grade (FG)"

    try:
        fg.SourceVA = va
    except Exception:
        pass
    try:
        fg.ShowWire = True
    except Exception:
        pass

    fg.touch()
    doc.recompute()
    try:
        prj = find_project(doc)
        if prj is not None:
            link_project(prj, adopt_extra=[fg, va])
    except Exception:
        pass
    return fg
