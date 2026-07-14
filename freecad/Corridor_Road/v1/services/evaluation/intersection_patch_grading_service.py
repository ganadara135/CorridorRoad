"""Evaluate non-roundabout Intersection patch grading policy."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ...models.result.intersection_patch_grading import (
    IntersectionPatchGradingResult,
)


VALID_GRADING_MODES = {
    "flatten_intersection",
    "keep_primary_crown",
    "blend_primary_side",
    "use_normal_superelevation",
}


@dataclass(frozen=True)
class IntersectionPatchGradingRequest:
    vertices: tuple[object, ...]
    intersection_model: object | None
    intersection_id: str


class IntersectionPatchGradingService:
    """Select and apply accepted Intersection grading source policy."""

    def evaluate(
        self,
        request: IntersectionPatchGradingRequest,
    ) -> IntersectionPatchGradingResult:
        policy = self.select_policy(
            request.intersection_model,
            request.intersection_id,
        )
        mode = self.normalized_mode(policy)
        source_vertices = list(request.vertices)
        plane = self.grading_plane(source_vertices, policy)
        vertices = self.apply_vertices(
            source_vertices,
            policy,
            grading_plane=plane,
        )
        max_delta = _max_abs_delta(
            [float(getattr(vertex, "z", 0.0) or 0.0) for vertex in source_vertices],
            [float(getattr(vertex, "z", 0.0) or 0.0) for vertex in vertices],
        )
        diagnostics = []
        if policy is None:
            diagnostics.append("intersection_grading_policy_missing_default_applied")
        if mode == "blend_primary_side" and plane is None:
            primary_ref = str(
                getattr(policy, "primary_alignment_ref", "") or ""
            ).strip()
            primary_found = any(
                primary_ref
                and f"alignment={primary_ref}"
                in str(getattr(vertex, "notes", "") or "")
                for vertex in source_vertices
            )
            diagnostics.append(
                "intersection_grading_blend_primary_fallback"
                if primary_found
                else "intersection_grading_blend_primary_missing"
            )
        return IntersectionPatchGradingResult(
            status="ready",
            intersection_id=str(request.intersection_id or ""),
            grading_policy=policy,
            grading_mode=mode,
            vertex_rows=tuple(vertices),
            grading_plane=plane,
            max_z_delta=max_delta,
            diagnostic_rows=tuple(diagnostics),
        )

    def select_policy(self, intersection_model: object | None, intersection_id: str):
        target = str(intersection_id or "").strip()
        rows = (
            list(getattr(intersection_model, "grading_policy_rows", []) or [])
            if intersection_model is not None
            else []
        )
        for row in rows:
            if (
                str(getattr(row, "intersection_id", "") or "") == target
                and str(getattr(row, "status", "") or "active") != "disabled"
            ):
                return row
        return None

    def normalized_mode(self, grading_policy: object | None) -> str:
        mode = str(
            getattr(grading_policy, "mode", "") or "use_normal_superelevation"
        ).strip()
        return mode if mode in VALID_GRADING_MODES else "use_normal_superelevation"

    def apply_vertices(
        self,
        vertices: list[object],
        grading_policy: object | None,
        *,
        grading_plane: tuple[float, float, float] | None = None,
    ) -> list[object]:
        mode = self.normalized_mode(grading_policy)
        if mode == "use_normal_superelevation":
            return vertices
        if mode == "flatten_intersection":
            if not vertices:
                return vertices
            target_z = sum(
                float(getattr(vertex, "z", 0.0) or 0.0) for vertex in vertices
            ) / len(vertices)
            return [
                replace(
                    vertex,
                    z=target_z,
                    notes=(
                        f"{getattr(vertex, 'notes', '')}; "
                        f"intersection_grading={mode}"
                    ),
                )
                for vertex in vertices
            ]
        if mode == "keep_primary_crown":
            return [
                replace(
                    vertex,
                    notes=(
                        f"{getattr(vertex, 'notes', '')}; "
                        f"intersection_grading={mode}"
                    ),
                )
                for vertex in vertices
            ]
        if grading_plane is None:
            grading_plane = self.grading_plane(vertices, grading_policy)
        if grading_plane is not None:
            return [
                replace(
                    vertex,
                    z=_plane_z(
                        grading_plane,
                        float(getattr(vertex, "x", 0.0) or 0.0),
                        float(getattr(vertex, "y", 0.0) or 0.0),
                    ),
                    notes=(
                        f"{getattr(vertex, 'notes', '')}; "
                        f"intersection_grading={mode}; "
                        "blend_basis=primary_side_plane"
                    ),
                )
                for vertex in vertices
            ]
        primary_ref = str(
            getattr(grading_policy, "primary_alignment_ref", "") or ""
        ).strip()
        primary_vertices = [
            vertex
            for vertex in vertices
            if primary_ref
            and f"alignment={primary_ref}"
            in str(getattr(vertex, "notes", "") or "")
        ]
        if not primary_vertices:
            return [
                replace(
                    vertex,
                    notes=(
                        f"{getattr(vertex, 'notes', '')}; "
                        f"intersection_grading={mode}; "
                        "blend_basis=missing_primary"
                    ),
                )
                for vertex in vertices
            ]
        primary_z = sum(
            float(getattr(vertex, "z", 0.0) or 0.0)
            for vertex in primary_vertices
        ) / len(primary_vertices)
        output = []
        for vertex in vertices:
            notes = str(getattr(vertex, "notes", "") or "")
            z = float(getattr(vertex, "z", 0.0) or 0.0)
            if primary_ref and f"alignment={primary_ref}" in notes:
                output.append(
                    replace(
                        vertex,
                        notes=(
                            f"{notes}; intersection_grading={mode}; "
                            "blend_basis=primary_preserved"
                        ),
                    )
                )
            else:
                output.append(
                    replace(
                        vertex,
                        z=(z + primary_z) / 2.0,
                        notes=(
                            f"{notes}; intersection_grading={mode}; "
                            "blend_basis=primary_side_half"
                        ),
                    )
                )
        return output

    def grading_plane(
        self,
        vertices: list[object],
        grading_policy: object | None,
    ) -> tuple[float, float, float] | None:
        if self.normalized_mode(grading_policy) != "blend_primary_side":
            return None
        if len(vertices) < 3:
            return None
        return _fit_z_plane(
            [
                (
                    float(getattr(vertex, "x", 0.0) or 0.0),
                    float(getattr(vertex, "y", 0.0) or 0.0),
                    float(getattr(vertex, "z", 0.0) or 0.0),
                )
                for vertex in vertices
            ]
        )


def _plane_z(plane: tuple[float, float, float], x: float, y: float) -> float:
    a, b, c = plane
    return float(a) * float(x) + float(b) * float(y) + float(c)


def _fit_z_plane(
    samples: list[tuple[float, float, float]],
) -> tuple[float, float, float] | None:
    valid = [(float(x), float(y), float(z)) for x, y, z in samples]
    if len(valid) < 3:
        return None
    sx = sum(x for x, _y, _z in valid)
    sy = sum(y for _x, y, _z in valid)
    sz = sum(z for _x, _y, z in valid)
    sxx = sum(x * x for x, _y, _z in valid)
    syy = sum(y * y for _x, y, _z in valid)
    sxy = sum(x * y for x, y, _z in valid)
    sxz = sum(x * z for x, _y, z in valid)
    syz = sum(y * z for _x, y, z in valid)
    count = float(len(valid))
    return _solve_3x3(
        ((sxx, sxy, sx), (sxy, syy, sy), (sx, sy, count)),
        (sxz, syz, sz),
    )


def _solve_3x3(matrix, values) -> tuple[float, float, float] | None:
    coefficients = [[float(value) for value in row] for row in matrix]
    constants = [float(value) for value in values]
    for pivot in range(3):
        pivot_row = max(
            range(pivot, 3),
            key=lambda row: abs(coefficients[row][pivot]),
        )
        if abs(coefficients[pivot_row][pivot]) <= 1.0e-12:
            return None
        if pivot_row != pivot:
            coefficients[pivot], coefficients[pivot_row] = (
                coefficients[pivot_row],
                coefficients[pivot],
            )
            constants[pivot], constants[pivot_row] = (
                constants[pivot_row],
                constants[pivot],
            )
        pivot_value = coefficients[pivot][pivot]
        for column in range(pivot, 3):
            coefficients[pivot][column] /= pivot_value
        constants[pivot] /= pivot_value
        for row in range(3):
            if row == pivot:
                continue
            factor = coefficients[row][pivot]
            if abs(factor) <= 1.0e-12:
                continue
            for column in range(pivot, 3):
                coefficients[row][column] -= factor * coefficients[pivot][column]
            constants[row] -= factor * constants[pivot]
    return (constants[0], constants[1], constants[2])


def _max_abs_delta(before: list[float], after: list[float]) -> float:
    values = [
        abs(float(before_value) - float(after_value))
        for before_value, after_value in zip(before, after)
    ]
    return max(values) if values else 0.0
