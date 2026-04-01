# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
CorridorRoad fixed-tree smoke test (headless-friendly).

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_tree_schema.py
or inside Python console:
    exec(open("tests/regression/smoke_tree_schema.py", "r", encoding="utf-8").read())
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_project import (
    ALN_REF_NAME_PROP,
    ALN_REF_PROP,
    ALIGNMENT_ASSEMBLY,
    ALIGNMENT_CORRIDOR,
    ALIGNMENT_HORIZONTAL,
    ALIGNMENT_ROOT,
    ALIGNMENT_SECTIONS,
    ALIGNMENT_STATIONING,
    ALIGNMENT_VERTICAL,
    TREE_ANALYSIS,
    TREE_INPUTS,
    TREE_INPUTS_STRUCTURES,
    TREE_INPUTS_SURVEY,
    TREE_INPUTS_TERRAINS,
    TREE_KEY_PROP,
    TREE_REFERENCES,
    TREE_SURFACES,
    CorridorRoadProject,
    ensure_project_tree,
)
from freecad.Corridor_Road.objects.project_links import link_project


def _group(obj):
    return list(getattr(obj, "Group", []) or [])


def _key(obj):
    return str(getattr(obj, TREE_KEY_PROP, "") or "")


def _iter_tree_folders(root):
    out = []
    seen = set()

    def walk(node):
        for ch in _group(node):
            nm = str(getattr(ch, "Name", "") or "")
            if nm in seen:
                continue
            seen.add(nm)
            if _key(ch):
                out.append(ch)
                walk(ch)

    walk(root)
    return out


def _find_folder(root, key):
    for f in _iter_tree_folders(root):
        if _key(f) == key:
            return f
    return None


def _owners(root, child):
    out = []
    all_owners = [root] + _iter_tree_folders(root)
    for o in all_owners:
        if child in _group(o):
            out.append(o)
    return out


def _owner_key(root, child):
    owners = _owners(root, child)
    if not owners:
        return ""
    # In tree policy, object should be under one folder owner.
    if len(owners) > 1:
        keys = [str(_key(o) or "project_root") for o in owners]
        raise Exception(f"Multiple owners for {child.Name}: {keys}")
    o = owners[0]
    return _key(o) or "project_root"


def _owner_folder(root, child):
    owners = _owners(root, child)
    if not owners:
        return None
    if len(owners) > 1:
        keys = [str(_key(o) or "project_root") for o in owners]
        raise Exception(f"Multiple owners for {child.Name}: {keys}")
    return owners[0]


def _parent_folder(root, child_folder):
    if child_folder is None:
        return None
    for o in [root] + _iter_tree_folders(root):
        if child_folder in _group(o):
            return o
    return None


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _add_alignment_link(obj, alignment):
    if not hasattr(obj, "Alignment"):
        obj.addProperty("App::PropertyLink", "Alignment", "Smoke", "Alignment link")
    obj.Alignment = alignment


