"""FreeCAD Part mapper for topology-validated watertight solids."""

from __future__ import annotations

from dataclasses import dataclass

from ...common.diagnostics import DiagnosticMessage
from ...models.result.applied_section_solid_profile import AppliedSectionSolidProfileSet
from ...models.result.solid_edge_network import SolidEdgeNetwork


@dataclass(frozen=True)
class WatertightSolidPartMappingResult:
    """Shape mapping result for one watertight solid target."""

    target_ref: str
    validation_status: str
    is_watertight: bool = False
    is_valid_solid: bool = False
    volume: float = 0.0
    face_count: int = 0
    edge_count: int = 0
    shell_shape: object | None = None
    solid_shape: object | None = None
    diagnostic_rows: list[DiagnosticMessage] | None = None


class WatertightSolidPartMapper:
    """Map validated topology rows to FreeCAD Part shapes without repairing topology."""

    def map_edge_network(
        self,
        edge_network: SolidEdgeNetwork,
        profile_set: AppliedSectionSolidProfileSet,
    ) -> WatertightSolidPartMappingResult:
        """Create a Part shell and solid from validated face rows."""

        target_ref = str(getattr(edge_network, "target_ref", "") or getattr(profile_set, "target_ref", "") or "")
        gate_diagnostics = _topology_gate_diagnostics(edge_network)
        if gate_diagnostics:
            return _result(
                target_ref,
                validation_status="blocked",
                face_count=int(getattr(edge_network, "face_count", 0) or 0),
                edge_count=int(getattr(edge_network, "edge_count", 0) or 0),
                diagnostics=gate_diagnostics,
            )

        try:
            import FreeCAD  # type: ignore
            import Part  # type: ignore
        except Exception as exc:
            return _result(
                target_ref,
                validation_status="blocked",
                face_count=int(getattr(edge_network, "face_count", 0) or 0),
                edge_count=int(getattr(edge_network, "edge_count", 0) or 0),
                diagnostics=[
                    DiagnosticMessage(
                        severity="error",
                        kind="part_module_unavailable",
                        message="FreeCAD Part mapping requires FreeCAD and Part modules.",
                        notes=str(exc),
                    )
                ],
            )

        node_points = _node_points(profile_set, FreeCAD)
        diagnostics: list[DiagnosticMessage] = []
        faces = []
        for face_row in list(getattr(edge_network, "face_rows", []) or []):
            face_id = str(getattr(face_row, "face_id", "") or "solid-face")
            node_ids = list(getattr(face_row, "node_ids", []) or [])
            missing = [node_id for node_id in node_ids if node_id not in node_points]
            if missing:
                diagnostics.append(
                    DiagnosticMessage(
                        severity="error",
                        kind="missing_face_node_geometry",
                        message="A topology face references nodes that are not present in the profile set.",
                        notes=f"face={face_id};missing={','.join(missing)}",
                    )
                )
                continue
            part_faces, face_diagnostics = _part_faces_for_topology_face(
                face_id=face_id,
                node_ids=node_ids,
                node_points=node_points,
                part_module=Part,
            )
            faces.extend(part_faces)
            diagnostics.extend(face_diagnostics)
        if any(row.severity == "error" for row in diagnostics):
            return _result(
                target_ref,
                validation_status="error",
                face_count=len(faces),
                edge_count=int(getattr(edge_network, "edge_count", 0) or 0),
                diagnostics=diagnostics,
            )
        try:
            shell = Part.Shell(faces)
            solid = Part.Solid(shell)
        except Exception as exc:
            return _result(
                target_ref,
                validation_status="error",
                face_count=len(faces),
                edge_count=int(getattr(edge_network, "edge_count", 0) or 0),
                diagnostics=[
                    DiagnosticMessage(
                        severity="error",
                        kind="part_solid_creation_failed",
                        message="FreeCAD Part failed to create a Shell or Solid from validated topology faces.",
                        notes=str(exc),
                    )
                ],
            )

        is_valid = bool(getattr(solid, "isValid", lambda: False)())
        volume = max(float(getattr(solid, "Volume", 0.0) or 0.0), 0.0)
        diagnostics.extend(_shape_diagnostics(shell, solid, is_valid=is_valid, volume=volume))
        status = "ok" if is_valid and volume > 0.0 and not any(row.severity == "error" for row in diagnostics) else "error"
        return _result(
            target_ref,
            validation_status=status,
            is_watertight=status == "ok",
            is_valid_solid=is_valid,
            volume=volume,
            face_count=len(faces),
            edge_count=int(getattr(edge_network, "edge_count", 0) or 0),
            shell_shape=shell,
            solid_shape=solid,
            diagnostics=diagnostics,
        )


