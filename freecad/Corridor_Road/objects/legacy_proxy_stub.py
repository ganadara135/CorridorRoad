# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""Restore-only proxies for retired legacy object types.

A saved document names each object's proxy class by module path and class name, and FreeCAD
drops the proxy for good the first time such a document is saved while the class cannot be
imported (docsV1/V1_LEGACY_PROXY_MIGRATION_DESIGN.md, section 3). The legacy modules therefore
keep their paths and class names, but their classes are these stubs: they hold the state they
were restored with and hand it back unchanged on save, and they compute nothing, so a legacy
object keeps the properties and geometry it was last saved with.
"""

from __future__ import annotations


class RestoreOnlyProxy:
    """Proxy of a retired legacy object type: restores and saves, never recomputes."""

    def __init__(self, obj=None):
        # FreeCAD restores a proxy without calling __init__; only new objects come through here.
        raise RuntimeError(
            f"{type(self).__name__} is a retired legacy object type; "
            "create the corresponding v1 source object instead."
        )

    def loads(self, state):
        self._legacy_state = state
        if isinstance(state, dict):
            # Expose the stored attributes (such as Type, which tree routing reads) as before.
            for key, value in state.items():
                if isinstance(key, str) and key.isidentifier() and not hasattr(type(self), key):
                    setattr(self, key, value)
        return None

    def dumps(self):
        return getattr(self, "_legacy_state", None)

    __setstate__ = loads
    __getstate__ = dumps


class RestoreOnlyViewProvider(RestoreOnlyProxy):
    """View provider of a retired legacy object type: displays the saved geometry as is."""

    def attach(self, vobj):
        # The legacy providers kept vobj.Object here, which FreeCAD could not serialize; the
        # stub keeps nothing, so its state stays what was stored.
        return None
