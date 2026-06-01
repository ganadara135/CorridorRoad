"""Civil 3D LandXML import parser facade for Parametric Road v1."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from .landxml_import_contracts import (
    LandXMLAlignmentCandidate,
    LandXMLAlignmentElementCandidate,
    LandXMLImportDiagnostic,
    LandXMLImportResult,
    LandXMLImportSummary,
    LandXMLPointCandidate,
    LandXMLProfileCandidate,
    LandXMLProfilePointCandidate,
    LandXMLSurfaceCandidate,
)


SUPPORTED_PRODUCER_TOKEN = "civil 3d"


def scan_landxml_file(path: str | Path) -> LandXMLImportResult:
    """Read a LandXML file and return parsed candidates without mutating FreeCAD."""

    source = Path(path)
    diagnostics: list[LandXMLImportDiagnostic] = []
    try:
        root = ET.parse(source).getroot()
    except Exception as exc:
        summary = LandXMLImportSummary(source_path=str(source))
        return LandXMLImportResult(
            summary=summary,
            diagnostics=(
                LandXMLImportDiagnostic(
                    severity="error",
                    code="landxml_parse_failed",
                    message="LandXML file could not be parsed.",
                    context=str(exc),
                ),
            ),
        )

    result = scan_landxml_root(root, source_path=str(source))
    diagnostics.extend(result.diagnostics)
    return LandXMLImportResult(
        summary=result.summary,
        alignments=result.alignments,
        profiles=result.profiles,
        surfaces=result.surfaces,
        cgpoints=result.cgpoints,
        diagnostics=tuple(diagnostics),
    )


def scan_landxml_text(text: str, *, source_path: str = "") -> LandXMLImportResult:
    """Parse LandXML text and return discovered Civil 3D import candidates."""

    try:
        root = ET.fromstring(text)
    except Exception as exc:
        return LandXMLImportResult(
            summary=LandXMLImportSummary(source_path=source_path),
            diagnostics=(
                LandXMLImportDiagnostic(
                    severity="error",
                    code="landxml_parse_failed",
                    message="LandXML text could not be parsed.",
                    context=str(exc),
                ),
            ),
        )
    return scan_landxml_root(root, source_path=source_path)


def scan_landxml_root(root: ET.Element, *, source_path: str = "") -> LandXMLImportResult:
    """Scan an ElementTree root and return import candidates."""

    diagnostics: list[LandXMLImportDiagnostic] = []
    version = str(root.attrib.get("version", "") or "")
    producer = _detect_producer(root)
    supported = SUPPORTED_PRODUCER_TOKEN in producer.lower()
    if supported:
        diagnostics.append(
            LandXMLImportDiagnostic(
                severity="info",
                code="landxml_civil3d_source_detected",
                message="Autodesk Civil 3D LandXML source detected.",
                context=producer,
            )
        )
    else:
        diagnostics.append(
            LandXMLImportDiagnostic(
                severity="warning",
                code="landxml_unsupported_producer",
                message="Only Autodesk Civil 3D LandXML is supported in this phase.",
                context=producer or "unknown producer",
            )
        )

    alignments, alignment_diagnostics = _parse_alignments(root)
    profiles, profile_diagnostics = _parse_profiles(root)
    surfaces, surface_diagnostics = _parse_surfaces(root)
    cgpoints, cgpoint_diagnostics = _parse_cgpoints(root)
    diagnostics.extend(alignment_diagnostics)
    diagnostics.extend(profile_diagnostics)
    diagnostics.extend(surface_diagnostics)
    diagnostics.extend(cgpoint_diagnostics)

    summary = LandXMLImportSummary(
        source_path=source_path,
        landxml_version=version,
        detected_producer=producer,
        supported_producer=supported,
        linear_unit=_detect_linear_unit(root),
        alignment_count=len(alignments),
        profile_count=len(profiles),
        surface_count=len(surfaces),
        cgpoint_count=len(cgpoints),
    )
    return LandXMLImportResult(
        summary=summary,
        alignments=tuple(alignments),
        profiles=tuple(profiles),
        surfaces=tuple(surfaces),
        cgpoints=tuple(cgpoints),
        diagnostics=tuple(diagnostics),
    )


def _parse_alignments(root: ET.Element) -> tuple[list[LandXMLAlignmentCandidate], list[LandXMLImportDiagnostic]]:
    candidates: list[LandXMLAlignmentCandidate] = []
    diagnostics: list[LandXMLImportDiagnostic] = []
    for index, alignment in enumerate(_iter_by_name(root, "Alignment"), start=1):
        alignment_id = _attr_first(alignment, "oID", "OID", "name") or f"alignment-{index:02d}"
        name = _attr_first(alignment, "name", "desc") or alignment_id
        start_station = _safe_float(_attr_first(alignment, "staStart", "startSta", "staStartRaw"))
        elements: list[LandXMLAlignmentElementCandidate] = []
        coord_geom = _first_child(alignment, "CoordGeom")
        if coord_geom is not None:
            for elem_index, child in enumerate(list(coord_geom), start=1):
                tag = _local_name(child.tag)
                if tag not in {"Line", "Curve", "Spiral", "IrregularLine"}:
                    continue
                kind = tag.lower()
                length = _safe_float(_attr_first(child, "length", "len"), default=0.0) or 0.0
                payload = dict(child.attrib)
                start = _point_child_text(child, "Start")
                end = _point_child_text(child, "End")
                if start:
                    payload["start"] = start
                if end:
                    payload["end"] = end
                if tag == "Line" and not length and start and end:
                    length = _distance_xy(start, end)
                if tag in {"Spiral", "IrregularLine"}:
                    diagnostics.append(
                        LandXMLImportDiagnostic(
                            severity="warning",
                            code="landxml_unsupported_geometry",
                            message=f"{tag} geometry is detected but not fully supported in the first importer.",
                            context=f"{name}:{elem_index}",
                        )
                    )
                elements.append(
                    LandXMLAlignmentElementCandidate(
                        element_id=f"{alignment_id}:element-{elem_index:03d}",
                        kind=kind,
                        length=length,
                        payload=payload,
                    )
                )
        candidates.append(
            LandXMLAlignmentCandidate(
                alignment_id=str(alignment_id),
                name=str(name),
                start_station=start_station,
                elements=tuple(elements),
            )
        )
    return candidates, diagnostics


def _parse_profiles(root: ET.Element) -> tuple[list[LandXMLProfileCandidate], list[LandXMLImportDiagnostic]]:
    candidates: list[LandXMLProfileCandidate] = []
    diagnostics: list[LandXMLImportDiagnostic] = []
    for alignment in _iter_by_name(root, "Alignment"):
        alignment_id = _attr_first(alignment, "oID", "OID", "name") or ""
        for profile_index, profile in enumerate(_children_by_name(alignment, "Profile"), start=1):
            profile_id = _attr_first(profile, "oID", "OID", "name") or f"profile-{profile_index:02d}"
            profile_name = _attr_first(profile, "name", "desc") or profile_id
            points: list[LandXMLProfilePointCandidate] = []
            for prof_align in _children_by_name(profile, "ProfAlign"):
                for pvi_index, pvi in enumerate(_children_by_name(prof_align, "PVI"), start=1):
                    values = _float_text_values(pvi.text)
                    if len(values) < 2:
                        diagnostics.append(
                            LandXMLImportDiagnostic(
                                severity="warning",
                                code="landxml_profile_pvi_invalid",
                                message="Profile PVI row does not contain station and elevation.",
                                context=f"{profile_name}:{pvi_index}",
                            )
                        )
                        continue
                    points.append(
                        LandXMLProfilePointCandidate(
                            point_id=f"{profile_id}:pvi-{pvi_index:03d}",
                            station=values[0],
                            elevation=values[1],
                        )
                    )
            candidates.append(
                LandXMLProfileCandidate(
                    profile_id=str(profile_id),
                    name=str(profile_name),
                    alignment_id=str(alignment_id),
                    points=tuple(points),
                )
            )
    return candidates, diagnostics


def _parse_surfaces(root: ET.Element) -> tuple[list[LandXMLSurfaceCandidate], list[LandXMLImportDiagnostic]]:
    candidates: list[LandXMLSurfaceCandidate] = []
    diagnostics: list[LandXMLImportDiagnostic] = []
    for surface_index, surface in enumerate(_iter_by_name(root, "Surface"), start=1):
        surface_id = _attr_first(surface, "oID", "OID", "name") or f"surface-{surface_index:02d}"
        name = _attr_first(surface, "name", "desc") or surface_id
        points: list[LandXMLPointCandidate] = []
        faces: list[tuple[str, str, str]] = []
        for pnt in _iter_descendants_by_name(surface, "P"):
            point = _parse_point_element(pnt, fallback_id=f"{surface_id}:p-{len(points) + 1:03d}")
            if point is not None:
                points.append(point)
        point_ids = {point.point_id for point in points}
        for face_index, face in enumerate(_iter_descendants_by_name(surface, "F"), start=1):
            ids = tuple((face.text or "").split())
            if len(ids) < 3:
                diagnostics.append(
                    LandXMLImportDiagnostic(
                        severity="warning",
                        code="landxml_invalid_tin_face",
                        message="TIN face does not contain three point references.",
                        context=f"{name}:{face_index}",
                    )
                )
                continue
            tri = (ids[0], ids[1], ids[2])
            if any(point_id not in point_ids for point_id in tri):
                diagnostics.append(
                    LandXMLImportDiagnostic(
                        severity="warning",
                        code="landxml_invalid_tin_face",
                        message="TIN face references a missing point id.",
                        context=f"{name}:{face_index}",
                    )
                )
                continue
            faces.append(tri)
        candidates.append(
            LandXMLSurfaceCandidate(
                surface_id=str(surface_id),
                name=str(name),
                points=tuple(points),
                faces=tuple(faces),
            )
        )
    return candidates, diagnostics


def _parse_cgpoints(root: ET.Element) -> tuple[list[LandXMLPointCandidate], list[LandXMLImportDiagnostic]]:
    points: list[LandXMLPointCandidate] = []
    diagnostics: list[LandXMLImportDiagnostic] = []
    for index, cgpoint in enumerate(_iter_by_name(root, "CgPoint"), start=1):
        point = _parse_point_element(cgpoint, fallback_id=f"cgpoint-{index:03d}")
        if point is None:
            diagnostics.append(
                LandXMLImportDiagnostic(
                    severity="warning",
                    code="landxml_cgpoint_invalid",
                    message="CgPoint does not contain usable xyz coordinates.",
                    context=str(index),
                )
            )
            continue
        points.append(point)
    return points, diagnostics


def _detect_producer(root: ET.Element) -> str:
    for app in _iter_by_name(root, "Application"):
        parts = [
            _attr_first(app, "name", "manufacturer", "manufacturerURL"),
            _attr_first(app, "version"),
        ]
        text = " ".join(str(part) for part in parts if part)
        if text:
            return text
    return ""


def _detect_linear_unit(root: ET.Element) -> str:
    for units in _iter_by_name(root, "Units"):
        for child in list(units):
            tag = _local_name(child.tag).lower()
            if tag in {"metric", "imperial"}:
                return _attr_first(child, "linearUnit", "linear") or tag
    return ""


def _parse_point_element(elem: ET.Element, *, fallback_id: str) -> LandXMLPointCandidate | None:
    values = _float_text_values(elem.text)
    if len(values) < 2:
        return None
    point_id = _attr_first(elem, "id", "name", "pntRef") or fallback_id
    desc = _attr_first(elem, "desc", "code") or ""
    z = values[2] if len(values) >= 3 else 0.0
    return LandXMLPointCandidate(point_id=str(point_id), x=values[0], y=values[1], z=z, description=str(desc))


def _iter_by_name(root: ET.Element, name: str):
    for elem in root.iter():
        if _local_name(elem.tag) == name:
            yield elem


def _iter_descendants_by_name(root: ET.Element, name: str):
    for elem in root.iter():
        if elem is root:
            continue
        if _local_name(elem.tag) == name:
            yield elem


def _children_by_name(root: ET.Element, name: str):
    return [child for child in list(root) if _local_name(child.tag) == name]


def _first_child(root: ET.Element, name: str) -> ET.Element | None:
    for child in list(root):
        if _local_name(child.tag) == name:
            return child
    return None


def _local_name(tag: str) -> str:
    return str(tag).split("}", 1)[-1]


def _attr_first(elem: ET.Element, *names: str) -> str:
    for name in names:
        value = elem.attrib.get(name)
        if value is not None:
            return str(value)
    return ""


def _safe_float(value: object, default: float | None = None) -> float | None:
    try:
        return float(value)
    except Exception:
        return default


def _float_text_values(text: str | None) -> list[float]:
    values: list[float] = []
    for part in str(text or "").replace(",", " ").split():
        try:
            values.append(float(part))
        except Exception:
            continue
    return values


def _point_child_text(elem: ET.Element, child_name: str) -> tuple[float, float, float] | None:
    child = _first_child(elem, child_name)
    if child is None:
        return None
    values = _float_text_values(child.text)
    if len(values) < 2:
        return None
    z = values[2] if len(values) >= 3 else 0.0
    return (values[0], values[1], z)


def _distance_xy(start: tuple[float, float, float], end: tuple[float, float, float]) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    return (dx * dx + dy * dy) ** 0.5
