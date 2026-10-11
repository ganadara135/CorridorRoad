"""Legacy proxy document corpus: builder and snapshot helpers.

`docsV1/V1_LEGACY_PROXY_MIGRATION_DESIGN.md` phase P1. The corpus holds documents written by the
legacy `objects` classes while their behavior still exists, so that later phases (restore-only
stubs, conversion) can prove that those documents still open, and that a reopen-and-save cycle
keeps every proxy reference, proxy state and property.

Build once, before any legacy class loses its behavior, with the FreeCAD interpreter:

    "C:\\Program Files\\FreeCAD 1.1\\bin\\python.exe" tests/legacy_proxy_corpus.py --build

`tests/contracts/v1/test_legacy_proxy_corpus.py` checks the committed corpus against the
manifest written here. Rebuilding after the stubs land would record the stubs, not the legacy
classes, so the builder refuses to overwrite an existing corpus without `--force`.
"""

from __future__ import annotations

import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = REPO_ROOT / "tests" / "samples" / "legacy_proxy_corpus"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
SAMPLES_DIR = REPO_ROOT / "tests" / "samples"

CANONICAL_OBJECTS = "freecad.Corridor_Road.objects"
LEGACY_PREFIX_OBJECTS = "objects"

# Every legacy proxy class: (module, class, FreeCAD base type). The base types are the ones the
# legacy code and smoke scripts create; classes no current code creates use the type their
# geometry property needs.
LEGACY_PROXY_CLASSES = (
    ("obj_alignment", "HorizontalAlignment", "Part::FeaturePython"),
    ("obj_assembly_template", "AssemblyTemplate", "Part::FeaturePython"),
    ("obj_centerline3d", "Centerline3D", "Part::FeaturePython"),
    ("obj_centerline3d_display", "Centerline3DDisplay", "Part::FeaturePython"),
    ("obj_corridor", "Corridor", "Part::FeaturePython"),
    ("obj_cross_section_edit_plan", "CrossSectionEditPlan", "Part::FeaturePython"),
    ("obj_cut_fill_calc", "CutFillCalc", "Part::FeaturePython"),
    ("obj_design_grading_surface", "DesignGradingSurface", "Mesh::FeaturePython"),
    ("obj_design_terrain", "DesignTerrain", "Mesh::FeaturePython"),
    ("obj_fg_display", "FGDisplay", "Part::FeaturePython"),
    ("obj_pointcloud_dem", "PointCloudDEM", "Mesh::FeaturePython"),
    ("obj_profile_bundle", "ProfileBundle", "Part::FeaturePython"),
    ("obj_region_plan", "RegionPlan", "Part::FeaturePython"),
    ("obj_section_set", "SectionSet", "Part::FeaturePython"),
    ("obj_stationing", "Stationing", "Part::FeaturePython"),
    ("obj_structure_set", "StructureSet", "Part::FeaturePython"),
    ("obj_typical_section_template", "TypicalSectionTemplate", "Part::FeaturePython"),
    ("obj_typical_section_template", "TypicalSectionPavementDisplay", "Part::FeaturePython"),
    ("obj_typical_section_template", "TypicalSectionSelectionDisplay", "Part::FeaturePython"),
    ("obj_vertical_alignment", "VerticalAlignment", "Part::FeaturePython"),
)

CORPUS_DOCUMENTS = (
    # (file name, module prefix the proxies are saved under)
    ("legacy_chain.FCStd", CANONICAL_OBJECTS),
    ("legacy_chain_prefixed.FCStd", LEGACY_PREFIX_OBJECTS),
)

GUI_DOCUMENT = "legacy_chain_gui.FCStd"
GUI_MANIFEST_PATH = CORPUS_DIR / "manifest_gui.json"

# Legacy view providers whose state holds the FreeCAD object itself (`self.Object`) and no
# __getstate__/dumps: FreeCAD's JSON save of that state fails, and what gets written ("" or
# {"Object": null}) depends on whether the provider was attached when saving. Their module and
# class references are stored either way, and attach() rebuilds the lost back-reference, so the
# round trip compares only module and class for these four. A pre-existing legacy defect
# (design document section 3), not something the corpus may hide for any other provider.
UNSERIALIZABLE_VIEW_PROVIDER_STATE = frozenset(
    {"Centerline3D", "Centerline3DDisplay", "HorizontalAlignment", "Stationing"}
)

