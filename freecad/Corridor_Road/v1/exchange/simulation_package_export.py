"""Export adapters for persisted v1 simulation package objects."""

from __future__ import annotations

import json
from pathlib import Path


def simulation_package_payload(simulation_package_obj, geometry_file_refs=None) -> dict[str, object]:
    """Build a serializable payload from one persisted v1 SimulationPackageOutput object."""

    if simulation_package_obj is None:
        raise RuntimeError("A v1 SimulationPackageOutput object is required for export.")
    solid_output_refs = list(getattr(simulation_package_obj, "SolidOutputRefs", []) or [])
    geometry_by_output_ref = {
        str(row.get("output_ref", "") or ""): dict(row)
        for row in list(geometry_file_refs or [])
        if str(row.get("output_ref", "") or "")
    }
    solid_rows = []
    for index, output_ref in enumerate(solid_output_refs):
        output_ref_text = str(output_ref or "")
        geometry_ref = geometry_by_output_ref.get(output_ref_text, {})
        solid_rows.append(
            {
                "output_ref": output_ref_text,
                "target_families": _split_refs(_list_value(getattr(simulation_package_obj, "SolidTargetFamilies", []), index, "")),
                "structure_refs": _split_refs(_list_value(getattr(simulation_package_obj, "SolidStructureRefs", []), index, "")),
                "drainage_refs": _split_refs(_list_value(getattr(simulation_package_obj, "SolidDrainageRefs", []), index, "")),
                "flow_route_refs": _split_refs(_list_value(getattr(simulation_package_obj, "SolidFlowRouteRefs", []), index, "")),
                "material_refs": _split_refs(_list_value(getattr(simulation_package_obj, "SolidMaterialRefs", []), index, "")),
                "source_refs": _split_refs(_list_value(getattr(simulation_package_obj, "SolidSourceRefs", []), index, "")),
                "volume": _float_list_value(getattr(simulation_package_obj, "SolidVolumes", []), index),
                "shape_valid": _bool_value(_list_value(getattr(simulation_package_obj, "SolidShapeValidStatuses", []), index, "")),
                "geometry_object_ref": str(geometry_ref.get("object_ref", output_ref_text) or output_ref_text),
                "geometry_file": str(geometry_ref.get("geometry_file", "") or ""),
                "geometry_format": str(geometry_ref.get("format", "") or ""),
                "geometry_status": str(geometry_ref.get("status", "not_exported") or "not_exported"),
            }
        )
    return {
        "schema_version": int(getattr(simulation_package_obj, "SchemaVersion", 1) or 1),
        "project_id": str(getattr(simulation_package_obj, "ProjectId", "") or ""),
        "simulation_package_output_id": str(getattr(simulation_package_obj, "SimulationPackageOutputId", "") or ""),
        "package_status": str(getattr(simulation_package_obj, "PackageStatus", "") or "blocked"),
        "simulation_ready": bool(getattr(simulation_package_obj, "SimulationReady", False)),
        "simulation_qa_output_ref": str(getattr(simulation_package_obj, "SimulationQaOutputRef", "") or ""),
        "terrain_context": {
            "status": str(getattr(simulation_package_obj, "TerrainStatus", "") or "missing"),
            "ref": str(getattr(simulation_package_obj, "TerrainRef", "") or ""),
            "bound_box": _bound_box_list(str(getattr(simulation_package_obj, "TerrainBoundBox", "") or "")),
        },
        "drainage_readiness": {
            "status": str(getattr(simulation_package_obj, "DrainageReadinessStatus", "") or "missing"),
            "source_status": str(getattr(simulation_package_obj, "DrainageSourceStatus", "") or "missing"),
            "flow_route_count": int(getattr(simulation_package_obj, "DrainageFlowRouteCount", 0) or 0),
            "capture_only_route_count": int(getattr(simulation_package_obj, "DrainageCaptureOnlyRouteCount", 0) or 0),
            "pipe_candidate_count": int(getattr(simulation_package_obj, "DrainagePipeCandidateCount", 0) or 0),
            "unresolved_port_route_count": int(getattr(simulation_package_obj, "DrainageUnresolvedPortRouteCount", 0) or 0),
            "missing_element_route_count": int(getattr(simulation_package_obj, "DrainageMissingElementRouteCount", 0) or 0),
            "lined_ditch_target_count": int(getattr(simulation_package_obj, "DrainageLinedDitchTargetCount", 0) or 0),
            "pipe_segment_target_count": int(getattr(simulation_package_obj, "DrainagePipeSegmentTargetCount", 0) or 0),
            "pipeline_network_target_count": int(getattr(simulation_package_obj, "DrainagePipelineNetworkTargetCount", 0) or 0),
            "structure_body_target_count": int(getattr(simulation_package_obj, "DrainageStructureBodyTargetCount", 0) or 0),
            "built_output_count": int(getattr(simulation_package_obj, "DrainageBuiltOutputCount", 0) or 0),
            "network_fuse_status": str(getattr(simulation_package_obj, "DrainageNetworkFuseStatus", "") or "not_available"),
        },
        "intersection_trim": {
            "status": str(getattr(simulation_package_obj, "IntersectionTrimStatus", "") or "not_available"),
            "result_ref": str(getattr(simulation_package_obj, "IntersectionTrimResultRef", "") or ""),
            "boundary_pair_count": int(getattr(simulation_package_obj, "IntersectionTrimBoundaryPairCount", 0) or 0),
            "ready_pair_count": int(getattr(simulation_package_obj, "IntersectionTrimReadyPairCount", 0) or 0),
            "blocked_pair_count": int(getattr(simulation_package_obj, "IntersectionTrimBlockedPairCount", 0) or 0),
            "handoff_status": str(getattr(simulation_package_obj, "IntersectionTrimHandoffStatus", "") or "not_available"),
            "fuse_candidate": {
                "status": str(getattr(simulation_package_obj, "IntersectionTrimFuseStatus", "") or "not_available"),
                "ref": str(getattr(simulation_package_obj, "IntersectionTrimFuseCandidateRef", "") or ""),
                "source_count": int(getattr(simulation_package_obj, "IntersectionTrimFuseSourceCount", 0) or 0),
                "face_count": int(getattr(simulation_package_obj, "IntersectionTrimFuseFaceCount", 0) or 0),
                "open_edge_count": int(getattr(simulation_package_obj, "IntersectionTrimFuseOpenEdgeCount", 0) or 0),
                "source_refs": list(getattr(simulation_package_obj, "IntersectionTrimFuseSourceRefs", []) or []),
            },
            "handoff_chain": {
                "refs": list(getattr(simulation_package_obj, "IntersectionTrimHandoffChainRefs", []) or []),
                "stage_statuses": list(getattr(simulation_package_obj, "IntersectionTrimHandoffStageStatuses", []) or []),
            },
            "pair_rows": _intersection_trim_pair_rows(simulation_package_obj),
        },
        "intersection_handoff": {
            "readiness_status": str(getattr(simulation_package_obj, "IntersectionHandoffReadinessStatus", "") or "not_available"),
            "final_quality_status": str(getattr(simulation_package_obj, "IntersectionHandoffFinalQualityStatus", "") or "not_available"),
            "digital_twin_handoff": str(getattr(simulation_package_obj, "IntersectionHandoffStatus", "") or "not_available"),
            "target_count": int(getattr(simulation_package_obj, "IntersectionHandoffTargetCount", 0) or 0),
            "patch_target_count": int(getattr(simulation_package_obj, "IntersectionHandoffPatchTargetCount", 0) or 0),
            "accepted_zone_target_count": int(getattr(simulation_package_obj, "IntersectionHandoffAcceptedZoneTargetCount", 0) or 0),
            "replacement_gate_status": str(getattr(simulation_package_obj, "IntersectionHandoffReplacementGateStatus", "") or ""),
            "replacement_readiness_status": str(getattr(simulation_package_obj, "IntersectionHandoffReplacementReadinessStatus", "") or ""),
            "replacement_handoff_preference": str(getattr(simulation_package_obj, "IntersectionHandoffReplacementHandoffPreference", "") or ""),
            "downstream_selected_role": str(getattr(simulation_package_obj, "IntersectionHandoffDownstreamSelectedRole", "") or ""),
            "legacy_patch_review_visibility": str(getattr(simulation_package_obj, "IntersectionHandoffLegacyPatchReviewVisibility", "") or ""),
            "legacy_patch_compatibility_audit_summary": str(getattr(simulation_package_obj, "IntersectionHandoffLegacyPatchCompatibilityAuditSummary", "") or ""),
            "replacement_blocker_kind": str(getattr(simulation_package_obj, "IntersectionHandoffReplacementBlockerKind", "") or ""),
        },
        "output_count": int(getattr(simulation_package_obj, "OutputCount", 0) or 0),
        "total_volume": float(getattr(simulation_package_obj, "TotalVolume", 0.0) or 0.0),
        "target_families": list(getattr(simulation_package_obj, "TargetFamilies", []) or []),
        "missing_contexts": list(getattr(simulation_package_obj, "MissingContexts", []) or []),
        "diagnostic_kinds": list(getattr(simulation_package_obj, "DiagnosticKinds", []) or []),
        "geometry_files": list(geometry_file_refs or []),
        "solid_rows": solid_rows,
        "source_refs": list(getattr(simulation_package_obj, "SourceRefs", []) or []),
        "result_refs": list(getattr(simulation_package_obj, "ResultRefs", []) or []),
    }


