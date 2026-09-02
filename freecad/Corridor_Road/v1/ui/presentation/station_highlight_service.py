"""3D station-highlight presentation service for CorridorRoad v1."""

from __future__ import annotations

import math

try:
    import FreeCAD as App
    import Part
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Part = None

from ...objects.project_document_adapter import ProjectDocumentAdapter


class StationHighlightPresentationService:
    """Build and apply the presentation-only marker for a reviewed station."""

    def build_shape(self, row: dict[str, object], *, radius: float = 5.0):
        """Build a 3D marker shape from one evaluated station review row."""

        if App is None or Part is None:
            return None
        x = _safe_float(row.get("x", 0.0), 0.0)
        y = _safe_float(row.get("y", 0.0), 0.0)
        tangent = _safe_float(row.get("tangent", 0.0), 0.0)
        marker_radius = max(float(radius), 0.5)
        center = App.Vector(x, y, 0.0)
        tangent_rad = math.radians(tangent)
        tx = math.cos(tangent_rad)
        ty = math.sin(tangent_rad)
        nx = -ty
        ny = tx
        edges = [
            Part.makeCircle(marker_radius, center, App.Vector(0.0, 0.0, 1.0)),
            Part.makeLine(
                App.Vector(x - tx * marker_radius, y - ty * marker_radius, 0.0),
                App.Vector(x + tx * marker_radius, y + ty * marker_radius, 0.0),
            ),
            Part.makeLine(
                App.Vector(x - nx * marker_radius, y - ny * marker_radius, 0.0),
                App.Vector(x + nx * marker_radius, y + ny * marker_radius, 0.0),
            ),
        ]
        return Part.Compound(edges)

    def show(self, document, row: dict[str, object], *, radius: float = 5.0):
        """Create or update the visible station marker in one document."""

        if document is None:
            raise RuntimeError("No active document is available for station highlight.")
        shape = self.build_shape(row, radius=radius)
        if shape is None:
            return None
        adapter = ProjectDocumentAdapter(document)
        with adapter.transaction("Update station highlight", recompute=True):
            obj = adapter.find_object(
                name="V1StationHighlight",
                v1_object_type="V1StationHighlight",
            )
            if obj is None:
                obj = adapter.ensure_object(
                    "Part::Feature",
                    "V1StationHighlight",
                    fallback_type_id="App::FeaturePython",
                )
            adapter.ensure_property(
                obj,
                "App::PropertyString",
                "V1ObjectType",
                "CorridorRoad",
                "v1 object type",
            )
            adapter.set_value(obj, "V1ObjectType", "V1StationHighlight")
            label = str(row.get("label", "") or "Station")
            station = _safe_float(row.get("station", 0.0), 0.0)
            adapter.set_value(obj, "Label", f"Station Highlight - {label}")
            adapter.set_value(obj, "Shape", shape)
            adapter.ensure_property(
                obj,
                "App::PropertyFloat",
                "Station",
                "Stations",
                "highlighted station",
            )
            adapter.set_value(obj, "Station", float(station))
            adapter.route_to_project_tree(obj)
            self._style(obj)
        return obj

    @staticmethod
    def _style(obj) -> None:
        vobj = getattr(obj, "ViewObject", None)
        if vobj is None:
            return
        try:
            vobj.Visibility = True
            vobj.DisplayMode = "Wireframe"
            vobj.LineColor = (1.0, 0.05, 0.02)
            vobj.LineWidth = 6.0
            vobj.PointColor = (1.0, 0.05, 0.02)
            vobj.PointSize = 10.0
        except Exception:
            pass


def station_highlight_shape(row: dict[str, object], *, radius: float = 5.0):
    """Compatibility function for building one station marker shape."""

    return StationHighlightPresentationService().build_shape(row, radius=radius)


def show_station_highlight(document, row: dict[str, object], *, radius: float = 5.0):
    """Compatibility function for showing one station marker."""

    return StationHighlightPresentationService().show(document, row, radius=radius)


def _safe_float(value, fallback: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(fallback)