# Rounding for geometry and float values read back from a document: the file stores doubles
# exactly, so this only absorbs the last-digit noise of derived values such as areas.
_DIGITS = 6


# Snapshots


def stored_proxies(path) -> dict[str, dict[str, str]]:
    """Each object's stored Proxy entry in Document.xml: module, class and encoded state."""

    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("Document.xml"))
    entries = {}
    for obj in root.iter("Object"):
        name = obj.get("name")
        properties = obj.find("Properties")
        if not name or properties is None:
            continue
        for prop in properties.findall("Property"):
            if prop.get("name") != "Proxy":
                continue
            python = prop.find("Python")
            if python is not None:
                entries[name] = {
                    "module": python.get("module", ""),
                    "class": python.get("class", ""),
                    "value": python.get("value", ""),
                }
    return entries


def stored_view_providers(path) -> dict[str, dict[str, str]]:
    """Each view provider's stored Proxy entry in GuiDocument.xml (written by GUI sessions only)."""

    with zipfile.ZipFile(path) as archive:
        if "GuiDocument.xml" not in archive.namelist():
            return {}
        root = ET.fromstring(archive.read("GuiDocument.xml"))
    entries = {}
    for view_provider in root.iter("ViewProvider"):
        name = view_provider.get("name")
        properties = view_provider.find("Properties")
        if not name or properties is None:
            continue
        for prop in properties.findall("Property"):
            python = prop.find("Python") if prop.get("name") == "Proxy" else None
            if python is not None:
                entries[name] = {
                    "module": python.get("module", ""),
                    "class": python.get("class", ""),
                    "value": python.get("value", ""),
                }
    return entries


def object_snapshot(obj) -> dict[str, object]:
    """Comparable values of one object's properties, its type and its live proxy class."""

    proxy = getattr(obj, "Proxy", None)
    properties = {}
    for name in sorted(obj.PropertiesList):
        if name in ("Proxy", "ExpressionEngine"):
            continue
        try:
            properties[name] = _normalize(getattr(obj, name))
        except Exception as exc:  # a property the restored object cannot read is a finding
            properties[name] = f"<unreadable: {type(exc).__name__}>"
    return {
        "type_id": obj.TypeId,
        "proxy": None if proxy is None else f"{type(proxy).__module__}.{type(proxy).__name__}",
        "properties": properties,
    }


def document_snapshot(doc) -> dict[str, dict[str, object]]:
    return {obj.Name: object_snapshot(obj) for obj in doc.Objects}


def _normalize(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, _DIGITS)
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in sorted(value.items())}
    type_name = type(value).__name__
    if hasattr(value, "TypeId") and hasattr(value, "Name"):  # a linked document object
        return f"<link {value.Name}>"
    if type_name == "Vector":
        return [round(value.x, _DIGITS), round(value.y, _DIGITS), round(value.z, _DIGITS)]
    if type_name == "Placement":
        return {"base": _normalize(value.Base), "rotation": [round(q, _DIGITS) for q in value.Rotation.Q]}
    if type_name in ("Shape", "TopoShape", "Compound", "Solid", "Shell", "Face", "Wire", "Edge", "Vertex"):
        if value.isNull():
            return {"shape": "null"}
        # not BoundBox: it uses the triangulation when one exists, so a GUI session (which
        # tessellates for display) and a headless one report different boxes for curved edges
        box = value.optimalBoundingBox(False, False)
        return {
            "shape": value.ShapeType,
            "faces": len(value.Faces),
            "edges": len(value.Edges),
            "vertexes": len(value.Vertexes),
            "length": round(value.Length, _DIGITS),
            "area": round(value.Area, _DIGITS),
            "bound_box": [round(v, _DIGITS) for v in (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax)],
        }
    if type_name in ("Mesh", "MeshObject"):
        return {"mesh_points": value.CountPoints, "mesh_facets": value.CountFacets}
    if type_name == "Quantity":
        return [round(value.Value, _DIGITS), str(value.Unit)]
    return f"<{type_name}>"


# Builder


def _load_classes():
    import importlib

    from freecad.Corridor_Road import install_virtual_path_mappings

    install_virtual_path_mappings(eager=True)
    return {
        name: importlib.import_module(f"{CANONICAL_OBJECTS}.{module}").__dict__[name]
        for module, name, _base in LEGACY_PROXY_CLASSES
    }


