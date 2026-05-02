"""Legacy FreeCAD document adapter for CorridorRoad v1 previews."""

from __future__ import annotations

from dataclasses import dataclass

from ...common.diagnostics import DiagnosticMessage
from ...common.identity import new_entity_id
from ...models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionQuantityFragment,
)
from ...models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from ...models.result.corridor_model import CorridorModel, CorridorSamplingPolicy
from ...models.result.earthwork_balance_model import (
    EarthworkBalanceModel,
    EarthworkBalanceRow,
    EarthworkMaterialRow,
    EarthworkZoneRow,
)
from ...models.source.alignment_model import (
    AlignmentConstraint,
    AlignmentElement,
    AlignmentModel,
)
from ...models.source.profile_model import (
    ProfileConstraint,
    ProfileControlPoint,
    ProfileModel,
    VerticalCurveRow,
)


@dataclass(frozen=True)
class LegacyPreviewBundle:
    """Minimal v1 preview bundle adapted from one legacy document."""

    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    earthwork_model: EarthworkBalanceModel | None = None


def _row_get(row: dict[str, object], *keys: str, default=None):
    """Return a case-tolerant value from a legacy row dictionary."""

    data = dict(row or {})
    for key in keys:
        if key in data:
            return data.get(key)
    lower_map = {str(key).strip().lower(): value for key, value in data.items()}
    for key in keys:
        normalized = str(key).strip().lower()
        if normalized in lower_map:
            return lower_map[normalized]
    return default


def _component_slope(row: dict[str, object], safe_float) -> float:
    """Resolve legacy component slope as elevation change per metre."""

    if _row_get(row, "Slope", "slope", default=None) is not None:
        return safe_float(_row_get(row, "Slope", "slope", default=0.0), 0.0)
    percent = safe_float(_row_get(row, "CrossSlopePct", "crossSlopePct", "cross_slope_pct", default=0.0), 0.0)
    return -float(percent) / 100.0


