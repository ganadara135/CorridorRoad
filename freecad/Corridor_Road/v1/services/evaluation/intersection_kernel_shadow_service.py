"""Shadow comparison of the parametric kernel with the current pipeline (plan section 6).

It only measures. Nothing the production build produces depends on it.
"""

from __future__ import annotations

import math

from dataclasses import dataclass


# targets closer than this agree: well above the micrometre noise of the sampled alignments,
# well below anything a reviewer would call a different boundary
SHADOW_AGREE_TOLERANCE_M = 0.05
# edges are sampled this finely when measuring a distance, so the Hausdorff distance is not
# underestimated along long straight edges
_DENSIFY_STEP_M = 0.5


@dataclass(frozen=True)
class IntersectionKernelShadowComparison:
    status: str
    # largest distance between a kernel curb return fillet and the build's arc at that corner
    fillet_deviation_m: float = -1.0
    # Hausdorff distance between the kernel boundary and the evaluation chain's outer boundary loop
    envelope_deviation_m: float = -1.0
    kernel_area_m2: float = 0.0
    current_area_m2: float = 0.0
    rows: tuple[str, ...] = ()


class IntersectionKernelShadowService:
    """Compare the kernel with two outputs of the current pipeline.

    - fillets: the curb return arcs of the boundary segment result, which the build draws from
      the Applied Sections' tie-in edges;
    - envelope: the outer intersection boundary loop of the evaluation chain, whose straight
      sides come from the arm policy's pavement width.
    A missing target is not compared. The status is `agree` when every compared target is within
    `SHADOW_AGREE_TOLERANCE_M`, `differ` otherwise; a deviation of -1 means not compared.
    """

    def compare(self, kernel_result, *, boundary_segment_result=None, boundary_loop_result=None) -> IntersectionKernelShadowComparison:
        rows = [f"kernel_status|{kernel_result.status}", f"kernel_fingerprint|{kernel_result.input_fingerprint}"]
        rows += [f"leg|{leg.leg_id}|enabled={leg.enabled}|mouth_station={_text(leg.mouth_station)}" for leg in kernel_result.legs]
        rows += [f"corner|{corner.corner_key}|{corner.treatment}|radius={corner.radius_m:.3f}" for corner in kernel_result.corners]
        rows += [f"value|{v.name}|{v.subject}|{v.value}|{v.origin}" for v in kernel_result.resolved_values]
        rows += [f"clip|{ref}|{start:.3f}|{end:.3f}" for ref, start, end in kernel_result.clip_spans]
        rows += [f"diagnostic|{d.as_text()}" for d in kernel_result.diagnostics]
        if kernel_result.status == "not_implemented":
            return IntersectionKernelShadowComparison("skipped", rows=tuple(rows + ["reason|the kernel builds no geometry for this kind yet"]))
        if kernel_result.status == "blocked" or not kernel_result.boundary_xyz:
            return IntersectionKernelShadowComparison("blocked", rows=tuple(rows))

        compared: list[float] = []
        fillet_deviation = _fillet_deviation(kernel_result, boundary_segment_result, rows)
        if fillet_deviation >= 0.0:
            compared.append(fillet_deviation)
        envelope = current_outer_loop_xy(boundary_loop_result)
        envelope_deviation, current_area = -1.0, 0.0
        if len(envelope) >= 3:
            kernel = [(p[0], p[1]) for p in kernel_result.boundary_xyz]
            envelope_deviation = max(_directed_hausdorff(kernel, envelope, closed=True), _directed_hausdorff(envelope, kernel, closed=True))
            current_area = abs(_signed_area(envelope))
            compared.append(envelope_deviation)
            rows.append(f"envelope_deviation_m|{envelope_deviation:.4f}")
            rows.append(f"envelope_area_m2|kernel={kernel_result.boundary_area_m2:.3f}|current={current_area:.3f}")
        else:
            rows.append("envelope|not_compared|no outer intersection boundary loop")
        if not compared:
            status = "skipped"
        else:
            status = "agree" if max(compared) <= SHADOW_AGREE_TOLERANCE_M else "differ"
        return IntersectionKernelShadowComparison(
            status, fillet_deviation, envelope_deviation, kernel_result.boundary_area_m2, current_area, tuple(rows)
        )


def current_outer_loop_xy(boundary_loop_result) -> list[tuple[float, float]]:
    loop = next(
        (
            row
            for row in list(getattr(boundary_loop_result, "loop_rows", []) or [])
            if str(getattr(row, "loop_role", "") or "") == "outer_intersection_boundary"
        ),
        None,
    )
    points = [(float(p[0]), float(p[1])) for p in list(getattr(loop, "loop_points_xyz", ()) or ())]
    if len(points) > 1 and math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) <= 1.0e-9:
        points.pop()
    return points


def _fillet_deviation(kernel_result, boundary_segment_result, rows: list[str]) -> float:
    current = [
        [(float(p[0]), float(p[1])) for p in (list(row.chord_points_xyz or ()) or [row.start_xyz, row.end_xyz])]
        for row in list(getattr(boundary_segment_result, "segment_rows", []) or [])
        if str(getattr(row, "segment_kind", "") or "") == "arc" and str(getattr(row, "segment_role", "") or "") == "curb_return"
    ]
    kernel = [[(p[0], p[1]) for p in corner.arc_xyz] for corner in kernel_result.corners if corner.arc_xyz]
    if not current or not kernel:
        rows.append("fillets|not_compared|no curb return arcs in the boundary segment result")
        return -1.0
    worst = 0.0
    for arc in kernel:
        # the build's arc at this corner is the one whose end points are nearest
        partner = min(current, key=lambda other: _end_distance(arc, other))
        worst = max(worst, _directed_hausdorff(arc, partner, closed=False), _directed_hausdorff(partner, arc, closed=False))
    rows.append(f"fillet_deviation_m|{worst:.4f}|kernel={len(kernel)}|current={len(current)}")
    if len(kernel) != len(current):
        rows.append(f"fillets|count_differs|kernel={len(kernel)}|current={len(current)}")
        return math.inf
    return worst


def _end_distance(a, b) -> float:
    same = math.dist(a[0], b[0]) + math.dist(a[-1], b[-1])
    swapped = math.dist(a[0], b[-1]) + math.dist(a[-1], b[0])
    return min(same, swapped)


def _text(value) -> str:
    return "-" if value is None else f"{float(value):.3f}"


def _densify(points, closed: bool):
    output = []
    count = len(points) if closed else len(points) - 1
    for index in range(count):
        a, b = points[index], points[(index + 1) % len(points)]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        steps = max(1, int(math.ceil(length / _DENSIFY_STEP_M)))
        output.extend((a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps) for k in range(steps))
    if not closed:
        output.append(points[-1])
    return output


def _directed_hausdorff(source, target, *, closed: bool) -> float:
    return max(_distance_to_polyline(point, target, closed) for point in _densify(source, closed))


def _distance_to_polyline(point, polyline, closed: bool) -> float:
    if len(polyline) == 1:
        return math.dist(point, polyline[0])
    best = math.inf
    count = len(polyline) if closed else len(polyline) - 1
    for index in range(count):
        a, b = polyline[index], polyline[(index + 1) % len(polyline)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length_sq = dx * dx + dy * dy
        t = 0.0 if length_sq <= 1.0e-18 else max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length_sq))
        best = min(best, math.hypot(point[0] - (a[0] + dx * t), point[1] - (a[1] + dy * t)))
    return best


def _signed_area(points) -> float:
    area = 0.0
    for index, point in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        area += point[0] * nxt[1] - nxt[0] * point[1]
    return area * 0.5
