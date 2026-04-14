# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

import math


LINEAR_UNITS = ("m", "mm", "custom")
DISPLAY_LINEAR_UNITS = ("m", "mm")
DEFAULT_LINEAR_UNIT = "m"
DEFAULT_CUSTOM_LINEAR_SCALE = 1.0


def _safe_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(number):
        return float(default)
    return float(number)


def _safe_positive(value, default: float = 1.0) -> float:
    number = _safe_float(value, default=default)
    if number <= 1.0e-12:
        return float(default)
    return float(number)


def _normalize_linear_unit(value, *, allow_custom: bool, default: str) -> str:
    token = str(value or "").strip().lower()
    valid = LINEAR_UNITS if allow_custom else DISPLAY_LINEAR_UNITS
    if token in valid:
        return token
    fallback = str(default or DEFAULT_LINEAR_UNIT).strip().lower()
    if fallback in valid:
        return fallback
    return "custom" if allow_custom else DEFAULT_LINEAR_UNIT


def _iter_project_candidates(doc):
    if doc is None or not hasattr(doc, "Objects"):
        return []
    out = []
    for obj in list(getattr(doc, "Objects", []) or []):
        try:
            name = str(getattr(obj, "Name", "") or "")
        except Exception:
            name = ""
        try:
            proxy_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
        except Exception:
            proxy_type = ""
        if name.startswith("CorridorRoadProject") or proxy_type == "CorridorRoadProject":
            out.append(obj)
    return out


def _resolve_project(doc_or_project):
    if doc_or_project is None:
        return None

    probe_props = (
        "LinearUnitDisplay",
        "LinearUnitImportDefault",
        "LinearUnitExportDefault",
        "CustomLinearUnitScale",
    )
    try:
        if any(hasattr(doc_or_project, prop) for prop in probe_props):
            return doc_or_project
    except Exception:
        pass

    try:
        doc = getattr(doc_or_project, "Document", None)
        if doc is not None:
            for obj in _iter_project_candidates(doc):
                return obj
    except Exception:
        pass

    if hasattr(doc_or_project, "Objects"):
        for obj in _iter_project_candidates(doc_or_project):
            return obj
    return None

def resolve_project_unit_settings(doc_or_project):
    project = _resolve_project(doc_or_project)
    defaults = {
        "display": DEFAULT_LINEAR_UNIT,
        "import": DEFAULT_LINEAR_UNIT,
        "export": DEFAULT_LINEAR_UNIT,
        "custom_scale": DEFAULT_CUSTOM_LINEAR_SCALE,
    }
    if project is None:
        return dict(defaults)

    display_unit = _normalize_linear_unit(
        getattr(project, "LinearUnitDisplay", defaults["display"]),
        allow_custom=False,
        default=defaults["display"],
    )
    import_unit = _normalize_linear_unit(
        getattr(project, "LinearUnitImportDefault", defaults["import"]),
        allow_custom=True,
        default=defaults["import"],
    )
    export_unit = _normalize_linear_unit(
        getattr(project, "LinearUnitExportDefault", defaults["export"]),
        allow_custom=True,
        default=defaults["export"],
    )
    custom_scale = _safe_positive(
        getattr(project, "CustomLinearUnitScale", defaults["custom_scale"]),
        default=defaults["custom_scale"],
    )
    return {
        "display": display_unit,
        "import": import_unit,
        "export": export_unit,
        "custom_scale": custom_scale,
    }


def get_linear_display_unit(doc_or_project) -> str:
    return str(resolve_project_unit_settings(doc_or_project).get("display", DEFAULT_LINEAR_UNIT))


def get_linear_import_unit(doc_or_project) -> str:
    return str(resolve_project_unit_settings(doc_or_project).get("import", DEFAULT_LINEAR_UNIT))


def get_linear_export_unit(doc_or_project) -> str:
    return str(resolve_project_unit_settings(doc_or_project).get("export", DEFAULT_LINEAR_UNIT))


def get_custom_linear_scale(doc_or_project) -> float:
    return float(resolve_project_unit_settings(doc_or_project).get("custom_scale", DEFAULT_CUSTOM_LINEAR_SCALE))


def meters_per_user_unit(doc_or_project, unit: str = "", *, use_default: str = "import") -> float:
    settings = resolve_project_unit_settings(doc_or_project)
    default_unit = settings.get("import", DEFAULT_LINEAR_UNIT)
    if str(use_default or "").strip().lower() == "export":
        default_unit = settings.get("export", default_unit)
    elif str(use_default or "").strip().lower() == "display":
        default_unit = settings.get("display", default_unit)
    token = _normalize_linear_unit(unit or default_unit, allow_custom=True, default=default_unit)
    if token == "m":
        return 1.0
    if token == "mm":
        return 0.001
    return _safe_positive(settings.get("custom_scale", DEFAULT_CUSTOM_LINEAR_SCALE), default=DEFAULT_CUSTOM_LINEAR_SCALE)


