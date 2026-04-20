# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Daylight coordinate-mode smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_daylight_coordinate_modes.py
"""

import FreeCAD as App
import Mesh

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment
from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate
from freecad.Corridor_Road.objects.obj_centerline3d_display import Centerline3DDisplay
from freecad.Corridor_Road.objects.obj_project import CorridorRoadProject, local_to_world
from freecad.Corridor_Road.objects.obj_section_set import SectionSet


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _approx(a, b, tol, msg):
    if abs(float(a) - float(b)) > float(tol):
        raise Exception(f"{msg}: {a} vs {b}")


def _shape_ok(obj) -> bool:
    shp = getattr(obj, "Shape", None)
    if shp is None:
        return False
    try:
        return not shp.isNull()
    except Exception:
        return False


def _make_project(doc):
    prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
    CorridorRoadProject(prj)
    prj.ProjectOriginE = 500000.0
    prj.ProjectOriginN = 200000.0
    prj.ProjectOriginZ = 75.0
    prj.LocalOriginX = 100.0
    prj.LocalOriginY = -50.0
    prj.LocalOriginZ = 5.0
    prj.NorthRotationDeg = 22.5
    prj.CRSEPSG = "EPSG:5186"
    prj.CoordSetupStatus = "Initialized"
    prj.CoordinateWorkflow = "World-first"
    return prj


def _make_alignment(doc, length=20.0):
    aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
    HorizontalAlignment(aln)
    aln.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(float(length), 0.0, 0.0)]
    aln.UseTransitionCurves = False
    return aln


def _make_display(doc, aln):
    disp = doc.addObject("Part::FeaturePython", "Centerline3DDisplay")
    Centerline3DDisplay(disp)
    disp.Alignment = aln
    disp.ElevationSource = "FlatZero"
    disp.UseStationing = False
    return disp


def _make_assembly(doc):
    asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
    AssemblyTemplate(asm)
    asm.LeftWidth = 4.0
    asm.RightWidth = 4.0
    asm.LeftSlopePct = -2.0
    asm.RightSlopePct = 2.0
    asm.UseSideSlopes = True
    asm.LeftSideWidth = 6.0
    asm.RightSideWidth = 6.0
    asm.LeftSideSlopePct = 50.0
    asm.RightSideSlopePct = 50.0
    return asm


def _plane_local_z(x: float, y: float) -> float:
    return 100.0 + float(x) + 2.0 * float(y)


def _plane_local_points():
    p00 = App.Vector(0.0, 0.0, _plane_local_z(0.0, 0.0))
    p10 = App.Vector(10.0, 0.0, _plane_local_z(10.0, 0.0))
    p01 = App.Vector(0.0, 10.0, _plane_local_z(0.0, 10.0))
    p11 = App.Vector(10.0, 10.0, _plane_local_z(10.0, 10.0))
    return p00, p10, p01, p11


def _make_mesh_feature(doc, name, tris, output_coords):
    obj = doc.addObject("Mesh::Feature", name)
    mesh = Mesh.Mesh()
    for p0, p1, p2 in list(tris or []):
        mesh.addFacet(p0, p1, p2)
    obj.Mesh = mesh
    if not hasattr(obj, "OutputCoords"):
        obj.addProperty("App::PropertyString", "OutputCoords", "Source", "Terrain coordinate mode")
    obj.OutputCoords = str(output_coords)
    return obj


def _make_section_set(doc, name, disp, asm, terrain, terrain_mesh_coords):
    sec = doc.addObject("Part::FeaturePython", name)
    SectionSet(sec)
    sec.SourceCenterlineDisplay = disp
    sec.AssemblyTemplate = asm
    sec.Mode = "Manual"
    sec.StationText = "5"
    sec.IncludeAlignmentIPStations = False
    sec.IncludeAlignmentSCCSStations = False
    sec.DaylightAuto = True
    sec.TerrainMesh = terrain
    sec.TerrainMeshCoords = str(terrain_mesh_coords)
    sec.CreateChildSections = False
    return sec


def run():
    doc = App.newDocument("CRDaylightCoordModes")

    prj = _make_project(doc)
    aln = _make_alignment(doc, length=20.0)
    disp = _make_display(doc, aln)
    asm = _make_assembly(doc)

    p00, p10, p01, p11 = _plane_local_points()
    local_tris = [(p00, p10, p11), (p00, p11, p01)]

    world_tris = []
    for tri in local_tris:
        row = []
        for p in tri:
            e, n, z = local_to_world(prj, p.x, p.y, p.z)
            row.append(App.Vector(float(e), float(n), float(z)))
        world_tris.append(tuple(row))

    terrain_local = _make_mesh_feature(doc, "TerrainLocal", local_tris, "Local")
    terrain_world = _make_mesh_feature(doc, "TerrainWorld", world_tris, "World")

    local_sampler = SectionSet._terrain_sampler(terrain_local, coord_context=prj, coord_mode="Local")
    world_sampler = SectionSet._terrain_sampler(terrain_world, coord_context=prj, coord_mode="World")
    _assert(local_sampler is not None, "Local terrain sampler was not created")
    _assert(world_sampler is not None, "World terrain sampler was not created")

    for x, y in [(2.5, 3.0), (7.0, 1.5), (6.0, 6.0)]:
        expected = _plane_local_z(x, y)
        z_local = SectionSet._terrain_z_at(local_sampler, x, y)
        z_world = SectionSet._terrain_z_at(world_sampler, x, y)
        _approx(z_local, expected, 1e-6, "Local terrain sampler Z mismatch")
        _approx(z_world, expected, 2e-2, "World terrain sampler Z mismatch")
        _approx(z_local, z_world, 2e-2, "Local/World terrain samplers diverged")

    sec_local = _make_section_set(doc, "SectionSetLocal", disp, asm, terrain_local, "World")
    sec_world = _make_section_set(doc, "SectionSetWorld", disp, asm, terrain_world, "Local")

    doc.recompute()

    _assert(_shape_ok(sec_local), "Local terrain SectionSet did not generate geometry")
    _assert(_shape_ok(sec_world), "World terrain SectionSet did not generate geometry")
    status_local = str(getattr(sec_local, "Status", "") or "")
    status_world = str(getattr(sec_world, "Status", "") or "")
    _assert("daylight=terrain:local" in status_local, "Local terrain status missing local daylight token")
    _assert("daylight=terrain:world" in status_world, "World terrain status missing world daylight token")
    _assert("earthwork=full" in status_local, "Local terrain status should report full earthwork")
    _assert("earthwork=full" in status_world, "World terrain status should report full earthwork")

    App.closeDocument(doc.Name)
    print("[PASS] Daylight coordinate-mode smoke test completed.")


if __name__ == "__main__":
    run()