def _read_csv(name):
    import csv

    with open(SAMPLES_DIR / name, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(row, key, default=0.0):
    text = str(row.get(key, "") or "").strip()
    return float(text) if text else float(default)


def _build_chain(App, classes, doc_name):
    """One instance of every legacy proxy class, linked into the chain the legacy workflow built."""

    doc = App.newDocument(doc_name)
    made = {}
    for module, name, base in LEGACY_PROXY_CLASSES:
        obj = doc.addObject(base, name)
        classes[name](obj)
        made[name] = obj

    alignment = made["HorizontalAlignment"]
    alignment.IPPoints = [App.Vector(0.0, 0.0, 0.0), App.Vector(380.0, 60.0, 0.0), App.Vector(760.0, 0.0, 0.0)]
    alignment.UseTransitionCurves = False

    profile = made["VerticalAlignment"]
    profile.PVIStations = [0.0, 380.0, 760.0]
    profile.PVIElevations = [10.0, 16.0, 12.0]

    display = made["Centerline3DDisplay"]
    display.Alignment = alignment
    display.ElevationSource = "FlatZero"
    display.UseStationing = False

    assembly = made["AssemblyTemplate"]
    assembly.UseSideSlopes = True
    assembly.LeftSideWidth = 8.0
    assembly.RightSideWidth = 8.0

    template = made["TypicalSectionTemplate"]
    components = _read_csv("typical_section_basic_rural.csv")
    template.ComponentIds = [str(r.get("Id", "") or "") for r in components]
    template.ComponentTypes = [str(r.get("Type", "") or "") for r in components]
    template.ComponentSides = [str(r.get("Side", "") or "") for r in components]
    template.ComponentWidths = [_number(r, "Width") for r in components]
    template.ComponentCrossSlopes = [_number(r, "CrossSlopePct") for r in components]
    pavement = _read_csv("typical_section_pavement_basic.csv")
    template.PavementLayerIds = [str(r.get("Id", "") or "") for r in pavement]
    template.PavementLayerTypes = [str(r.get("Type", "") or "") for r in pavement]
    template.PavementLayerThicknesses = [_number(r, "Thickness") for r in pavement]

    structures = made["StructureSet"]
    structures.StructureIds = ["CULV-01"]
    structures.StructureTypes = ["culvert"]
    structures.StartStations = [300.0]
    structures.EndStations = [320.0]
    structures.CenterStations = [310.0]
    structures.Sides = ["both"]
    structures.Offsets = [0.0]
    structures.Widths = [6.0]
    structures.Heights = [3.0]

    sections = made["SectionSet"]
    sections.SourceCenterlineDisplay = display
    sections.AssemblyTemplate = assembly
    sections.TypicalSectionTemplate = template
    sections.UseTypicalSectionTemplate = True
    sections.StructureSet = structures
    sections.UseStructureSet = True
    sections.Mode = "Range"
    sections.StartStation = 0.0
    sections.EndStation = 760.0
    sections.Interval = 80.0
    sections.CreateChildSections = False

    made["Corridor"].SourceSectionSet = sections
    made["DesignGradingSurface"].SourceSectionSet = sections
    made["FGDisplay"].SourceVA = profile
    made["ProfileBundle"].VerticalAlignment = profile
    made["Stationing"].Alignment = alignment
    made["Centerline3D"].Alignment = alignment
    made["Centerline3D"].VerticalAlignment = profile
    made["CutFillCalc"].SourceCorridor = made["Corridor"]
    made["DesignTerrain"].SourceDesignSurface = made["DesignGradingSurface"]
    made["TypicalSectionPavementDisplay"].SourceTypicalSection = template
    made["TypicalSectionSelectionDisplay"].SourceTypicalSection = template
    regions = made["RegionPlan"]
    regions.BaseIds = ["BASE-01"]
    regions.BaseStartStations = [0.0]
    regions.BaseEndStations = [760.0]
    doc.recompute()
    return doc


def build(force: bool = False) -> None:
    import FreeCAD as App

    if MANIFEST_PATH.exists() and not force:
        raise SystemExit(f"{MANIFEST_PATH} exists; the corpus records the legacy classes. Use --force to rebuild.")
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    classes = _load_classes()
    manifest = {"documents": {}}
    for file_name, prefix in CORPUS_DOCUMENTS:
        originals = {name: cls.__module__ for name, cls in classes.items()}
        try:
            if prefix != CANONICAL_OBJECTS:
                # Save under a legacy module path, as documents from the pre-refactor layout did.
                for module, name, _base in LEGACY_PROXY_CLASSES:
                    classes[name].__module__ = f"{prefix}.{module}"
            doc = _build_chain(App, classes, Path(file_name).stem)
            path = CORPUS_DIR / file_name
            path.unlink(missing_ok=True)  # saveAs over a file leaves an .FCBak copy
            doc.saveAs(str(path))
            App.closeDocument(doc.Name)
        finally:
            for name, module in originals.items():
                classes[name].__module__ = module
        reopened = App.openDocument(str(path))
        try:
            manifest["documents"][file_name] = {
                "saved_module_prefix": prefix,
                "stored_proxies": stored_proxies(path),
                "objects": document_snapshot(reopened),
            }
        finally:
            App.closeDocument(reopened.Name)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(CORPUS_DOCUMENTS)} documents and {MANIFEST_PATH.relative_to(REPO_ROOT)}")


