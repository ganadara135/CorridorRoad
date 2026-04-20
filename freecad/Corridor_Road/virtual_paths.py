# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""Virtual module-path mapping for FreeCAD proxy persistence.

FreeCAD can persist Python proxy class module paths in FCStd files.
This module keeps those paths stable by mapping legacy imports to the
canonical addon namespace: ``freecad.Corridor_Road``.
"""

from __future__ import annotations

import importlib
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

_INSTALL_LEVEL = 0
_INSTALL_BASIC = 1
_INSTALL_EAGER = 2

# Explicit proxy module list to avoid package-wide scans on startup.
_PROXY_OBJECT_MODULES = (
    "obj_alignment",
    "obj_assembly_template",
    "obj_centerline3d",
    "obj_centerline3d_display",
    "obj_corridor",
    "obj_cut_fill_calc",
    "obj_design_grading_surface",
    "obj_design_terrain",
    "obj_fg_display",
    "obj_pointcloud_dem",
    "obj_profile_bundle",
    "obj_project",
    "obj_section_set",
    "obj_stationing",
    "obj_vertical_alignment",
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


def _preload_proxy_modules() -> None:
    for rel_name in _PROXY_OBJECT_MODULES:
        _import_module(f"{CANONICAL_OBJECTS}.{rel_name}")


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


def install_virtual_path_mappings(*, eager: bool = False) -> None:
    """Install canonical/legacy alias mapping for proxy module paths.

    `eager=False` keeps startup light (root/package aliases only).
    `eager=True` additionally preloads proxy-bearing object modules.
    """
    global _INSTALL_LEVEL
    required_level = _INSTALL_EAGER if eager else _INSTALL_BASIC
    if _INSTALL_LEVEL >= required_level:
        return

    # Ensure canonical package skeleton exists.
    _import_module(CANONICAL_ROOT)
    _import_module(CANONICAL_OBJECTS)
    _import_module(CANONICAL_COMMANDS)
    _import_module(CANONICAL_UI)
    _import_module(f"{CANONICAL_UI}.common")

    if eager:
        # Preload proxy-bearing object modules in canonical namespace.
        _preload_proxy_modules()
        
        # Explicitly alias retired modules
        corridor_mod = sys.modules.get(f"{CANONICAL_OBJECTS}.obj_corridor")
        if corridor_mod:
            _set_alias(f"{CANONICAL_OBJECTS}.obj_corridor_loft", corridor_mod)
            _set_alias("obj_corridor_loft", corridor_mod)


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
    _INSTALL_LEVEL = max(_INSTALL_LEVEL, required_level)
