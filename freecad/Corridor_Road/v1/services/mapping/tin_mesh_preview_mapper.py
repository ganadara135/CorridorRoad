"""TIN mesh preview mapper for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.tin_surface import TINSurface


TIN_MESH_PREVIEW_STYLES = {
    "base": {
        "shape_color": (0.35, 0.60, 0.95),
        "line_color": (0.18, 0.36, 0.72),
        "point_color": (0.18, 0.36, 0.72),
        "transparency": 35,
        "line_width": 1.0,
    },
    "edited": {
        "shape_color": (0.20, 0.72, 0.38),
        "line_color": (0.08, 0.42, 0.18),
        "point_color": (0.08, 0.42, 0.18),
        "transparency": 15,
        "line_width": 1.2,
    },
    "design": {
        "shape_color": (1.00, 0.56, 0.12),
        "line_color": (1.00, 0.32, 0.02),
        "point_color": (1.00, 0.32, 0.02),
        "transparency": 18,
        "line_width": 1.6,
    },
    "subgrade": {
        "shape_color": (0.46, 0.49, 0.58),
        "line_color": (0.20, 0.23, 0.30),
        "point_color": (0.20, 0.23, 0.30),
        "transparency": 62,
        "line_width": 1.0,
    },
    "daylight": {
        "shape_color": (0.42, 0.72, 0.28),
        "line_color": (0.18, 0.45, 0.12),
        "point_color": (0.18, 0.45, 0.12),
        "transparency": 32,
        "line_width": 1.4,
    },
    "drainage": {
        "shape_color": (0.08, 0.74, 0.92),
        "line_color": (0.00, 0.35, 0.62),
        "point_color": (0.00, 0.35, 0.62),
        "transparency": 12,
        "line_width": 1.8,
    },
}


@dataclass(frozen=True)
class TINMeshPreviewResult:
    """Result of creating a lightweight FreeCAD mesh preview."""

    status: str
    object_name: str = ""
    label: str = ""
    facet_count: int = 0
    notes: str = ""


class TINMeshPreviewMapper:
    """Map a TINSurface into a lightweight FreeCAD mesh preview."""

    def build_facet_rows(self, surface: TINSurface) -> list[tuple[tuple[float, float, float], ...]]:
        """Return mesh facet coordinate triples from TIN triangle rows."""

        vertices = surface.vertex_map()
        facets: list[tuple[tuple[float, float, float], ...]] = []
        for triangle in list(surface.triangle_rows or []):
            try:
                p0 = vertices[triangle.v1]
                p1 = vertices[triangle.v2]
                p2 = vertices[triangle.v3]
            except KeyError:
                continue
            facets.append(
                (
                    (float(p0.x), float(p0.y), float(p0.z)),
                    (float(p1.x), float(p1.y), float(p1.z)),
                    (float(p2.x), float(p2.y), float(p2.z)),
                )
            )
        return facets

    def build_mesh(self, surface: TINSurface, *, mesh_module=None, app_module=None):
        """Build a Mesh.Mesh object from a TINSurface."""

        if mesh_module is None:
            import Mesh as mesh_module  # type: ignore
        if app_module is None:
            import FreeCAD as app_module  # type: ignore

        mesh = mesh_module.Mesh()
        for p0, p1, p2 in self.build_facet_rows(surface):
            mesh.addFacet(
                app_module.Vector(*p0),
                app_module.Vector(*p1),
                app_module.Vector(*p2),
            )
        return mesh

    def create_preview_object(
        self,
        document,
        surface: TINSurface,
        *,
        object_name: str = "",
        mesh_module=None,
        app_module=None,
        recompute: bool = True,
    ) -> TINMeshPreviewResult:
        """Create a FreeCAD Mesh::Feature preview object for a TINSurface."""

        if document is None:
            return TINMeshPreviewResult(status="skipped", notes="No FreeCAD document is available.")
        try:
            mesh = self.build_mesh(surface, mesh_module=mesh_module, app_module=app_module)
            facet_count = int(getattr(mesh, "CountFacets", 0) or 0)
            name = object_name or self._safe_object_name(surface)
            obj = document.addObject("Mesh::Feature", name)
            obj.Mesh = mesh
            label = f"TIN Preview - {getattr(surface, 'label', '') or surface.surface_id or name}"
            try:
                obj.Label = label
            except Exception:
                label = str(getattr(obj, "Label", "") or name)
            if bool(recompute):
                try:
                    document.recompute()
                except Exception:
                    pass
            return TINMeshPreviewResult(
                status="created",
                object_name=str(getattr(obj, "Name", "") or name),
                label=label,
                facet_count=facet_count,
                notes="TIN mesh preview created from TINSurface triangles.",
            )
        except Exception as exc:
            return TINMeshPreviewResult(
                status="error",
                notes=f"TIN mesh preview creation failed: {exc}",
            )

    def create_or_update_preview_object(
        self,
        document,
        surface: TINSurface,
        *,
        object_name: str = "",
        label_prefix: str = "TIN Preview",
        surface_role: str = "base",
        mesh_module=None,
        app_module=None,
        recompute: bool = True,
    ) -> TINMeshPreviewResult:
        """Create or update one reusable Mesh::Feature preview for a TINSurface."""

        if document is None:
            return TINMeshPreviewResult(status="skipped", notes="No FreeCAD document is available.")
        try:
            mesh = self.build_mesh(surface, mesh_module=mesh_module, app_module=app_module)
            facet_count = int(getattr(mesh, "CountFacets", 0) or 0)
            name = object_name or self._safe_object_name(surface)
            obj = document.getObject(name)
            status = "updated" if obj is not None else "created"
            if obj is None:
                obj = document.addObject("Mesh::Feature", name)
            obj.Mesh = mesh
            label = f"{label_prefix} - {getattr(surface, 'label', '') or surface.surface_id or name}"
            try:
                obj.Label = label
            except Exception:
                label = str(getattr(obj, "Label", "") or name)
            _set_string_property(obj, "CRRecordKind", "tin_mesh_preview")
            _set_string_property(obj, "SurfaceId", str(getattr(surface, "surface_id", "") or ""))
            _set_string_property(obj, "SurfaceKind", str(getattr(surface, "surface_kind", "") or ""))
            _set_string_property(obj, "SurfaceRole", str(surface_role or "base"))
            _set_coordinate_metadata(obj, surface)
            _set_integer_property(obj, "VertexCount", len(list(getattr(surface, "vertex_rows", []) or [])))
            _set_integer_property(obj, "TriangleCount", len(list(getattr(surface, "triangle_rows", []) or [])))
            _style_preview_object(obj, surface_role=str(surface_role or "base"))
            if bool(recompute):
                try:
                    document.recompute()
                except Exception:
                    pass
            return TINMeshPreviewResult(
                status=status,
                object_name=str(getattr(obj, "Name", "") or name),
                label=label,
                facet_count=facet_count,
                notes=f"TIN mesh preview {status} from TINSurface triangles.",
            )
        except Exception as exc:
            return TINMeshPreviewResult(
                status="error",
                notes=f"TIN mesh preview creation failed: {exc}",
            )

    @staticmethod
    def _safe_object_name(surface: TINSurface) -> str:
        raw = str(getattr(surface, "surface_id", "") or getattr(surface, "label", "") or "TINPreview")
        safe = "".join(ch if ch.isalnum() else "_" for ch in raw)
        safe = safe.strip("_") or "TINPreview"
        if not safe.startswith("TINPreview"):
            safe = f"TINPreview_{safe}"
        return safe[:80]


def _set_string_property(obj, name: str, value: str) -> None:
    if obj is None:
        return
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyString", name, "CorridorRoad", name)
    setattr(obj, name, str(value or ""))


def _set_coordinate_metadata(obj, surface: TINSurface) -> None:
    values = _surface_quality_values(surface)
    mapping = {
        "SourceCoords": "coordinate_input",
        "ModelCoords": "coordinate_model",
        "CoordinateWorkflow": "coordinate_workflow",
        "CRSEPSG": "crs_epsg",
        "ProjectOriginE": "project_origin_e",
        "ProjectOriginN": "project_origin_n",
        "ProjectOriginZ": "project_origin_z",
        "LocalOriginX": "local_origin_x",
        "LocalOriginY": "local_origin_y",
        "LocalOriginZ": "local_origin_z",
        "NorthRotationDeg": "north_rotation_deg",
    }
    for prop_name, key in mapping.items():
        value = values.get(key, "")
        if prop_name in {
            "ProjectOriginE",
            "ProjectOriginN",
            "ProjectOriginZ",
            "LocalOriginX",
            "LocalOriginY",
            "LocalOriginZ",
            "NorthRotationDeg",
        }:
            _set_float_property(obj, prop_name, value)
        else:
            _set_string_property(obj, prop_name, str(value or ""))


def _surface_quality_values(surface: TINSurface) -> dict[str, object]:
    values: dict[str, object] = {}
    for row in list(getattr(surface, "quality_rows", []) or []):
        kind = str(getattr(row, "kind", "") or "")
        if kind:
            values[kind] = getattr(row, "value", "")
    return values


def _set_integer_property(obj, name: str, value: int) -> None:
    if obj is None:
        return
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyInteger", name, "CorridorRoad", name)
    setattr(obj, name, int(value or 0))


def _set_float_property(obj, name: str, value) -> None:
    if obj is None:
        return
    if not hasattr(obj, name):
        obj.addProperty("App::PropertyFloat", name, "CorridorRoad", name)
    try:
        setattr(obj, name, float(value or 0.0))
    except Exception:
        setattr(obj, name, 0.0)


def _style_preview_object(obj, *, surface_role: str) -> None:
    vobj = getattr(obj, "ViewObject", None)
    if vobj is None:
        return
    style = tin_mesh_preview_style(surface_role)
    try:
        vobj.Visibility = True
        if hasattr(vobj, "Selectable"):
            vobj.Selectable = True
        vobj.DisplayMode = "Flat Lines"
        vobj.ShapeColor = style["shape_color"]
        vobj.LineColor = style["line_color"]
        vobj.PointColor = style["point_color"]
        vobj.LineWidth = float(style["line_width"])
        if hasattr(vobj, "Transparency"):
            vobj.Transparency = int(style["transparency"])
    except Exception:
        pass


def tin_mesh_preview_style(surface_role: object) -> dict[str, object]:
    """Return the visual style policy for a TIN mesh preview role."""

    role = str(surface_role or "").strip().lower()
    return dict(TIN_MESH_PREVIEW_STYLES.get(role, TIN_MESH_PREVIEW_STYLES["base"]))
