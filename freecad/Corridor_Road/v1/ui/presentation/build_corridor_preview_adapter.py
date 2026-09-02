"""FreeCAD presentation adapters for Build Parametric previews."""

from __future__ import annotations


class BuildCorridorPreviewAdapter:
    """Own preview properties, cleanup, and diagnostic marker objects."""

    @staticmethod
    def set_string(obj, name: str, value: str) -> None:
        _set_property(obj, "App::PropertyString", name, str(value or ""))

    @staticmethod
    def set_integer(obj, name: str, value: int) -> None:
        _set_property(obj, "App::PropertyInteger", name, int(value or 0))

    @staticmethod
    def set_string_list(obj, name: str, values: list[str]) -> None:
        _set_property(
            obj,
            "App::PropertyStringList",
            name,
            [str(value or "") for value in list(values or [])],
        )

    @staticmethod
    def set_float(obj, name: str, value: float) -> None:
        _set_property(obj, "App::PropertyFloat", name, float(value or 0.0))

    @staticmethod
    def remove_object(document, object_name: str) -> None:
        if document is None:
            return
        try:
            obj = document.getObject(str(object_name or ""))
            if obj is not None:
                document.removeObject(obj.Name)
        except Exception:
            pass

    def create_marker_compound(
        self,
        *,
        document,
        object_name: str,
        label: str,
        points: list[tuple[float, float, float]],
        radius: float,
        color: tuple[float, float, float],
        surface,
        corridor_model,
        record_kind: str = "v1_review_issue",
        object_type: str = "ReviewIssue",
        issue_kind: str = "slope_face_tie_in",
        connect_points: bool = False,
        app_module=None,
        part_module=None,
    ):
        """Create presentation-only marker geometry from result coordinates."""

        if document is None or app_module is None or part_module is None:
            return None
        try:
            obj = document.getObject(object_name)
        except Exception:
            return None
        if not points:
            self.remove_object(document, object_name)
            return None
        shapes = []
        if bool(connect_points) and len(points) >= 2:
            for start, end in zip(points, points[1:]):
                if _same_xyz(start, end):
                    continue
                try:
                    shapes.append(
                        part_module.makeLine(
                            app_module.Vector(*_xyz(start)),
                            app_module.Vector(*_xyz(end)),
                        )
                    )
                except Exception:
                    pass
        for point in points:
            try:
                shapes.append(
                    part_module.makeSphere(
                        float(radius),
                        app_module.Vector(*_xyz(point)),
                    )
                )
            except Exception:
                pass
        if not shapes:
            return None
        if obj is None:
            try:
                obj = document.addObject("Part::Feature", object_name)
            except Exception:
                return None
        try:
            obj.Shape = part_module.makeCompound(shapes)
            obj.Label = label
        except Exception:
            return obj
        self.set_string(obj, "CRRecordKind", record_kind or "v1_review_issue")
        self.set_string(obj, "V1ObjectType", object_type or "ReviewIssue")
        self.set_string(obj, "IssueKind", issue_kind or "slope_face_tie_in")
        self.set_string(
            obj,
            "SurfaceId",
            str(getattr(surface, "surface_id", "") or ""),
        )
        self.set_string(
            obj,
            "CorridorId",
            str(getattr(corridor_model, "corridor_id", "") or ""),
        )
        self.set_integer(obj, "MarkerCount", len(points))
        try:
            view = getattr(obj, "ViewObject", None)
            if view is not None:
                view.Visibility = True
                view.ShapeColor = color
                view.PointColor = color
                view.LineColor = color
                view.Transparency = 0
        except Exception:
            pass
        return obj


def _set_property(obj, property_type: str, name: str, value) -> None:
    if obj is None:
        return
    try:
        if not hasattr(obj, name):
            obj.addProperty(property_type, name, "CorridorRoad", name)
        setattr(obj, name, value)
    except Exception:
        pass


def _xyz(point) -> tuple[float, float, float]:
    values = tuple(point or ())
    return (
        float(values[0]) if len(values) > 0 else 0.0,
        float(values[1]) if len(values) > 1 else 0.0,
        float(values[2]) if len(values) > 2 else 0.0,
    )


def _same_xyz(first, second, tolerance: float = 1.0e-9) -> bool:
    a = _xyz(first)
    b = _xyz(second)
    return all(abs(a[index] - b[index]) <= tolerance for index in range(3))


__all__ = ["BuildCorridorPreviewAdapter"]