class LegacyDocumentAdapter:
    """Adapt a legacy FreeCAD document into minimal v1 preview models."""

    def build_alignment_model(
        self,
        document,
        *,
        preferred_alignment=None,
    ) -> AlignmentModel | None:
        """Build a minimal v1 alignment source model from one legacy document."""

        if document is None:
            return None

        project = self._find_project(document)
        alignment = self._resolve_alignment_object(
            project,
            document,
            preferred_alignment=preferred_alignment,
        )
        if alignment is None:
            return None

        alignment_id = self._object_id(alignment, fallback="alignment:legacy")
        geometry_sequence = self._alignment_geometry_sequence(alignment, alignment_id=alignment_id)
        constraint_rows = self._alignment_constraint_rows(alignment)
        diagnostic_rows = self._alignment_diagnostic_rows(alignment)

        return AlignmentModel(
            schema_version=1,
            project_id=self._project_id(project, document),
            alignment_id=alignment_id,
            label=self._object_label(alignment, fallback=self._document_label(document)),
            source_refs=[alignment_id],
            geometry_sequence=geometry_sequence,
            constraint_rows=constraint_rows,
            diagnostic_rows=diagnostic_rows,
        )

    def build_profile_model(
        self,
        document,
        *,
        preferred_profile=None,
        preferred_alignment=None,
    ) -> ProfileModel | None:
        """Build a minimal v1 profile source model from one legacy document."""

        if document is None:
            return None

        project = self._find_project(document)
        alignment = self._resolve_alignment_object(
            project,
            document,
            preferred_alignment=preferred_alignment,
        )
        profile = self._resolve_vertical_alignment_object(
            project,
            document,
            preferred_profile=preferred_profile,
        )
        if profile is None:
            return None

        profile_id = self._object_id(profile, fallback="profile:legacy")
        alignment_id = self._object_id(alignment, fallback="alignment:legacy")
        control_rows = self._profile_control_rows(profile, profile_id=profile_id)
        curve_rows = self._profile_vertical_curve_rows(profile, profile_id=profile_id)
        constraint_rows = self._profile_constraint_rows(profile)
        diagnostic_rows = self._profile_diagnostic_rows(profile)

        return ProfileModel(
            schema_version=1,
            project_id=self._project_id(project, document),
            profile_id=profile_id,
            alignment_id=alignment_id,
            label=self._object_label(profile, fallback=self._document_label(document)),
            source_refs=[ref for ref in (profile_id, alignment_id) if ref],
            control_rows=control_rows,
            vertical_curve_rows=curve_rows,
            constraint_rows=constraint_rows,
            diagnostic_rows=diagnostic_rows,
        )

    def build_preview_bundle(
        self,
        document,
        *,
        preferred_section_set=None,
    ) -> LegacyPreviewBundle | None:
        """Return a minimal preview bundle when the document has usable legacy objects."""

        if document is None:
            return None

        project = self._find_project(document)
        section_set = self._resolve_section_set(project, document, preferred_section_set)
        typical_section = self._resolve_typical_section(project, section_set, document)
        if section_set is None or typical_section is None:
            return None

        document_label = self._document_label(document)
        corridor = CorridorModel(
            schema_version=1,
            project_id=self._project_id(project, document),
            corridor_id=self._corridor_id(project, document),
            alignment_id=self._alignment_id(project, section_set),
            profile_id=self._profile_id(project, section_set),
            label=document_label,
            sampling_policy=CorridorSamplingPolicy(
                sampling_policy_id=f"{self._corridor_id(project, document)}:sampling",
                station_interval=self._section_interval(section_set),
            ),
            source_refs=self._source_refs(project, section_set, typical_section),
        )

        applied_section_set = self._build_applied_section_set(
            corridor=corridor,
            section_set=section_set,
            typical_section=typical_section,
            region_plan=self._resolve_region_plan(project, section_set, document),
            document_label=document_label,
        )
        if not applied_section_set.sections:
            return None

        earthwork_model = self._build_earthwork_model(
            corridor=corridor,
            applied_section_set=applied_section_set,
            cut_fill_calc=self._resolve_cut_fill_calc(project, document),
        )

        return LegacyPreviewBundle(
            corridor=corridor,
            applied_section_set=applied_section_set,
            earthwork_model=earthwork_model,
        )

    def _find_project(self, document):
        """Resolve the legacy CorridorRoadProject object from one document."""

        try:
            from freecad.Corridor_Road.objects.obj_project import find_project

            return find_project(document)
        except Exception:
            return self._find_first_by_name(document, "CorridorRoadProject")

    def _resolve_section_set(self, project, document, preferred_section_set=None):
        """Resolve the preferred legacy SectionSet object."""

        if preferred_section_set is not None:
            return preferred_section_set
        candidate = getattr(project, "SectionSet", None) if project is not None else None
        if candidate is not None:
            return candidate
        return self._find_first_by_proxy_or_name(document, "SectionSet", "SectionSet")

    def _resolve_typical_section(self, project, section_set, document):
        """Resolve the preferred legacy TypicalSectionTemplate object."""

        for candidate in (
            getattr(project, "TypicalSectionTemplate", None) if project is not None else None,
            getattr(section_set, "TypicalSectionTemplate", None) if section_set is not None else None,
        ):
            if candidate is not None:
                return candidate
        return self._find_first_by_proxy_or_name(
            document,
            "TypicalSectionTemplate",
            "TypicalSectionTemplate",
        )

    def _resolve_region_plan(self, project, section_set, document):
        """Resolve the preferred legacy RegionPlan object."""

        for candidate in (
            getattr(section_set, "RegionPlan", None) if section_set is not None else None,
            getattr(project, "RegionPlan", None) if project is not None else None,
        ):
            if candidate is not None:
                return candidate
        return self._find_first_by_proxy_or_name(document, "RegionPlan", "RegionPlan")

    def _resolve_cut_fill_calc(self, project, document):
        """Resolve the preferred legacy CutFillCalc object."""

        candidate = getattr(project, "CutFillCalc", None) if project is not None else None
        if candidate is not None:
            return candidate
        return self._find_first_by_proxy_or_name(document, "CutFillCalc", "CutFillCalc")

    def _resolve_alignment_object(self, project, document, preferred_alignment=None):
        """Resolve the preferred legacy HorizontalAlignment object."""

        if preferred_alignment is not None:
            return preferred_alignment
        candidate = getattr(project, "Alignment", None) if project is not None else None
        if candidate is not None:
            return candidate
        return self._find_first_by_proxy_or_name(document, "HorizontalAlignment", "HorizontalAlignment")

    def _resolve_vertical_alignment_object(self, project, document, preferred_profile=None):
        """Resolve the preferred legacy VerticalAlignment object."""

        if preferred_profile is not None:
            return preferred_profile
        candidate = getattr(project, "VerticalAlignment", None) if project is not None else None
        if candidate is not None:
            return candidate
        return self._find_first_by_proxy_or_name(document, "VerticalAlignment", "VerticalAlignment")

    def _build_applied_section_set(
        self,
        *,
        corridor: CorridorModel,
        section_set,
        typical_section,
        region_plan,
        document_label: str,
    ) -> AppliedSectionSet:
        """Build a minimal applied-section set from legacy section and template objects."""

        station_values = self._station_values(section_set)
        stationing_values = self._v1_station_values(getattr(section_set, "Document", None))
        if len(stationing_values) > len(station_values):
            station_values = stationing_values
        if not station_values:
            station_values = [0.0]

        component_rows = self._legacy_typical_component_rows(typical_section)
        pavement_rows = self._legacy_pavement_rows(typical_section)

        sections: list[AppliedSection] = []
        station_rows: list[AppliedSectionStationRow] = []
        template_id = self._object_id(typical_section, fallback="template:legacy")

        for index, station in enumerate(station_values, start=1):
            applied_section_id = f"{corridor.corridor_id}:section:{index}"
            region_id = self._region_id_at_station(region_plan, station)
            applied_components = [
                AppliedSectionComponentRow(
                    component_id=str(_row_get(row, "Id", "id", "component_id", default=f"component-{row_index}")),
                    kind=str(_row_get(row, "Type", "type", "Kind", "kind", default="component")),
                    source_template_id=template_id,
                    region_id=region_id,
                    side=str(_row_get(row, "Side", "side", default="center") or "center").strip().lower(),
                    width=max(0.0, self._safe_float(_row_get(row, "Width", "width", default=0.0), 0.0)),
                    slope=_component_slope(row, self._safe_float),
                    thickness=max(
                        0.0,
                        self._safe_float(_row_get(row, "Thickness", "thickness", "Height", "height", default=0.0), 0.0),
                    ),
                    material=str(_row_get(row, "Material", "material", default="") or ""),
                )
                for row_index, row in enumerate(component_rows, start=1)
                if bool(_row_get(row, "Enabled", "enabled", default=True))
            ]
            quantity_rows = [
                AppliedSectionQuantityFragment(
                    fragment_id=f"{applied_section_id}:pavement:{row_index}",
                    quantity_kind=f"pavement_{str(row.get('Type', 'layer'))}",
                    value=float(row.get("Thickness", 0.0) or 0.0),
                    unit="m",
                    component_id=str(row.get("Id", "")),
                )
                for row_index, row in enumerate(pavement_rows, start=1)
                if bool(row.get("Enabled", True))
            ]

            sections.append(
                AppliedSection(
                    schema_version=1,
                    project_id=corridor.project_id,
                    applied_section_id=applied_section_id,
                    corridor_id=corridor.corridor_id,
                    alignment_id=corridor.alignment_id,
                    profile_id=corridor.profile_id,
                    label=document_label,
                    station=float(station),
                    template_id=template_id,
                    region_id=region_id,
                    component_rows=applied_components,
                    quantity_rows=quantity_rows,
                    source_refs=list(corridor.source_refs),
                )
            )
            station_rows.append(
                AppliedSectionStationRow(
                    station_row_id=f"{applied_section_id}:station",
                    station=float(station),
                    applied_section_id=applied_section_id,
                )
            )

        return AppliedSectionSet(
            schema_version=1,
            project_id=corridor.project_id,
            applied_section_set_id=f"{corridor.corridor_id}:sections",
            corridor_id=corridor.corridor_id,
            alignment_id=corridor.alignment_id,
            label=document_label,
            source_refs=list(corridor.source_refs),
            station_rows=station_rows,
            sections=sections,
        )

    def _build_earthwork_model(
        self,
        *,
        corridor: CorridorModel,
        applied_section_set: AppliedSectionSet,
        cut_fill_calc,
    ) -> EarthworkBalanceModel | None:
        """Build a minimal earthwork model from legacy CutFillCalc totals and bins."""

        if cut_fill_calc is None:
            return None

        station_bin_rows = self._station_bin_rows(cut_fill_calc)
        balance_rows: list[EarthworkBalanceRow] = []
        zone_rows: list[EarthworkZoneRow] = []

        for row in station_bin_rows:
            cut_value = self._safe_float(row.get("cut", 0.0), 0.0)
            fill_value = self._safe_float(row.get("fill", 0.0), 0.0)
            usable_cut_value = cut_value
            balance_rows.append(
                EarthworkBalanceRow(
                    balance_row_id=new_entity_id("earthwork_balance_row"),
                    station_start=self._safe_float(row.get("fromStation", 0.0), 0.0),
                    station_end=self._safe_float(row.get("toStation", 0.0), 0.0),
                    cut_value=cut_value,
                    fill_value=fill_value,
                    usable_cut_value=usable_cut_value,
                    unusable_cut_value=0.0,
                    balance_ratio=(usable_cut_value / fill_value) if fill_value > 0.0 else 0.0,
                )
            )
            zone_rows.append(
                EarthworkZoneRow(
                    zone_row_id=new_entity_id("earthwork_zone_row"),
                    kind=self._zone_kind(usable_cut_value - fill_value),
                    station_start=self._safe_float(row.get("fromStation", 0.0), 0.0),
                    station_end=self._safe_float(row.get("toStation", 0.0), 0.0),
                    value=abs(usable_cut_value - fill_value),
                )
            )

        if not balance_rows:
            min_station, max_station = self._station_extent(applied_section_set)
            total_cut = self._safe_float(getattr(cut_fill_calc, "CutVolume", 0.0), 0.0)
            total_fill = self._safe_float(getattr(cut_fill_calc, "FillVolume", 0.0), 0.0)
            balance_rows = [
                EarthworkBalanceRow(
                    balance_row_id=new_entity_id("earthwork_balance_row"),
                    station_start=min_station,
                    station_end=max_station,
                    cut_value=total_cut,
                    fill_value=total_fill,
                    usable_cut_value=total_cut,
                    unusable_cut_value=0.0,
                    balance_ratio=(total_cut / total_fill) if total_fill > 0.0 else 0.0,
                )
            ]
            zone_rows = [
                EarthworkZoneRow(
                    zone_row_id=new_entity_id("earthwork_zone_row"),
                    kind=self._zone_kind(total_cut - total_fill),
                    station_start=min_station,
                    station_end=max_station,
                    value=abs(total_cut - total_fill),
                )
            ]

        total_cut = self._safe_float(getattr(cut_fill_calc, "CutVolume", 0.0), 0.0)
        total_fill = self._safe_float(getattr(cut_fill_calc, "FillVolume", 0.0), 0.0)
        material_rows = [
            EarthworkMaterialRow(
                material_row_id=new_entity_id("earthwork_material_row"),
                kind="usable_cut_total",
                value=total_cut,
                unit="m3",
            ),
            EarthworkMaterialRow(
                material_row_id=new_entity_id("earthwork_material_row"),
                kind="fill_total",
                value=total_fill,
                unit="m3",
            ),
        ]

        return EarthworkBalanceModel(
            schema_version=1,
            project_id=corridor.project_id,
            earthwork_balance_id=f"{corridor.corridor_id}:earthwork",
            corridor_id=corridor.corridor_id,
            label=corridor.label,
            source_refs=list(corridor.source_refs) + [self._object_id(cut_fill_calc, fallback="CutFillCalc")],
            balance_rows=balance_rows,
            material_rows=material_rows,
            zone_rows=zone_rows,
        )

    def _alignment_geometry_sequence(
        self,
        alignment,
        *,
        alignment_id: str,
    ) -> list[AlignmentElement]:
        """Extract a minimal alignment geometry sequence from a legacy object."""

        edge_sequence = self._alignment_edge_sequence(alignment, alignment_id=alignment_id)
        if edge_sequence:
            return edge_sequence

        point_rows = self._alignment_point_rows(alignment)
        if len(point_rows) < 2:
            return []

        geometry_rows: list[AlignmentElement] = []
        station_cursor = 0.0
        for index in range(len(point_rows) - 1):
            x0, y0 = point_rows[index]
            x1, y1 = point_rows[index + 1]
            length = self._xy_distance((x0, y0), (x1, y1))
            geometry_rows.append(
                AlignmentElement(
                    element_id=f"{alignment_id}:segment:{index + 1}",
                    kind="tangent",
                    station_start=station_cursor,
                    station_end=station_cursor + length,
                    length=length,
                    geometry_payload={
                        "x_values": [x0, x1],
                        "y_values": [y0, y1],
                        "style_role": "tangent",
                    },
                )
            )
            station_cursor += length
        return geometry_rows

    def _alignment_edge_sequence(
        self,
        alignment,
        *,
        alignment_id: str,
    ) -> list[AlignmentElement]:
        """Extract geometry rows from shape edges when they are available."""

        try:
            shape = getattr(alignment, "Shape", None)
            edges = list(getattr(shape, "Edges", []) or [])
        except Exception:
            edges = []
        if not edges:
            return []

        station_cursor = 0.0
        geometry_rows: list[AlignmentElement] = []
        for index, edge in enumerate(edges, start=1):
            points = self._edge_xy_points(edge)
            if len(points) < 2:
                continue
            length = self._safe_float(getattr(edge, "Length", 0.0), 0.0)
            geometry_rows.append(
                AlignmentElement(
                    element_id=f"{alignment_id}:edge:{index}",
                    kind=self._edge_kind(edge),
                    station_start=station_cursor,
                    station_end=station_cursor + length,
                    length=length,
                    geometry_payload={
                        "x_values": [point[0] for point in points],
                        "y_values": [point[1] for point in points],
                        "style_role": self._edge_kind(edge),
                    },
                )
            )
            station_cursor += length
        return geometry_rows

    def _alignment_point_rows(self, alignment) -> list[tuple[float, float]]:
        """Extract raw IP point rows from one legacy alignment object."""

        rows = []
        for point in list(getattr(alignment, "IPPoints", []) or []):
            xy = self._point_xy(point)
            if xy is None:
                continue
            rows.append(xy)
        return rows

    def _alignment_constraint_rows(self, alignment) -> list[AlignmentConstraint]:
        """Extract a minimal constraint set from one legacy alignment object."""

        rows: list[AlignmentConstraint] = []
        for attr, kind, unit in (
            ("DesignSpeedKph", "design_speed", "km/h"),
            ("MinRadius", "min_radius", "m"),
            ("MinTangentLength", "min_tangent_length", "m"),
            ("MinTransitionLength", "min_transition_length", "m"),
        ):
            if not hasattr(alignment, attr):
                continue
            rows.append(
                AlignmentConstraint(
                    constraint_id=f"{self._object_id(alignment, fallback='alignment:legacy')}:{kind}",
                    kind=kind,
                    value=self._safe_float(getattr(alignment, attr, 0.0), 0.0),
                    unit=unit,
                    hard_or_soft="soft",
                )
            )
        return rows

    def _alignment_diagnostic_rows(self, alignment) -> list[DiagnosticMessage]:
        """Extract legacy criteria messages as v1 diagnostics."""

        diagnostics: list[DiagnosticMessage] = []
        for message in list(getattr(alignment, "CriteriaMessages", []) or []):
            text = str(message or "").strip()
            if not text:
                continue
            diagnostics.append(
                DiagnosticMessage(
                    severity="warning",
                    kind="legacy_alignment_criteria",
                    message=text,
                )
            )
        return diagnostics

    def _profile_control_rows(
        self,
        profile,
        *,
        profile_id: str,
    ) -> list[ProfileControlPoint]:
        """Extract control rows from one legacy vertical alignment object."""

        stations = list(getattr(profile, "PVIStations", []) or [])
        elevations = list(getattr(profile, "PVIElevations", []) or [])
        curve_lengths = list(getattr(profile, "CurveLengths", []) or [])
        count = min(len(stations), len(elevations))
        rows: list[ProfileControlPoint] = []
        for index in range(count):
            station = self._safe_float(stations[index], 0.0)
            elevation = self._safe_float(elevations[index], 0.0)
            curve_length = self._safe_float(curve_lengths[index], 0.0) if index < len(curve_lengths) else 0.0
            rows.append(
                ProfileControlPoint(
                    control_point_id=f"{profile_id}:pvi:{index + 1}",
                    station=station,
                    elevation=elevation,
                    kind="pvi" if curve_length > 0.0 else "grade_break",
                )
            )
        rows.sort(key=lambda row: row.station)
        return rows

    def _profile_vertical_curve_rows(
        self,
        profile,
        *,
        profile_id: str,
    ) -> list[VerticalCurveRow]:
        """Extract vertical-curve rows from one legacy vertical alignment object."""

        rows: list[VerticalCurveRow] = []
        try:
            from freecad.Corridor_Road.objects.obj_vertical_alignment import VerticalAlignment

            _pvis, _grades, curves = VerticalAlignment._solve_curves(profile)
            for index, row in enumerate(curves, start=1):
                rows.append(
                    VerticalCurveRow(
                        vertical_curve_id=f"{profile_id}:curve:{index}",
                        kind="parabolic_vertical_curve",
                        station_start=self._safe_float(row.get("bvc", 0.0), 0.0),
                        station_end=self._safe_float(row.get("evc", 0.0), 0.0),
                        curve_length=self._safe_float(row.get("L", 0.0), 0.0),
                        curve_parameter=self._safe_float(row.get("g2", 0.0), 0.0)
                        - self._safe_float(row.get("g1", 0.0), 0.0),
                    )
                )
            return rows
        except Exception:
            pass

        stations = list(getattr(profile, "PVIStations", []) or [])
        curve_lengths = list(getattr(profile, "CurveLengths", []) or [])
        for index, station_value in enumerate(stations):
            curve_length = self._safe_float(curve_lengths[index], 0.0) if index < len(curve_lengths) else 0.0
            if curve_length <= 0.0:
                continue
            center = self._safe_float(station_value, 0.0)
            half = 0.5 * curve_length
            rows.append(
                VerticalCurveRow(
                    vertical_curve_id=f"{profile_id}:curve:{index + 1}",
                    kind="parabolic_vertical_curve",
                    station_start=center - half,
                    station_end=center + half,
                    curve_length=curve_length,
                )
            )
        return rows

    def _profile_constraint_rows(self, profile) -> list[ProfileConstraint]:
        """Extract a minimal constraint set from one legacy vertical alignment object."""

        rows: list[ProfileConstraint] = []
        if hasattr(profile, "ClampOverlaps"):
            rows.append(
                ProfileConstraint(
                    constraint_id=f"{self._object_id(profile, fallback='profile:legacy')}:clamp-overlaps",
                    kind="clamp_overlaps",
                    value=str(bool(getattr(profile, "ClampOverlaps", True))).lower(),
                )
            )
        if hasattr(profile, "MinTangent"):
            rows.append(
                ProfileConstraint(
                    constraint_id=f"{self._object_id(profile, fallback='profile:legacy')}:min-tangent",
                    kind="min_tangent",
                    value=self._safe_float(getattr(profile, "MinTangent", 0.0), 0.0),
                    unit="m",
                )
            )
        return rows

    def _profile_diagnostic_rows(self, profile) -> list[DiagnosticMessage]:
        """Extract basic diagnostics from one legacy vertical alignment object."""

        control_count = min(
            len(list(getattr(profile, "PVIStations", []) or [])),
            len(list(getattr(profile, "PVIElevations", []) or [])),
        )
        if control_count >= 2:
            return []
        return [
            DiagnosticMessage(
                severity="warning",
                kind="legacy_profile_controls",
                message="VerticalAlignment has fewer than 2 valid PVI rows.",
            )
        ]

    def _station_values(self, section_set) -> list[float]:
        """Resolve sorted station values from a legacy SectionSet."""

        try:
            from freecad.Corridor_Road.objects.obj_section_set import SectionSet

            return [float(value) for value in list(SectionSet.resolve_station_values(section_set) or [])]
        except Exception:
            raw_values = []
            for value in (
                getattr(section_set, "StartStation", None),
                getattr(section_set, "EndStation", None),
            ):
                if value is None:
                    continue
                raw_values.append(self._safe_float(value, 0.0))
            return sorted(dict.fromkeys(raw_values))

    def viewer_station_rows(self, section_set) -> list[dict[str, object]]:
        """Resolve viewer-oriented station rows from a legacy SectionSet."""

        v1_rows = self._v1_station_viewer_rows(getattr(section_set, "Document", None))
        if v1_rows:
            return v1_rows
        try:
            from freecad.Corridor_Road.objects.obj_section_set import SectionSet

            return [dict(row) for row in list(SectionSet.resolve_viewer_station_rows(section_set) or [])]
        except Exception:
            return [
                {
                    "index": index,
                    "station": station,
                    "label": f"STA {station:.3f}",
                }
                for index, station in enumerate(self._station_values(section_set))
            ]

    def _v1_station_values(self, document) -> list[float]:
        rows = self._v1_station_viewer_rows(document)
        values = []
        for row in rows:
            try:
                values.append(float(row.get("station", 0.0) or 0.0))
            except Exception:
                pass
        return values

    def _v1_station_viewer_rows(self, document) -> list[dict[str, object]]:
        try:
            from freecad.Corridor_Road.v1.objects.obj_stationing import find_v1_stationing, station_value_rows

            stationing = find_v1_stationing(document)
            rows = []
            for index, (station, label) in enumerate(station_value_rows(stationing)):
                rows.append(
                    {
                        "index": index,
                        "station": float(station),
                        "label": str(label or f"STA {float(station):.3f}"),
                    }
                )
            return rows
        except Exception:
            return []

    def nearest_station_row(
        self,
        section_set,
        preferred_station: float | None = None,
    ) -> dict[str, object] | None:
        """Resolve the nearest viewer station row for an optional preferred station."""

        rows = self.viewer_station_rows(section_set)
        if not rows:
            return None
        if preferred_station is None:
            return dict(rows[0])

        best_row = dict(rows[0])
        best_delta = abs(self._safe_float(best_row.get("station", 0.0), 0.0) - float(preferred_station))
        for row in rows[1:]:
            delta = abs(self._safe_float(row.get("station", 0.0), 0.0) - float(preferred_station))
            if delta < best_delta:
                best_delta = delta
                best_row = dict(row)
        return best_row

    def _legacy_typical_component_rows(self, typical_section) -> list[dict[str, object]]:
        """Read component rows from a legacy TypicalSectionTemplate."""

        try:
            from freecad.Corridor_Road.objects.obj_typical_section_template import component_rows

            return [dict(row) for row in list(component_rows(typical_section) or [])]
        except Exception:
            return []

    def _legacy_pavement_rows(self, typical_section) -> list[dict[str, object]]:
        """Read pavement rows from a legacy TypicalSectionTemplate."""

        try:
            from freecad.Corridor_Road.objects.obj_typical_section_template import pavement_rows

            return [dict(row) for row in list(pavement_rows(typical_section) or [])]
        except Exception:
            return []

    def _region_id_at_station(self, region_plan, station: float) -> str:
        """Resolve one legacy region id at a given station."""

        if region_plan is None:
            return ""
        try:
            from freecad.Corridor_Road.objects.obj_region_plan import RegionPlan

            context = RegionPlan.resolve_station_context(region_plan, float(station))
            return str(context.get("BaseRegionId", "") or "")
        except Exception:
            return ""

    def _station_bin_rows(self, cut_fill_calc) -> list[dict[str, str]]:
        """Parse legacy station-bin rows from CutFillCalc."""

        rows = []
        for text in list(getattr(cut_fill_calc, "StationBinnedSummaryRows", []) or []):
            row = self._parse_report_row(text)
            if row.get("kind") != "stationBin":
                continue
            if str(row.get("side", "") or "") != "all":
                continue
            rows.append(row)
        return rows

    def _parse_report_row(self, text: str) -> dict[str, str]:
        """Parse the legacy `kind|key=value` summary row format."""

        raw = str(text or "").strip()
        if not raw:
            return {}
        parts = [part.strip() for part in raw.split("|")]
        parsed = {"kind": parts[0]}
        for part in parts[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            parsed[key.strip()] = value.strip()
        return parsed

    def _station_extent(self, applied_section_set: AppliedSectionSet) -> tuple[float, float]:
        """Return the station extent of one applied section set."""

        if not applied_section_set.station_rows:
            return 0.0, 0.0
        values = [float(row.station) for row in applied_section_set.station_rows]
        return min(values), max(values)

    def _zone_kind(self, delta_value: float) -> str:
        """Classify one earthwork delta into a minimal zone kind."""

        if delta_value > 0.0:
            return "surplus_zone"
        if delta_value < 0.0:
            return "deficit_zone"
        return "balanced_zone"

    def _project_id(self, project, document) -> str:
        """Build a stable v1 preview project id."""

        return self._object_id(project, fallback=self._document_label(document) or "corridorroad-v1")

    def _corridor_id(self, project, document) -> str:
        """Build a stable v1 preview corridor id."""

        return f"corridor:{self._project_id(project, document)}"

    def _alignment_id(self, project, section_set) -> str:
        """Resolve the alignment id from a legacy project or section set."""

        candidate = getattr(project, "Alignment", None) if project is not None else None
        if candidate is None and section_set is not None:
            source = getattr(section_set, "SourceCenterlineDisplay", None)
            candidate = getattr(source, "Alignment", None) if source is not None else None
        return self._object_id(candidate, fallback="alignment:legacy")

    def _profile_id(self, project, section_set) -> str:
        """Resolve the profile id from a legacy project or section set."""

        candidate = getattr(project, "VerticalAlignment", None) if project is not None else None
        if candidate is None and section_set is not None:
            source = getattr(section_set, "SourceCenterlineDisplay", None)
            candidate = getattr(source, "VerticalAlignment", None) if source is not None else None
        return self._object_id(candidate, fallback="profile:legacy")

    def _document_label(self, document) -> str:
        """Resolve a human-friendly label for one FreeCAD document."""

        for attr in ("Label", "Name"):
            value = getattr(document, attr, "")
            if isinstance(value, str) and value:
                return value
        return "CorridorRoad v1 Preview"

    def _section_interval(self, section_set) -> float:
        """Resolve a reasonable station interval from one legacy SectionSet."""

        return max(1.0, self._safe_float(getattr(section_set, "Interval", 20.0), 20.0))

    def _source_refs(self, project, section_set, typical_section) -> list[str]:
        """Build basic source refs for one legacy preview bundle."""

        refs = [
            self._object_id(project, fallback=""),
            self._object_id(section_set, fallback=""),
            self._object_id(typical_section, fallback=""),
        ]
        return [ref for ref in refs if ref]

    def _object_id(self, obj, fallback: str) -> str:
        """Resolve a stable id-like string from one legacy object."""

        if obj is None:
            return fallback
        for attr in ("Name", "Label"):
            value = getattr(obj, attr, "")
            if isinstance(value, str) and value:
                return value
        return fallback

    def _object_label(self, obj, fallback: str) -> str:
        """Resolve a human-friendly label from one legacy object."""

        if obj is None:
            return fallback
        for attr in ("Label", "Name"):
            value = getattr(obj, attr, "")
            if isinstance(value, str) and value:
                return value
        return fallback

    def _edge_kind(self, edge) -> str:
        """Classify one edge into a minimal plan geometry kind."""

        curve = getattr(edge, "Curve", None)
        name = str(type(curve).__name__ if curve is not None else "")
        if "Line" in name:
            return "tangent"
        if "Circle" in name or "Arc" in name:
            return "circular_curve"
        if "BSpline" in name or "Bezier" in name or "Spline" in name:
            return "transition_curve"
        return "geometry"

    def _edge_xy_points(self, edge) -> list[tuple[float, float]]:
        """Extract XY sample points from one edge-like object."""

        try:
            points = list(edge.discretize(Number=12) or [])
        except Exception:
            points = []
        if not points:
            try:
                vertexes = list(getattr(edge, "Vertexes", []) or [])
                points = [getattr(vertex, "Point", vertex) for vertex in vertexes]
            except Exception:
                points = []
        rows: list[tuple[float, float]] = []
        for point in points:
            xy = self._point_xy(point)
            if xy is None:
                continue
            rows.append(xy)
        return rows

    def _point_xy(self, point) -> tuple[float, float] | None:
        """Extract XY coordinates from a point-like object or tuple."""

        if point is None:
            return None
        for x_attr, y_attr in (("x", "y"), ("X", "Y")):
            try:
                return float(getattr(point, x_attr)), float(getattr(point, y_attr))
            except Exception:
                pass
        try:
            return float(point[0]), float(point[1])
        except Exception:
            return None

    def _xy_distance(self, left: tuple[float, float], right: tuple[float, float]) -> float:
        """Measure Euclidean distance in XY."""

        dx = float(right[0]) - float(left[0])
        dy = float(right[1]) - float(left[1])
        return (dx * dx + dy * dy) ** 0.5

    def _find_first_by_name(self, document, name_prefix: str):
        """Find the first object whose name starts with the given prefix."""

        if document is None:
            return None
        for obj in list(getattr(document, "Objects", []) or []):
            name = getattr(obj, "Name", "")
            if isinstance(name, str) and name.startswith(name_prefix):
                return obj
        return None

    def _find_first_by_proxy_or_name(self, document, proxy_type: str, name_prefix: str):
        """Find the first object that matches a proxy type or name prefix."""

        if document is None:
            return None
        for obj in list(getattr(document, "Objects", []) or []):
            try:
                found_type = str(getattr(getattr(obj, "Proxy", None), "Type", "") or "")
            except Exception:
                found_type = ""
            name = str(getattr(obj, "Name", "") or "")
            if found_type == proxy_type or name.startswith(name_prefix):
                return obj
        return None

    def _safe_float(self, value, default: float) -> float:
        """Safely parse one numeric value."""

        try:
            return float(value)
        except Exception:
            return float(default)
