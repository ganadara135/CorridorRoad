"""IFC export adapters for CorridorRoad v1."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

from .exchange_package_export import exchange_package_payload


def export_exchange_package_to_ifc(path: str | Path, exchange_package_obj) -> dict[str, object]:
    """Write one persisted v1 structure ExchangePackage to a lightweight IFC4 handoff file."""

    export_path = Path(path)
    if not str(export_path):
        raise RuntimeError("An export path is required.")
    payload = exchange_package_payload(exchange_package_obj)
    blocking = _blocking_export_diagnostics(payload)
    if blocking:
        kinds = ", ".join(sorted({str(row.get("kind", "") or "") for row in blocking if row.get("kind")}))
        raise RuntimeError(f"Structure IFC export is not ready: {len(blocking)} blocking diagnostic(s). {kinds}")
    text = exchange_package_ifc_text(payload)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(text, encoding="utf-8", newline="\n")
    return {
        "path": str(export_path),
        "exchange_output_id": payload["exchange_output_id"],
        "structure_solid_count": len(list(payload.get("structure_solid_rows", []) or [])),
        "structure_solid_segment_count": len(list(payload.get("structure_solid_segment_rows", []) or [])),
        "export_readiness_status": payload.get("export_readiness_status", ""),
        "export_diagnostic_count": int(payload.get("export_diagnostic_count", 0) or 0),
        "ifc_entity_count": text.count("\n#"),
    }


def exchange_package_ifc_text(payload: dict[str, object]) -> str:
    """Build a deterministic IFC4 STEP handoff from normalized structure solid rows."""

    rows = list(payload.get("structure_solid_rows", []) or [])
    segments_by_parent = _segments_by_parent(payload)
    diagnostics_by_output = _diagnostics_by_output_object_id(payload)
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('CorridorRoad v1 structure exchange handoff'),'2;1');",
        f"FILE_NAME('{_step_string(str(payload.get('exchange_output_id', '') or 'corridorroad-structure-export'))}.ifc','',('CorridorRoad'),('CorridorRoad'),'CorridorRoad v1','CorridorRoad','');",
        "FILE_SCHEMA(('IFC4'));",
        "ENDSEC;",
        "DATA;",
    ]

    next_id = 1
    origin = next_id
    lines.append(f"#{origin}=IFCCARTESIANPOINT((0.,0.,0.));")
    next_id += 1
    placement = next_id
    lines.append(f"#{placement}=IFCAXIS2PLACEMENT3D(#{origin},$,$);")
    next_id += 1
    context = next_id
    lines.append(f"#{context}=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#{placement},$);")
    next_id += 1
    length_unit = next_id
    lines.append(f"#{length_unit}=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);")
    next_id += 1
    volume_unit = next_id
    lines.append(f"#{volume_unit}=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);")
    next_id += 1
    unit_assignment = next_id
    lines.append(f"#{unit_assignment}=IFCUNITASSIGNMENT((#{length_unit},#{volume_unit}));")
    next_id += 1
    project = next_id
    project_name = _step_string(str(payload.get("project_id", "") or "CorridorRoad Project"))
    lines.append(
        f"#{project}=IFCPROJECT('{_ifc_guid(str(payload.get('exchange_output_id', '') or 'project'))}',$,'{project_name}',$,$,$,$,(#{context}),#{unit_assignment});"
    )
    next_id += 1

    element_ids: list[int] = []
    for index, row in enumerate(rows, start=1):
        structure_id = str(row.get("structure_id", "") or f"structure:{index}")
        geometry_spec_id = str(row.get("geometry_spec_id", "") or "")
        solid_kind = str(row.get("solid_kind", "") or "structure_envelope_solid")
        tag = str(row.get("output_object_id", "") or structure_id)
        output_object_id = str(row.get("output_object_id", "") or "")
        segment_rows = segments_by_parent.get(output_object_id, [])
        diagnostic_rows = diagnostics_by_output.get(output_object_id, [])
        readiness_status = _readiness_status(diagnostic_rows)
        diagnostic_kinds = ",".join(
            sorted({str(item.get("kind", "") or "") for item in diagnostic_rows if str(item.get("kind", "") or "")})
        )
        width = max(_float(row.get("width")), 0.001)
        height = max(_float(row.get("height")), 0.001)
        length = max(_float(row.get("length")), 0.001)
        placement_x = _float(row.get("placement_x"), _float(row.get("station_start")))
        placement_y = _float(row.get("placement_y"))
        placement_z = _float(row.get("placement_z"))
        tangent_direction_deg = _float(row.get("tangent_direction_deg"))
        start_x = _float(row.get("start_x"), placement_x)
        start_y = _float(row.get("start_y"), placement_y)
        start_z = _float(row.get("start_z"), placement_z)
        end_x = _float(row.get("end_x"), placement_x + length)
        end_y = _float(row.get("end_y"), placement_y)
        end_z = _float(row.get("end_z"), placement_z)
        start_tangent_direction_deg = _float(row.get("start_tangent_direction_deg"), tangent_direction_deg)
        end_tangent_direction_deg = _float(row.get("end_tangent_direction_deg"), tangent_direction_deg)
        tangent_radians = math.radians(tangent_direction_deg)
        ref_x = math.cos(tangent_radians)
        ref_y = math.sin(tangent_radians)
        description = (
            f"geometry_spec_id={geometry_spec_id};"
            f"station={_float(row.get('station_start')):.3f}-{_float(row.get('station_end')):.3f};"
            f"volume={_float(row.get('volume')):.3f}"
        )

        local_point = next_id
        next_id += 1
        lines.append(f"#{local_point}=IFCCARTESIANPOINT(({placement_x:.6f},{placement_y:.6f},{placement_z:.6f}));")
        local_z_direction = next_id
        next_id += 1
        lines.append(f"#{local_z_direction}=IFCDIRECTION((0.,0.,1.));")
        local_ref_direction = next_id
        next_id += 1
        lines.append(f"#{local_ref_direction}=IFCDIRECTION(({ref_x:.9f},{ref_y:.9f},0.));")
        local_axis = next_id
        next_id += 1
        lines.append(f"#{local_axis}=IFCAXIS2PLACEMENT3D(#{local_point},#{local_z_direction},#{local_ref_direction});")
        local_placement = next_id
        next_id += 1
        lines.append(f"#{local_placement}=IFCLOCALPLACEMENT($,#{local_axis});")
        swept_solids: list[int] = []
        if len(segment_rows) > 1:
            for segment in segment_rows:
                swept_solid, next_id = _append_segment_swept_solid(
                    lines,
                    next_id,
                    context_x=placement_x,
                    context_y=placement_y,
                    context_z=placement_z,
                    profile_name=f"{structure_id}:segment:{int(_float(segment.get('segment_index')))}:profile",
                    width=max(_float(segment.get("width"), width), 0.001),
                    height=max(_float(segment.get("height"), height), 0.001),
                    length=max(_float(segment.get("length")), 0.001),
                    start_x=_float(segment.get("start_x"), placement_x),
                    start_y=_float(segment.get("start_y"), placement_y),
                    start_z=_float(segment.get("start_z"), placement_z),
                    tangent_direction_deg=_float(segment.get("start_tangent_direction_deg"), tangent_direction_deg),
                )
                swept_solids.append(swept_solid)
        else:
            swept_solid, next_id = _append_segment_swept_solid(
                lines,
                next_id,
                context_x=placement_x,
                context_y=placement_y,
                context_z=placement_z,
                profile_name=f"{structure_id}:profile",
                width=width,
                height=height,
                length=length,
                start_x=placement_x,
                start_y=placement_y,
                start_z=placement_z,
                tangent_direction_deg=tangent_direction_deg,
            )
            swept_solids.append(swept_solid)
        shape_representation = next_id
        next_id += 1
        lines.append(
            f"#{shape_representation}=IFCSHAPEREPRESENTATION(#{context},'Body','SweptSolid',({','.join(f'#{item}' for item in swept_solids)}));"
        )
        product_shape = next_id
        next_id += 1
        lines.append(f"#{product_shape}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{shape_representation}));")

        element = next_id
        next_id += 1
        element_ids.append(element)
        lines.append(
            f"#{element}=IFCBUILDINGELEMENTPROXY('{_ifc_guid(structure_id)}',$,'{_step_string(structure_id)}','{_step_string(description)}','{_step_string(solid_kind)}',#{local_placement},#{product_shape},'{_step_string(tag)}',.USERDEFINED.);"
        )

        property_ids: list[int] = []
        for name, value, value_kind in (
            ("StructureId", structure_id, "IFCTEXT"),
            ("GeometrySpecId", geometry_spec_id, "IFCTEXT"),
            ("SourceRegionRef", str(row.get("region_ref", "") or ""), "IFCTEXT"),
            ("SourceAssemblyRef", str(row.get("assembly_ref", "") or ""), "IFCTEXT"),
            ("SourceStructureRef", str(row.get("structure_ref", "") or structure_id), "IFCTEXT"),
            ("SolidKind", solid_kind, "IFCTEXT"),
            ("Material", str(row.get("material", "") or ""), "IFCTEXT"),
            ("StationStart", _float(row.get("station_start")), "IFCLENGTHMEASURE"),
            ("StationEnd", _float(row.get("station_end")), "IFCLENGTHMEASURE"),
            ("Width", _float(row.get("width")), "IFCLENGTHMEASURE"),
            ("Height", _float(row.get("height")), "IFCLENGTHMEASURE"),
            ("Length", _float(row.get("length")), "IFCLENGTHMEASURE"),
            ("Volume", _float(row.get("volume")), "IFCVOLUMEMEASURE"),
            ("SegmentCount", len(segment_rows), "IFCINTEGER"),
            ("GeometrySegmentation", "segmented" if len(segment_rows) > 1 else "single_segment", "IFCTEXT"),
            ("IFCGeometryMode", "segmented_swept_solid" if len(segment_rows) > 1 else "single_swept_solid", "IFCTEXT"),
            ("ExportReadinessStatus", readiness_status, "IFCTEXT"),
            ("ExportDiagnosticCount", len(diagnostic_rows), "IFCINTEGER"),
            ("ExportDiagnosticKinds", diagnostic_kinds, "IFCTEXT"),
            ("PlacementX", placement_x, "IFCLENGTHMEASURE"),
            ("PlacementY", placement_y, "IFCLENGTHMEASURE"),
            ("PlacementZ", placement_z, "IFCLENGTHMEASURE"),
            ("TangentDirectionDeg", tangent_direction_deg, "IFCREAL"),
            ("StartX", start_x, "IFCLENGTHMEASURE"),
            ("StartY", start_y, "IFCLENGTHMEASURE"),
            ("StartZ", start_z, "IFCLENGTHMEASURE"),
            ("EndX", end_x, "IFCLENGTHMEASURE"),
            ("EndY", end_y, "IFCLENGTHMEASURE"),
            ("EndZ", end_z, "IFCLENGTHMEASURE"),
            ("StartTangentDirectionDeg", start_tangent_direction_deg, "IFCREAL"),
            ("EndTangentDirectionDeg", end_tangent_direction_deg, "IFCREAL"),
        ):
            prop_id = next_id
            next_id += 1
            property_ids.append(prop_id)
            lines.append(f"#{prop_id}=IFCPROPERTYSINGLEVALUE('{name}',$,{_ifc_value(value, value_kind)},$);")
        pset = next_id
        next_id += 1
        lines.append(
            f"#{pset}=IFCPROPERTYSET('{_ifc_guid(structure_id + ':pset')}',$,'CorridorRoadStructureSolid',$,({','.join(f'#{item}' for item in property_ids)}));"
        )
        rel = next_id
        next_id += 1
        lines.append(
            f"#{rel}=IFCRELDEFINESBYPROPERTIES('{_ifc_guid(structure_id + ':rel')}',$,$,$,(#{element}),#{pset});"
        )

    if element_ids:
        rel_project = next_id
        lines.append(
            f"#{rel_project}=IFCRELAGGREGATES('{_ifc_guid(str(payload.get('exchange_output_id', '') or 'package') + ':aggregates')}',$,$,$,#{project},({','.join(f'#{item}' for item in element_ids)}));"
        )

    lines.extend(["ENDSEC;", "END-ISO-10303-21;", ""])
    return "\n".join(lines)


def _ifc_guid(seed: str) -> str:
    return hashlib.sha1(str(seed or "corridorroad").encode("utf-8")).hexdigest()[:22]


def _step_string(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace("'", "''")


def _ifc_value(value, value_kind: str) -> str:
    if value_kind == "IFCTEXT":
        return f"IFCTEXT('{_step_string(str(value or ''))}')"
    if value_kind == "IFCREAL":
        return f"IFCREAL({_float(value):.6f})"
    if value_kind == "IFCINTEGER":
        return f"IFCINTEGER({int(_float(value))})"
    return f"{value_kind}({_float(value):.6f})"


def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _segments_by_parent(payload: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in list(payload.get("structure_solid_segment_rows", []) or []):
        parent = str(row.get("parent_output_object_id", "") or "")
        if not parent:
            continue
        grouped.setdefault(parent, []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: int(_float(item.get("segment_index"))))
    return grouped


def _diagnostics_by_output_object_id(payload: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in list(payload.get("export_diagnostic_rows", []) or []):
        output_object_id = str(row.get("output_object_id", "") or "")
        if not output_object_id:
            continue
        grouped.setdefault(output_object_id, []).append(row)
    return grouped


def _blocking_export_diagnostics(payload: dict[str, object]) -> list[dict[str, object]]:
    return [
        row
        for row in list(payload.get("export_diagnostic_rows", []) or [])
        if str(row.get("severity", "") or "").strip().lower() == "error"
    ]


def _readiness_status(diagnostics: list[dict[str, object]]) -> str:
    severities = {str(row.get("severity", "") or "").strip().lower() for row in list(diagnostics or [])}
    if "error" in severities:
        return "error"
    if "warning" in severities:
        return "warning"
    return "ready"


def _append_segment_swept_solid(
    lines: list[str],
    next_id: int,
    *,
    context_x: float,
    context_y: float,
    context_z: float,
    profile_name: str,
    width: float,
    height: float,
    length: float,
    start_x: float,
    start_y: float,
    start_z: float,
    tangent_direction_deg: float,
) -> tuple[int, int]:
    profile_point = next_id
    next_id += 1
    lines.append(f"#{profile_point}=IFCCARTESIANPOINT((0.,0.));")
    profile_axis = next_id
    next_id += 1
    lines.append(f"#{profile_axis}=IFCAXIS2PLACEMENT2D(#{profile_point},$);")
    profile = next_id
    next_id += 1
    lines.append(f"#{profile}=IFCRECTANGLEPROFILEDEF(.AREA.,'{_step_string(profile_name)}',#{profile_axis},{width:.6f},{height:.6f});")
    solid_origin = next_id
    next_id += 1
    lines.append(f"#{solid_origin}=IFCCARTESIANPOINT(({start_x - context_x:.6f},{start_y - context_y:.6f},{start_z - context_z:.6f}));")
    solid_z_direction = next_id
    next_id += 1
    lines.append(f"#{solid_z_direction}=IFCDIRECTION((0.,0.,1.));")
    tangent_radians = math.radians(tangent_direction_deg)
    solid_ref_direction = next_id
    next_id += 1
    lines.append(f"#{solid_ref_direction}=IFCDIRECTION(({math.cos(tangent_radians):.9f},{math.sin(tangent_radians):.9f},0.));")
    solid_axis = next_id
    next_id += 1
    lines.append(f"#{solid_axis}=IFCAXIS2PLACEMENT3D(#{solid_origin},#{solid_z_direction},#{solid_ref_direction});")
    extrusion_direction = next_id
    next_id += 1
    lines.append(f"#{extrusion_direction}=IFCDIRECTION((1.,0.,0.));")
    swept_solid = next_id
    next_id += 1
    lines.append(f"#{swept_solid}=IFCEXTRUDEDAREASOLID(#{profile},#{solid_axis},#{extrusion_direction},{length:.6f});")
    return swept_solid, next_id
