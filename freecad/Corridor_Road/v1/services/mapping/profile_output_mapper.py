"""Profile output mapper for CorridorRoad v1."""

from __future__ import annotations

from ...models.output.profile_output import (
    ProfileEarthworkRow,
    ProfileLineRow,
    ProfileOutput,
    ProfilePviRow,
    ProfileSummaryRow,
)
from ...models.result.earthwork_balance_model import EarthworkBalanceModel
from ...models.source.profile_model import ProfileModel
from ..evaluation.profile_evaluation_service import ProfileEvaluationService


class ProfileOutputMapper:
    """Map profile sources and attached results into profile output payloads."""

    def map_profile_model(
        self,
        profile_model: ProfileModel,
        earthwork_model: EarthworkBalanceModel | None = None,
        *,
        station_interval: float | None = None,
    ) -> ProfileOutput:
        """Create a normalized profile output from one profile model."""

        ordered_controls = sorted(profile_model.control_rows, key=lambda row: row.station)

        line_rows = [
            ProfileLineRow(
                line_row_id=f"{profile_model.profile_id}:fg",
                kind="finished_grade_line" if station_interval is not None else profile_model.profile_kind,
                station_values=self._finished_grade_station_values(
                    profile_model,
                    ordered_controls,
                    station_interval=station_interval,
                ),
                elevation_values=self._finished_grade_elevation_values(
                    profile_model,
                    ordered_controls,
                    station_interval=station_interval,
                ),
                style_role="finished_grade",
                source_ref=profile_model.profile_id,
            )
        ]

        pvi_rows = [
            ProfilePviRow(
                pvi_row_id=row.control_point_id,
                station=row.station,
                elevation=row.elevation,
                label=row.kind,
            )
            for row in ordered_controls
        ]

        earthwork_rows = []
        if earthwork_model is not None:
            earthwork_rows = [
                ProfileEarthworkRow(
                    earthwork_row_id=row.balance_row_id,
                    kind="usable_cut_minus_fill",
                    station_start=0.0 if row.station_start is None else row.station_start,
                    station_end=0.0 if row.station_end is None else row.station_end,
                    value=row.usable_cut_value - row.fill_value,
                    unit=row.unit,
                )
                for row in earthwork_model.balance_rows
            ]

        summary_rows = [
            ProfileSummaryRow(
                summary_id=f"{profile_model.profile_id}:control-count",
                kind="control_count",
                label="Control Count",
                value=len(ordered_controls),
            ),
            ProfileSummaryRow(
                summary_id=f"{profile_model.profile_id}:earthwork-count",
                kind="earthwork_attachment_count",
                label="Earthwork Attachment Count",
                value=len(earthwork_rows),
            ),
        ]

        source_refs = [profile_model.profile_id]
        result_refs: list[str] = []
        if earthwork_model is not None:
            source_refs.extend(ref for ref in earthwork_model.source_refs if ref not in source_refs)
            result_refs.append(earthwork_model.earthwork_balance_id)

        return ProfileOutput(
            schema_version=1,
            project_id=profile_model.project_id,
            profile_output_id=profile_model.profile_id,
            alignment_id=profile_model.alignment_id,
            profile_id=profile_model.profile_id,
            label=profile_model.label,
            unit_context=profile_model.unit_context,
            coordinate_context=profile_model.coordinate_context,
            selection_scope={
                "scope_kind": "profile_review",
                "alignment_id": profile_model.alignment_id,
                "profile_id": profile_model.profile_id,
            },
            source_refs=source_refs,
            result_refs=result_refs,
            line_rows=line_rows,
            pvi_rows=pvi_rows,
            earthwork_rows=earthwork_rows,
            summary_rows=summary_rows,
            diagnostic_rows=list(profile_model.diagnostic_rows),
        )

    def _finished_grade_station_values(
        self,
        profile_model: ProfileModel,
        ordered_controls,
        *,
        station_interval: float | None,
    ) -> list[float]:
        if station_interval is None:
            return [row.station for row in ordered_controls]
        return self._sample_profile_stations(profile_model, ordered_controls, station_interval=station_interval)

    def _finished_grade_elevation_values(
        self,
        profile_model: ProfileModel,
        ordered_controls,
        *,
        station_interval: float | None,
    ) -> list[float]:
        if station_interval is None:
            return [row.elevation for row in ordered_controls]
        service = ProfileEvaluationService()
        elevations: list[float] = []
        for station in self._sample_profile_stations(
            profile_model,
            ordered_controls,
            station_interval=station_interval,
        ):
            result = service.evaluate_station(profile_model, station)
            elevations.append(float(result.elevation))
        return elevations

    @staticmethod
    def _sample_profile_stations(
        profile_model: ProfileModel,
        ordered_controls,
        *,
        station_interval: float,
    ) -> list[float]:
        if not ordered_controls:
            return []
        try:
            interval = float(station_interval)
        except Exception:
            interval = 20.0
        if interval <= 0.0:
            interval = 20.0
        start_station = float(ordered_controls[0].station)
        end_station = float(ordered_controls[-1].station)
        stations = {round(float(row.station), 9) for row in ordered_controls}
        for curve in list(getattr(profile_model, "vertical_curve_rows", []) or []):
            stations.add(round(float(curve.station_start), 9))
            stations.add(round(float(curve.station_end), 9))
        current = start_station
        while current <= end_station + 1e-9:
            stations.add(round(current, 9))
            current += interval
        stations.add(round(end_station, 9))
        return [float(value) for value in sorted(stations)]
