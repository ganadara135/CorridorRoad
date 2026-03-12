"""Virtual module-path mapping for FreeCAD proxy persistence.

FreeCAD can persist Python proxy class module paths in FCStd files.
This module keeps those paths stable by mapping legacy imports to the
canonical addon namespace: ``freecad.Corridor_Road``.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from types import ModuleType

CANONICAL_ROOT = "freecad.Corridor_Road"
CANONICAL_OBJECTS = f"{CANONICAL_ROOT}.objects"
CANONICAL_COMMANDS = f"{CANONICAL_ROOT}.commands"
CANONICAL_UI = f"{CANONICAL_ROOT}.ui"

# Legacy prefixes seen in pre-refactor/local layouts.
_LEGACY_PREFIX_TO_CANONICAL = (
    ("CorridorRoad.freecad.Corridor_Road", CANONICAL_ROOT),
    ("CorridorRoad.freecad", CANONICAL_ROOT),
    ("Corridor_Road", CANONICAL_ROOT),
    ("CorridorRoad", CANONICAL_ROOT),
    ("objects", CANONICAL_OBJECTS),
    ("commands", CANONICAL_COMMANDS),
    ("ui", CANONICAL_UI),
)


def _import_module(name: str) -> ModuleType | None:
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def _set_alias(alias_name: str, target: ModuleType) -> None:
    cur = sys.modules.get(alias_name)
    if cur is None or cur is target:
        sys.modules[alias_name] = target


def _to_canonical_name(module_name: str) -> str:
    for legacy, canonical in _LEGACY_PREFIX_TO_CANONICAL:
        if module_name == legacy:
            return canonical
        prefix = legacy + "."
        if module_name.startswith(prefix):
            suffix = module_name[len(legacy) :]
            return canonical + suffix
    return module_name


def _normalize_proxy_class_module_names(module: ModuleType, from_name: str, to_name: str) -> None:
    if from_name == to_name:
        return
    try:
        values = list(vars(module).values())
    except Exception:
        return
    for value in values:
        if not isinstance(value, type):
            continue
        try:
            if getattr(value, "__module__", "") == from_name:
                value.__module__ = to_name
        except Exception:
            pass


def _iter_proxy_object_module_names() -> list[str]:
    mod = _import_module(CANONICAL_OBJECTS)
    if mod is None:
        return []
    pkg_path = getattr(mod, "__path__", None)
    if not pkg_path:
        return []

    out: list[str] = []
    for info in pkgutil.iter_modules(pkg_path):
        # Proxy-bearing modules in this addon follow obj_*.py naming.
        if info.name.startswith("obj_"):
            out.append(info.name)
    out.sort()
    return out


def _alias_loaded_subtree(alias_prefix: str, canonical_prefix: str) -> None:
    canonical_module = _import_module(canonical_prefix)
    if canonical_module is None:
        return
    _set_alias(alias_prefix, canonical_module)

    loaded = list(sys.modules.items())
    for mod_name, mod in loaded:
        if mod is None:
            continue
        if mod_name == canonical_prefix:
            continue
        if not mod_name.startswith(canonical_prefix + "."):
            continue
        suffix = mod_name[len(canonical_prefix) :]
        _set_alias(alias_prefix + suffix, mod)


def _canonicalize_loaded_modules() -> None:
    loaded = list(sys.modules.items())
    for mod_name, mod in loaded:
        if mod is None:
            continue
        canonical_name = _to_canonical_name(mod_name)
        if canonical_name == mod_name:
            continue
        _set_alias(canonical_name, mod)
        _normalize_proxy_class_module_names(mod, mod_name, canonical_name)


def install_virtual_path_mappings() -> None:
    """Install canonical/legacy alias mapping for proxy module paths."""
    # Ensure canonical package skeleton exists.
    _import_module(CANONICAL_ROOT)
    _import_module(CANONICAL_OBJECTS)
    _import_module(CANONICAL_COMMANDS)
    _import_module(CANONICAL_UI)
    _import_module(f"{CANONICAL_UI}.common")

    # Preload proxy-bearing object modules in canonical namespace.
    for rel_name in _iter_proxy_object_module_names():
        _import_module(f"{CANONICAL_OBJECTS}.{rel_name}")

    # Map legacy package roots to canonical package roots.
    _alias_loaded_subtree("CorridorRoad.freecad.Corridor_Road", CANONICAL_ROOT)
    _alias_loaded_subtree("CorridorRoad.freecad", CANONICAL_ROOT)
    _alias_loaded_subtree("Corridor_Road", CANONICAL_ROOT)
    _alias_loaded_subtree("CorridorRoad", CANONICAL_ROOT)
    _alias_loaded_subtree("objects", CANONICAL_OBJECTS)
    _alias_loaded_subtree("commands", CANONICAL_COMMANDS)
    _alias_loaded_subtree("ui", CANONICAL_UI)

    # If anything got loaded under a legacy name, normalize its class/module path.
    _canonicalize_loaded_modules()