def export_simulation_package_to_json(path: str | Path, simulation_package_obj, *, document=None, export_geometry: bool = True) -> dict[str, object]:
    """Write one persisted v1 SimulationPackageOutput object to a JSON file."""

    export_path = Path(path)
    if not str(export_path):
        raise RuntimeError("An export path is required.")
    export_path.parent.mkdir(parents=True, exist_ok=True)
    geometry_file_refs = []
    if export_geometry and document is not None:
        geometry_file_refs = _export_geometry_files(export_path, simulation_package_obj, document=document)
    payload = simulation_package_payload(simulation_package_obj, geometry_file_refs=geometry_file_refs)
    with export_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    exported_geometry_count = len([row for row in geometry_file_refs if str(row.get("status", "") or "") == "exported"])
    geometry_file_paths = _exported_geometry_file_paths(export_path, geometry_file_refs)
    return {
        "path": str(export_path),
        "simulation_package_output_id": payload["simulation_package_output_id"],
        "package_status": payload["package_status"],
        "simulation_ready": payload["simulation_ready"],
        "output_count": payload["output_count"],
        "total_volume": payload["total_volume"],
        "terrain_status": payload["terrain_context"]["status"],
        "terrain_ref": payload["terrain_context"]["ref"],
        "intersection_handoff_final_quality_status": payload["intersection_handoff"]["final_quality_status"],
        "intersection_handoff_status": payload["intersection_handoff"]["digital_twin_handoff"],
        "intersection_handoff_replacement_readiness_status": payload["intersection_handoff"]["replacement_readiness_status"],
        "intersection_handoff_replacement_blocker_kind": payload["intersection_handoff"]["replacement_blocker_kind"],
        "intersection_trim_status": payload["intersection_trim"]["status"],
        "intersection_trim_fuse_status": payload["intersection_trim"]["fuse_candidate"]["status"],
        "intersection_trim_handoff_status": payload["intersection_trim"]["handoff_status"],
        "solid_row_count": len(list(payload["solid_rows"] or [])),
        "diagnostic_count": len(list(payload["diagnostic_kinds"] or [])),
        "geometry_file_count": exported_geometry_count,
        "geometry_export_status": _geometry_export_status(geometry_file_refs),
        "geometry_directory": str(export_path.with_name(f"{export_path.stem}_geometry")) if geometry_file_refs else "",
        "geometry_file_paths": geometry_file_paths,
    }


