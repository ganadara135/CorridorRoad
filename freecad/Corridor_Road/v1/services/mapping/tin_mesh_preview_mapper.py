"""TIN mesh preview mapper for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.result.tin_surface import TINSurface


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

    @staticmethod
    def _safe_object_name(surface: TINSurface) -> str:
        raw = str(getattr(surface, "surface_id", "") or getattr(surface, "label", "") or "TINPreview")
        safe = "".join(ch if ch.isalnum() else "_" for ch in raw)
        safe = safe.strip("_") or "TINPreview"
        if not safe.startswith("TINPreview"):
            safe = f"TINPreview_{safe}"
        return safe[:80]