def _topology_gate_diagnostics(edge_network: SolidEdgeNetwork) -> list[DiagnosticMessage]:
    diagnostics = []
    if str(getattr(edge_network, "validation_status", "") or "") != "ok":
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="topology_gate_failed",
                message="Part mapping requires a topology edge network with validation_status=ok.",
                notes=str(getattr(edge_network, "target_ref", "") or ""),
            )
        )
    if not bool(getattr(edge_network, "is_shell_closed", False)):
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="shell_not_closed",
                message="Part mapping requires every topology edge to be shared by exactly two faces.",
                notes=str(getattr(edge_network, "target_ref", "") or ""),
            )
        )
    return diagnostics


def _node_points(profile_set: AppliedSectionSolidProfileSet, freecad_module) -> dict[str, object]:
    output: dict[str, object] = {}
    for profile in list(getattr(profile_set, "profile_rows", []) or []):
        for node in list(getattr(profile, "node_rows", []) or []):
            node_id = str(getattr(node, "node_id", "") or "")
            if not node_id:
                continue
            output[node_id] = freecad_module.Vector(
                float(getattr(node, "x", 0.0) or 0.0),
                float(getattr(node, "y", 0.0) or 0.0),
                float(getattr(node, "z", 0.0) or 0.0),
            )
    return output


def _part_faces_for_topology_face(
    *,
    face_id: str,
    node_ids: list[str],
    node_points: dict[str, object],
    part_module,
) -> tuple[list[object], list[DiagnosticMessage]]:
    points = [node_points[node_id] for node_id in node_ids]
    try:
        return [_part_face(points, part_module)], []
    except Exception as direct_exc:
        direct_error = str(direct_exc)

    try:
        triangle_faces = []
        for index in range(1, len(points) - 1):
            triangle_faces.append(_part_face([points[0], points[index], points[index + 1]], part_module))
        if triangle_faces:
            return triangle_faces, [
                DiagnosticMessage(
                    severity="warning",
                    kind="part_face_triangulated",
                    message="FreeCAD Part required triangulation for a topology face.",
                    notes=f"face={face_id};triangles={len(triangle_faces)};direct_error={direct_error}",
                )
            ]
    except Exception as triangulation_exc:
        return [], [
            DiagnosticMessage(
                severity="error",
                kind="part_face_creation_failed",
                message="FreeCAD Part failed to create a face from a topology face row.",
                notes=f"face={face_id};direct={direct_error};triangulation={triangulation_exc}",
            )
        ]

    return [], [
        DiagnosticMessage(
            severity="error",
            kind="part_face_creation_failed",
            message="FreeCAD Part failed to create a face from a topology face row.",
            notes=f"face={face_id};direct={direct_error};triangulation=no triangles created",
        )
    ]


def _part_face(points: list[object], part_module):
    polygon = part_module.makePolygon(points + [points[0]])
    return part_module.Face(polygon)


def _shape_diagnostics(shell, solid, *, is_valid: bool, volume: float) -> list[DiagnosticMessage]:
    diagnostics: list[DiagnosticMessage] = []
    shell_is_valid = bool(getattr(shell, "isValid", lambda: False)())
    if not shell_is_valid:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="invalid_part_shell",
                message="FreeCAD Part shell is not valid.",
            )
        )
    if not is_valid:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="invalid_part_solid",
                message="FreeCAD Part solid is not valid.",
            )
        )
    if volume <= 0.0:
        diagnostics.append(
            DiagnosticMessage(
                severity="error",
                kind="non_positive_solid_volume",
                message="FreeCAD Part solid volume must be positive.",
            )
        )
    return diagnostics


def _result(
    target_ref: str,
    *,
    validation_status: str,
    is_watertight: bool = False,
    is_valid_solid: bool = False,
    volume: float = 0.0,
    face_count: int = 0,
    edge_count: int = 0,
    shell_shape: object | None = None,
    solid_shape: object | None = None,
    diagnostics: list[DiagnosticMessage] | None = None,
) -> WatertightSolidPartMappingResult:
    return WatertightSolidPartMappingResult(
        target_ref=target_ref,
        validation_status=validation_status,
        is_watertight=bool(is_watertight),
        is_valid_solid=bool(is_valid_solid),
        volume=max(float(volume or 0.0), 0.0),
        face_count=int(face_count or 0),
        edge_count=int(edge_count or 0),
        shell_shape=shell_shape,
        solid_shape=solid_shape,
        diagnostic_rows=list(diagnostics or []),
    )