def meters_from_user_length(doc_or_project, value: float, unit: str = "", *, use_default: str = "import") -> float:
    return _safe_float(value, default=0.0) * meters_per_user_unit(doc_or_project, unit=unit, use_default=use_default)


def user_length_from_meters(doc_or_project, meters: float, unit: str = "", *, use_default: str = "display") -> float:
    scale = meters_per_user_unit(doc_or_project, unit=unit, use_default=use_default)
    return _safe_float(meters, default=0.0) / scale


def format_length(doc_or_project, meters: float, digits: int = 3, unit: str = "", *, use_default: str = "display") -> str:
    token = _normalize_linear_unit(
        unit or (
            get_linear_display_unit(doc_or_project)
            if str(use_default or "").strip().lower() == "display"
            else get_linear_import_unit(doc_or_project)
        ),
        allow_custom=True,
        default=DEFAULT_LINEAR_UNIT,
    )
    value = user_length_from_meters(doc_or_project, meters, unit=token, use_default=use_default)
    return f"{value:.{max(0, int(digits))}f} {token}"


def meters_from_internal_length(doc_or_project, internal_value: float) -> float:
    _ = doc_or_project
    return _safe_float(internal_value, default=0.0)


def internal_length_from_meters(doc_or_project, meters: float) -> float:
    _ = doc_or_project
    return _safe_float(meters, default=0.0)


def meters_from_model_length(doc_or_project, model_value: float) -> float:
    """
    Convert model/geometry-space length into canonical meters.

    Geometry carriers are now treated as meter-native too. This helper remains
    as the single boundary API so geometry code does not need to know whether
    a future backend introduces a different model-space representation.
    """
    return meters_from_internal_length(doc_or_project, model_value)


def model_length_from_meters(doc_or_project, meters: float) -> float:
    """
    Convert canonical meters into model/geometry-space length.

    Prefer this helper over ad-hoc conversion math so any future model-space
    bridge remains centralized in unit_policy.
    """
    return internal_length_from_meters(doc_or_project, meters)


def display_length_from_internal(doc_or_project, internal_value: float, unit: str = "", *, use_default: str = "display") -> float:
    meters = meters_from_internal_length(doc_or_project, internal_value)
    return user_length_from_meters(doc_or_project, meters, unit=unit, use_default=use_default)


def internal_length_from_display(doc_or_project, display_value: float, unit: str = "", *, use_default: str = "display") -> float:
    meters = meters_from_user_length(doc_or_project, display_value, unit=unit, use_default=use_default)
    return internal_length_from_meters(doc_or_project, meters)


def format_internal_length(doc_or_project, internal_value: float, digits: int = 3, unit: str = "", *, use_default: str = "display") -> str:
    meters = meters_from_internal_length(doc_or_project, internal_value)
    return format_length(doc_or_project, meters, digits=digits, unit=unit, use_default=use_default)


def display_area_from_internal(doc_or_project, internal_area: float, unit: str = "", *, use_default: str = "display") -> float:
    meters_sq = _safe_float(internal_area, default=0.0)
    meters_per_unit = meters_per_user_unit(doc_or_project, unit=unit, use_default=use_default)
    return meters_sq / (meters_per_unit * meters_per_unit)


def display_volume_from_internal(doc_or_project, internal_volume: float, unit: str = "", *, use_default: str = "display") -> float:
    meters_cu = _safe_float(internal_volume, default=0.0)
    meters_per_unit = meters_per_user_unit(doc_or_project, unit=unit, use_default=use_default)
    return meters_cu / (meters_per_unit * meters_per_unit * meters_per_unit)


def format_internal_area(doc_or_project, internal_area: float, digits: int = 3, unit: str = "", *, use_default: str = "display") -> str:
    token = _normalize_linear_unit(
        unit or get_linear_display_unit(doc_or_project),
        allow_custom=True,
        default=DEFAULT_LINEAR_UNIT,
    )
    value = display_area_from_internal(doc_or_project, internal_area, unit=token, use_default=use_default)
    return f"{value:.{max(0, int(digits))}f} {token}^2"


def format_internal_volume(doc_or_project, internal_volume: float, digits: int = 3, unit: str = "", *, use_default: str = "display") -> str:
    token = _normalize_linear_unit(
        unit or get_linear_display_unit(doc_or_project),
        allow_custom=True,
        default=DEFAULT_LINEAR_UNIT,
    )
    value = display_volume_from_internal(doc_or_project, internal_volume, unit=token, use_default=use_default)
    return f"{value:.{max(0, int(digits))}f} {token}^3"
