"""Shared FreeCAD document persistence boundary for CorridorRoad v1."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator

from ...objects.obj_project import find_project, route_to_v1_tree


class ProjectDocumentAdapter:
    """Centralize v1 document lookup, persistence, routing, and write boundaries."""

    def __init__(self, document) -> None:
        if document is None:
            raise ValueError("ProjectDocumentAdapter requires a document.")
        self.document = document
        self._transaction_depth = 0

    def project(self):
        """Return the CorridorRoad project object in this document, if present."""

        return find_project(self.document)

    def find_object(
        self,
        *,
        name: str = "",
        name_prefix: str = "",
        v1_object_type: str = "",
        predicate: Callable[[object], bool] | None = None,
    ):
        """Find one document object using stable identity before presentation labels."""

        exact_name = str(name or "").strip()
        if exact_name:
            getter = getattr(self.document, "getObject", None)
            candidate = getter(exact_name) if callable(getter) else None
            if candidate is not None and self._matches(
                candidate,
                name_prefix=name_prefix,
                v1_object_type=v1_object_type,
                predicate=predicate,
            ):
                return candidate
        for candidate in list(getattr(self.document, "Objects", []) or []):
            if self._matches(
                candidate,
                name_prefix=name_prefix or exact_name,
                v1_object_type=v1_object_type,
                predicate=predicate,
            ):
                return candidate
        return None

    def ensure_object(self, type_id: str, name: str, *, fallback_type_id: str = ""):
        """Return an existing named object or create it with an optional fallback type."""

        existing = self.find_object(name=name)
        if existing is not None:
            return existing
        return self.create_object(type_id, name, fallback_type_id=fallback_type_id)

    def create_object(self, type_id: str, name: str, *, fallback_type_id: str = ""):
        """Create a new object while preserving FreeCAD's automatic name disambiguation."""

        try:
            return self.document.addObject(str(type_id), str(name))
        except Exception:
            if not str(fallback_type_id or "").strip():
                raise
            return self.document.addObject(str(fallback_type_id), str(name))

    def ensure_property(
        self,
        obj,
        type_id: str,
        name: str,
        group: str = "CorridorRoad",
        description: str = "",
    ) -> bool:
        """Ensure one FreeCAD property exists, returning whether it is available."""

        if obj is None:
            return False
        if hasattr(obj, str(name)):
            return True
        try:
            obj.addProperty(str(type_id), str(name), str(group), str(description))
            return hasattr(obj, str(name))
        except Exception:
            return False

    @staticmethod
    def set_value(obj, name: str, value: object) -> bool:
        """Set one existing object value without hiding whether the write succeeded."""

        if obj is None:
            return False
        try:
            setattr(obj, str(name), value)
            return True
        except Exception:
            return False

    def route_to_project_tree(self, obj, *, project=None):
        """Route an object through the canonical v1 project-tree policy."""

        owner = project or self.project()
        if owner is None or obj is None:
            return None
        return route_to_v1_tree(owner, obj)

    def remove_stale_objects(
        self,
        *,
        keep_names: set[str] | None = None,
        name_prefixes: tuple[str, ...] = (),
        v1_object_types: tuple[str, ...] = (),
        predicate: Callable[[object], bool] | None = None,
    ) -> list[str]:
        """Remove explicitly selected stale result objects and return removed names."""

        if not name_prefixes and not v1_object_types and predicate is None:
            return []
        keep = {str(value or "") for value in set(keep_names or set())}
        removed: list[str] = []
        for obj in list(getattr(self.document, "Objects", []) or []):
            name = str(getattr(obj, "Name", "") or "")
            if not name or name in keep:
                continue
            selected = bool(name_prefixes and name.startswith(tuple(name_prefixes)))
            if v1_object_types and str(getattr(obj, "V1ObjectType", "") or "") in set(v1_object_types):
                selected = True
            selected = selected or bool(predicate is not None and predicate(obj))
            if not selected:
                continue
            self.document.removeObject(name)
            removed.append(name)
        return removed

    @contextmanager
    def transaction(self, label: str, *, recompute: bool = False) -> Iterator["ProjectDocumentAdapter"]:
        """Apply one deliberate document transaction and optional final recompute."""

        outermost = self._transaction_depth == 0
        opened = False
        if outermost:
            open_transaction = getattr(self.document, "openTransaction", None)
            if callable(open_transaction):
                open_transaction(str(label or "CorridorRoad v1 update"))
                opened = True
        self._transaction_depth += 1
        try:
            yield self
        except Exception:
            if outermost and opened:
                abort = getattr(self.document, "abortTransaction", None)
                if callable(abort):
                    abort()
            raise
        else:
            if outermost and opened:
                commit = getattr(self.document, "commitTransaction", None)
                if callable(commit):
                    commit()
            if outermost and recompute:
                self.recompute()
        finally:
            self._transaction_depth = max(self._transaction_depth - 1, 0)

    def recompute(self) -> bool:
        """Run one explicit document recompute when supported."""

        recompute = getattr(self.document, "recompute", None)
        if not callable(recompute):
            return False
        recompute()
        return True

    @staticmethod
    def _matches(
        obj,
        *,
        name_prefix: str,
        v1_object_type: str,
        predicate: Callable[[object], bool] | None,
    ) -> bool:
        if obj is None:
            return False
        prefix = str(name_prefix or "").strip()
        if prefix and not str(getattr(obj, "Name", "") or "").startswith(prefix):
            return False
        object_type = str(v1_object_type or "").strip()
        if object_type and str(getattr(obj, "V1ObjectType", "") or "") != object_type:
            return False
        return predicate(obj) if predicate is not None else True