def _export_geometry_files(export_path: Path, simulation_package_obj, *, document=None) -> list[dict[str, str]]:
    solid_output_refs = [str(value or "") for value in list(getattr(simulation_package_obj, "SolidOutputRefs", []) or []) if str(value or "")]
    if not solid_output_refs:
        return []
    geometry_dir = export_path.with_name(f"{export_path.stem}_geometry")
    geometry_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for output_ref in solid_output_refs:
        obj = _find_document_object(document, output_ref)
        filename = f"{_safe_file_stem(output_ref)}.brep"
        geometry_path = geometry_dir / filename
        relative_path = _relative_path(geometry_path, export_path.parent)
        row = {
            "output_ref": output_ref,
            "object_ref": output_ref,
            "geometry_file": relative_path,
            "format": "brep",
            "status": "not_exported",
            "message": "",
        }
        shape = getattr(obj, "Shape", None) if obj is not None else None
        if obj is None:
            row["status"] = "missing_object"
            row["message"] = "The referenced watertight solid output object was not found in the document."
        elif not _shape_is_exportable(shape):
            row["status"] = "missing_shape"
            row["message"] = "The referenced watertight solid output object does not have an exportable solid Shape."
        else:
            try:
                shape.exportBrep(str(geometry_path))
                row["status"] = "exported"
            except Exception as exc:
                row["status"] = "export_error"
                row["message"] = str(exc)
        rows.append(row)
    return rows