def build_gui(force: bool = False) -> None:
    """Write the GUI corpus document: the chain with every class's stored view provider.

    View providers are saved in GuiDocument.xml, which only a GUI session writes. Run from the
    FreeCAD GUI (for example `freecad.exe` with a launcher that calls this). It also proves the
    GUI round trip: reopen and save twice, keeping every stored view-provider and object proxy.
    """

    import FreeCAD as App

    if not getattr(App, "GuiUp", False):
        raise SystemExit("build_gui needs the FreeCAD GUI.")
    if GUI_MANIFEST_PATH.exists() and not force:
        raise SystemExit(f"{GUI_MANIFEST_PATH} exists; use force to rebuild.")
    import importlib
    import tempfile

    classes = _load_classes()
    doc = _build_chain(App, classes, Path(GUI_DOCUMENT).stem)
    for module, name, _base in LEGACY_PROXY_CLASSES:
        view_provider = importlib.import_module(f"{CANONICAL_OBJECTS}.{module}").__dict__[f"ViewProvider{name}"]
        view_provider(doc.getObject(name).ViewObject)
    doc.recompute()
    path = CORPUS_DIR / GUI_DOCUMENT
    path.unlink(missing_ok=True)  # saveAs over a file leaves an .FCBak copy
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)

    reopened = App.openDocument(str(path))
    try:
        recorded = {
            "stored_proxies": stored_proxies(path),
            "stored_view_providers": stored_view_providers(path),
            "objects": document_snapshot(reopened),
        }
    finally:
        App.closeDocument(reopened.Name)

    failures = []
    with tempfile.TemporaryDirectory() as folder:
        source = str(path)
        for cycle in (1, 2):
            doc = App.openDocument(source)
            try:
                if document_snapshot(doc) != recorded["objects"]:
                    failures.append(f"cycle {cycle}: restored values differ")
                source = str(Path(folder) / f"gui_cycle{cycle}.FCStd")
                doc.saveAs(source)
            finally:
                App.closeDocument(doc.Name)
            for label, before, after in (
                ("object", recorded["stored_proxies"], stored_proxies(source)),
                ("view provider", recorded["stored_view_providers"], stored_view_providers(source)),
            ):
                for name in sorted(set(before) | set(after)):
                    changed = sorted(
                        key for key in ("module", "class", "value")
                        if before.get(name, {}).get(key) != after.get(name, {}).get(key)
                    )
                    if label == "view provider" and name in UNSERIALIZABLE_VIEW_PROVIDER_STATE:
                        changed = [key for key in changed if key != "value"]
                    if changed:
                        failures.append(f"cycle {cycle}: {label} {name}: " + ", ".join(changed))
    recorded["gui_round_trip"] = failures or "pass"
    GUI_MANIFEST_PATH.write_text(json.dumps(recorded, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {GUI_DOCUMENT}; GUI round trip: {recorded['gui_round_trip']}")


if __name__ == "__main__":
    sys.path.insert(0, str(REPO_ROOT))
    os.chdir(REPO_ROOT)
    if "--build" in sys.argv:
        build(force="--force" in sys.argv)
    else:
        print(__doc__)