def run():
    doc = App.newDocument("CRSmokeTree")

    prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(prj)
    prj.Label = "CorridorRoad Project"
    ensure_project_tree(prj, include_references=False)

    # Base fixed folders.
    for k in (TREE_INPUTS, TREE_INPUTS_TERRAINS, TREE_INPUTS_SURVEY, TREE_INPUTS_STRUCTURES, TREE_SURFACES, TREE_ANALYSIS):
        _assert(_find_folder(prj, k) is not None, f"Missing tree folder: {k}")

    # Alignment branch + alignment-related objects.
    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    aln.Label = "MainLine"
    link_project(prj, links={"Alignment": aln}, adopt_extra=[aln])
    aln2 = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    aln2.Label = "MainLine"
    link_project(prj, adopt_extra=[aln2])

    st = doc.addObject("Part::FeaturePython", "Stationing")
    _add_alignment_link(st, aln)
    link_project(prj, links={"Stationing": st}, adopt_extra=[st])

    va = doc.addObject("Part::FeaturePython", "VerticalAlignment")
    pb = doc.addObject("Part::FeaturePython", "ProfileBundle")
    fg = doc.addObject("Part::FeaturePython", "FinishedGradeFG")
    if not hasattr(pb, "Stationing"):
        pb.addProperty("App::PropertyLink", "Stationing", "Smoke", "Stationing link")
    if not hasattr(pb, "VerticalAlignment"):
        pb.addProperty("App::PropertyLink", "VerticalAlignment", "Smoke", "VA link")
    pb.Stationing = st
    pb.VerticalAlignment = va
    if not hasattr(fg, "SourceVA"):
        fg.addProperty("App::PropertyLink", "SourceVA", "Smoke", "VA link")
    fg.SourceVA = va
    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    if not hasattr(sec, "SourceCenterlineDisplay"):
        sec.addProperty("App::PropertyLink", "SourceCenterlineDisplay", "Smoke", "Display link")
    if not hasattr(sec, "AssemblyTemplate"):
        sec.addProperty("App::PropertyLink", "AssemblyTemplate", "Smoke", "Assembly link")
    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    if not hasattr(disp, "Alignment"):
        disp.addProperty("App::PropertyLink", "Alignment", "Smoke", "Alignment link")
    if not hasattr(disp, "VerticalAlignment"):
        disp.addProperty("App::PropertyLink", "VerticalAlignment", "Smoke", "VA link")
    disp.Alignment = aln
    disp.VerticalAlignment = va
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    if not hasattr(cor, "SourceSectionSet"):
        cor.addProperty("App::PropertyLink", "SourceSectionSet", "Smoke", "Section set link")
    cor.SourceSectionSet = sec
    link_project(prj, adopt_extra=[va, pb, fg, asm, sec, cor, disp])

    _assert(_find_folder(prj, ALIGNMENT_ROOT) is not None, "Missing alignment root")
    for k in (ALIGNMENT_HORIZONTAL, ALIGNMENT_STATIONING, ALIGNMENT_VERTICAL, ALIGNMENT_ASSEMBLY, ALIGNMENT_SECTIONS, ALIGNMENT_CORRIDOR):
        _assert(_find_folder(prj, k) is not None, f"Missing alignment subfolder: {k}")
    roots = [f for f in _iter_tree_folders(prj) if _key(f) == ALIGNMENT_ROOT]
    _assert(len(roots) >= 2, "Expected at least two alignment roots")
    aln_root_1 = None
    aln_root_2 = None
    for r in roots:
        if str(getattr(r, ALN_REF_NAME_PROP, "") or "") == str(getattr(aln, "Name", "") or ""):
            aln_root_1 = r
        if str(getattr(r, ALN_REF_NAME_PROP, "") or "") == str(getattr(aln2, "Name", "") or ""):
            aln_root_2 = r
    _assert(aln_root_1 is not None, "Missing alignment root for first alignment")
    _assert(aln_root_2 is not None, "Missing alignment root for second alignment")
    _assert(aln_root_1 != aln_root_2, "Two alignments were mapped to the same root")
    _assert(str(getattr(aln_root_1, "Label", "")) != str(getattr(aln_root_2, "Label", "")), "Duplicate alignment root labels")
    _assert(getattr(aln_root_1, ALN_REF_PROP, None) is None, "Alignment root should not keep legacy direct link")
    _assert(getattr(aln_root_2, ALN_REF_PROP, None) is None, "Alignment root should not keep legacy direct link")

    # Surface / analysis / input / optional references.
    terr = doc.addObject("App::FeaturePython", "ExistingTerrain")
    terr.Label = "Existing Terrain"
    link_project(prj, links={"Terrain": terr}, adopt_extra=[terr])

    dgs = doc.addObject("App::FeaturePython", "DesignGradingSurface")
    dtm = doc.addObject("App::FeaturePython", "DesignTerrain")
    cfc = doc.addObject("App::FeaturePython", "CutFillCalc")
    link_project(
        prj,
        links={"DesignGradingSurface": dgs, "DesignTerrain": dtm, "CutFillCalc": cfc},
        adopt_extra=[dgs, dtm, cfc],
    )

    misc = doc.addObject("App::FeaturePython", "MiscObject")
    link_project(prj, adopt_extra=[misc])
    _assert(_find_folder(prj, TREE_REFERENCES) is not None, "Missing optional references folder")
    ext = doc.addObject("App::FeaturePython", "ExternalSurface")
    ext.Label = "External Surface"
    topo = doc.addObject("App::FeaturePython", "TopoSurface")
    topo.Label = "Topo Surface"
    link_project(prj, adopt_extra=[ext, topo])
    va_unlinked = doc.addObject("Part::FeaturePython", "VerticalAlignmentLoose")
    link_project(prj, adopt_extra=[va_unlinked])

    expected = {
        aln: ALIGNMENT_HORIZONTAL,
        aln2: ALIGNMENT_HORIZONTAL,
        st: ALIGNMENT_STATIONING,
        va: ALIGNMENT_VERTICAL,
        pb: ALIGNMENT_VERTICAL,
        fg: ALIGNMENT_VERTICAL,
        asm: ALIGNMENT_ASSEMBLY,
        sec: ALIGNMENT_SECTIONS,
        cor: ALIGNMENT_CORRIDOR,
        terr: TREE_INPUTS_TERRAINS,
        dgs: TREE_SURFACES,
        dtm: TREE_SURFACES,
        cfc: TREE_ANALYSIS,
        misc: TREE_REFERENCES,
        ext: TREE_REFERENCES,
        topo: TREE_INPUTS_TERRAINS,
        va_unlinked: ALIGNMENT_VERTICAL,
    }

    for obj, want_key in expected.items():
        got_key = _owner_key(prj, obj)
        _assert(got_key == want_key, f"{obj.Name} owner mismatch: got={got_key}, want={want_key}")

    # No direct project links: object should still land under a valid alignment root.
    # Current routing prefers a document-level fallback alignment when one exists,
    # and only falls back to ALN_Unassigned when no alignment context is available.
    prj2 = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(prj2)
    prj2.Label = "CorridorRoad Project (No Links)"
    ensure_project_tree(prj2, include_references=False)
    va2 = doc.addObject("Part::FeaturePython", "VerticalAlignmentNoLinks")
    link_project(prj2, adopt_extra=[va2])
    va2_owner = _owner_folder(prj2, va2)
    _assert(va2_owner is not None, "No-links VA has no owner")
    _assert(_key(va2_owner) == ALIGNMENT_VERTICAL, "No-links VA should be in vertical folder")
    va2_root = _parent_folder(prj2, va2_owner)
    _assert(va2_root is not None, "No-links VA alignment root not found")
    _assert(_key(va2_root) == ALIGNMENT_ROOT, "No-links VA parent must be alignment root")
    _assert(str(getattr(va2_root, "Label", "") or "").startswith("ALN_"), "No-links VA should map to an alignment root label")
    _assert(
        str(getattr(va2_root, ALN_REF_NAME_PROP, "") or "") in ("", str(getattr(aln, "Name", "") or "")),
        "No-links VA should use the doc fallback alignment root or ALN_Unassigned",
    )

    doc.recompute()
    print("[PASS] CorridorRoad fixed-tree smoke test completed.")


if __name__ == "__main__":
    run()
