"""Map the Drainage source and its evaluated result to the normalized Drainage output."""

from __future__ import annotations

from ...models.output.drainage_output import (
    DrainageCheckOutputRow,
    DrainageFlowlineOutputRow,
    DrainageLinkOutputRow,
    DrainageOutput,
    DrainagePointOutputRow,
)
from ...models.result.drainage_result import DrainageResult
from ...models.source.drainage_model import DrainageModel
from ..evaluation.drainage_evaluation_service import point_places


class DrainageOutputMapper:
    def map(self, drainage_model: DrainageModel, result: DrainageResult) -> DrainageOutput:
        places = point_places(drainage_model.point_rows, result.flowline_rows)
        flowlines = []
        for row in result.flowline_rows:
            grades = [segment.grade_percent for segment in row.segment_rows] or [0.0]
            flowlines.append(
                DrainageFlowlineOutputRow(
                    ditch_run_ref=row.ditch_run_ref,
                    side=row.side,
                    subassembly_ref=row.subassembly_ref,
                    station_start=row.station_rows[0].station,
                    station_end=row.station_rows[-1].station,
                    length_m=sum(segment.length_m for segment in row.segment_rows),
                    min_grade_percent=min(grades),
                    max_grade_percent=max(grades),
                    profile=tuple((station.station, station.z) for station in row.station_rows),
                    low_point_stations=tuple(row.low_point_stations),
                    high_point_stations=tuple(row.high_point_stations),
                )
            )
        points = []
        for point in drainage_model.point_rows:
            place = places.get(point.point_id)
            points.append(
                DrainagePointOutputRow(
                    point_ref=point.point_id,
                    kind=point.kind,
                    station=point.station,
                    ditch_run_ref=point.ditch_run_ref,
                    side=point.side,
                    x=place[0] if place else None,
                    y=place[1] if place else None,
                    z=place[2] if place else None,
                )
            )
        policy = drainage_model.policy
        return DrainageOutput(
            schema_version=1,
            project_id=drainage_model.project_id,
            label="Drainage",
            drainage_output_id=f"drainage-output:{drainage_model.drainage_model_id}",
            status=result.status,
            min_grade_percent=float(policy.min_grade_percent),
            max_inlet_spacing_m=float(policy.max_inlet_spacing_m),
            low_point_rule=policy.low_point_rule,
            flowline_rows=flowlines,
            point_rows=points,
            link_rows=[
                DrainageLinkOutputRow(row.link_ref, row.from_ref, row.to_ref, row.length_m, row.grade_percent)
                for row in result.link_rows
            ],
            check_rows=[
                DrainageCheckOutputRow(row.check_id, row.kind, row.severity, row.ditch_run_ref, row.station_start, row.station_end, row.message)
                for row in result.check_rows
            ],
            source_refs=[drainage_model.drainage_model_id],
            result_refs=[result.drainage_result_id, *([result.applied_section_set_ref] if result.applied_section_set_ref else [])],
        )


__all__ = ["DrainageOutputMapper"]