def _find_document_object(document, object_ref: str):
    if document is None:
        return None
    try:
        return document.getObject(str(object_ref or ""))
    except Exception:
        return None


def _shape_is_exportable(shape) -> bool:
    if shape is None or not hasattr(shape, "exportBrep"):
        return False
    try:
        solids = list(getattr(shape, "Solids", []) or [])
        if solids and float(getattr(shape, "Volume", 0.0) or 0.0) > 0.0:
            return True
    except Exception:
        pass
    return False


def _safe_file_stem(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value or "").strip())
    safe = "_".join(part for part in safe.split("_") if part)
    return safe or "watertight_solid_output"


def _relative_path(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except Exception:
        return path.as_posix()


def _geometry_export_status(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "not_available"
    statuses = [str(row.get("status", "") or "") for row in rows]
    if all(status == "exported" for status in statuses):
        return "exported"
    if any(status == "exported" for status in statuses):
        return "partial"
    return "not_available"


def _exported_geometry_file_paths(export_path: Path, rows: list[dict[str, str]]) -> list[str]:
    paths: list[str] = []
    for row in rows:
        if str(row.get("status", "") or "") != "exported":
            continue
        geometry_file = str(row.get("geometry_file", "") or "")
        if geometry_file:
            paths.append(str(export_path.parent / geometry_file))
    return paths


def _split_refs(value: str) -> list[str]:
    return [part for part in str(value or "").split("|") if part]


def _intersection_trim_pair_rows(simulation_package_obj) -> list[dict[str, object]]:
    pair_ids = list(getattr(simulation_package_obj, "IntersectionTrimPairIds", []) or [])
    count = max(
        len(pair_ids),
        len(list(getattr(simulation_package_obj, "IntersectionTrimPairStatuses", []) or [])),
        len(list(getattr(simulation_package_obj, "IntersectionTrimPatchOutputRefs", []) or [])),
        len(list(getattr(simulation_package_obj, "IntersectionTrimRoadOutputRefs", []) or [])),
        len(list(getattr(simulation_package_obj, "IntersectionTrimDistancesXY", []) or [])),
    )
    rows: list[dict[str, object]] = []
    for index in range(count):
        rows.append(
            {
                "boundary_pair_id": _list_value(pair_ids, index, f"intersection-trim-boundary:{index + 1}"),
                "status": _list_value(getattr(simulation_package_obj, "IntersectionTrimPairStatuses", []), index, ""),
                "patch_output_ref": _list_value(getattr(simulation_package_obj, "IntersectionTrimPatchOutputRefs", []), index, ""),
                "road_output_ref": _list_value(getattr(simulation_package_obj, "IntersectionTrimRoadOutputRefs", []), index, ""),
                "distance_xy": _float_list_value(getattr(simulation_package_obj, "IntersectionTrimDistancesXY", []), index),
                "patch_segment_xyz": _segment_list(_list_value(getattr(simulation_package_obj, "IntersectionTrimPatchSegmentsXYZ", []), index, "")),
                "road_segment_xyz": _segment_list(_list_value(getattr(simulation_package_obj, "IntersectionTrimRoadSegmentsXYZ", []), index, "")),
            }
        )
    return rows


def _segment_list(value: object) -> list[float]:
    output = []
    for token in str(value or "").replace(",", "|").split("|"):
        try:
            output.append(float(token))
        except Exception:
            output.append(0.0)
    while len(output) < 6:
        output.append(0.0)
    return output[:6]


def _bound_box_list(value: str) -> list[float]:
    output = []
    for part in str(value or "").split("|"):
        if not part:
            continue
        try:
            output.append(float(part))
        except Exception:
            return []
    return output if len(output) == 6 else []


def _list_value(values, index: int, default: str = "") -> str:
    try:
        values_list = list(values or [])
        return str(values_list[index]) if index < len(values_list) else str(default)
    except Exception:
        return str(default)


def _float_list_value(values, index: int) -> float:
    try:
        values_list = list(values or [])
        return float(values_list[index]) if index < len(values_list) else 0.0
    except Exception:
        return 0.0


def _bool_value(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}
