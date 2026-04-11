# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
StructureSet recompute propagation smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_structure_recompute_chain.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_cut_fill_calc import CutFillCalc
from freecad.Corridor_Road.objects.obj_design_grading_surface import DesignGradingSurface
from freecad.Corridor_Road.objects.obj_design_terrain import DesignTerrain
from freecad.Corridor_Road.objects.obj_section_set import SectionSet
from freecad.Corridor_Road.objects.obj_structure_set import StructureSet


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    doc = App.newDocument("CRStructureRecomputeChain")

    ss = doc.addObject("Part::FeaturePython", "StructureSet")
    StructureSet(ss)

    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    sec.UseStructureSet = True
    sec.StructureSet = ss
    sec.Status = "OK"

    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    cor.Status = "OK"

    dgs = doc.addObject("Mesh::FeaturePython", "DesignGradingSurface")
    DesignGradingSurface(dgs)
    dgs.SourceSectionSet = sec
    dgs.Status = "OK"

    dtm = doc.addObject("Mesh::FeaturePython", "DesignTerrain")
    DesignTerrain(dtm)
    dtm.SourceDesignSurface = dgs
    dtm.Status = "OK"

    cfc = doc.addObject("Part::FeaturePython", "CutFillCalc")
    CutFillCalc(cfc)
    cfc.SourceCorridor = cor
    cfc.Status = "OK"

    ss.StructureIds = ["S1"]
    ss.Proxy.onChanged(ss, "StructureIds")

    _assert(str(getattr(sec, "Status", "") or "").startswith("NEEDS_RECOMPUTE"), "SectionSet was not marked for recompute")
    _assert("[Recompute]" in str(getattr(sec, "Label", "") or ""), "SectionSet label was not marked")

    _assert(bool(getattr(cor, "NeedsRecompute", False)), "CorridorLoft NeedsRecompute was not set")
    _assert("NEEDS_RECOMPUTE" not in str(getattr(cor, "Status", "") or ""), "CorridorLoft should keep stale state internal rather than overwriting user-facing status")
    _assert("[Recompute]" not in str(getattr(cor, "Label", "") or ""), "CorridorLoft should not add a recompute suffix to the user-facing label")

    _assert(bool(getattr(dgs, "NeedsRecompute", False)), "DesignGradingSurface NeedsRecompute was not set")
    _assert(str(getattr(dgs, "Status", "") or "").startswith("NEEDS_RECOMPUTE"), "DesignGradingSurface status was not marked")

    _assert(bool(getattr(dtm, "NeedsRecompute", False)), "DesignTerrain NeedsRecompute was not set")
    _assert(str(getattr(dtm, "Status", "") or "").startswith("NEEDS_RECOMPUTE"), "DesignTerrain status was not marked")

    _assert(str(getattr(cfc, "Status", "") or "").startswith("NEEDS_RECOMPUTE"), "CutFillCalc status was not marked")
    _assert("[Recompute]" in str(getattr(cfc, "Label", "") or ""), "CutFillCalc label was not marked")

    App.closeDocument(doc.Name)


run()
