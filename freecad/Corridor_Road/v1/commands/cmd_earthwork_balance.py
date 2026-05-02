"""Earthwork balance command bridge for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from ..models.result.applied_section import (
    AppliedSection,
    AppliedSectionComponentRow,
    AppliedSectionFrame,
    AppliedSectionQuantityFragment,
)
from ..models.result.applied_section_set import AppliedSectionSet, AppliedSectionStationRow
from ..models.result.corridor_model import CorridorModel, CorridorSamplingPolicy
from ..services.evaluation import LegacyDocumentAdapter
from ..services.builders import (
    EarthworkBalanceBuildRequest,
    EarthworkBalanceService,
    EarthworkReportBuildRequest,
    EarthworkReportService,
    MassHaulBuildRequest,
    MassHaulService,
    QuantityBuildRequest,
    QuantityBuildService,
)
from ..services.mapping import EarthworkOutputMapper, QuantityOutputMapper
from ..ui.common import clear_ui_context, get_ui_context
from ..ui.viewers import EarthworkViewerTaskPanel
from .selection_context import selected_section_target


def _build_navigation_station_rows(
    station_values: list[tuple[float, str]] | None,
    *,
    current_station: float | None,
) -> list[dict[str, object]]:
    """Build the full station-navigation payload for the earthwork viewer."""

    raw_rows = []
    for station, label in list(station_values or []):
        try:
            station_value = float(station)
        except Exception:
            continue
        raw_rows.append((station_value, str(label or f"STA {station_value:.3f}").strip()))
    if not raw_rows:
        return []

    unique_rows: list[tuple[float, str]] = []
    seen_stations: set[float] = set()
    for station_value, label in sorted(raw_rows, key=lambda row: row[0]):
        rounded = round(station_value, 9)
        if rounded in seen_stations:
            continue
        seen_stations.add(rounded)
        unique_rows.append((station_value, label))

    if current_station is None:
        current_index = 0
    else:
        current_index = min(
            range(len(unique_rows)),
            key=lambda idx: abs(unique_rows[idx][0] - float(current_station)),
        )

    result = []
    for output_index, row_index in enumerate(range(len(unique_rows))):
        station_value, label = unique_rows[row_index]
        result.append(
            {
                "index": row_index,
                "station": station_value,
                "label": label or f"STA {station_value:.3f}",
                "is_current": bool(row_index == current_index),
                "navigation_order": output_index,
            }
        )
    return result


def build_document_earthwork_report(
    document,
    *,
    preferred_section_set=None,
    preferred_station: float | None = None,
    existing_ground_surface=None,
    corridor_model=None,
) -> dict[str, object] | None:
    """Build a v1-native earthwork report from a FreeCAD document when possible."""

    return build_v1_document_earthwork_report(
        document,
        preferred_section_set=preferred_section_set,
        preferred_station=preferred_station,
        existing_ground_surface=existing_ground_surface,
        corridor_model=corridor_model,
    )


def build_v1_document_earthwork_report(
    document,
    *,
    preferred_section_set=None,
    preferred_station: float | None = None,
    existing_ground_surface=None,
    corridor_model=None,
) -> dict[str, object] | None:
    """Build a v1-native earthwork report from document Applied Sections and EG TIN."""

    applied_section_set = _resolve_v1_applied_section_set_model(
        document,
        preferred_section_set=preferred_section_set,
    )
    if applied_section_set is None:
        return None

    corridor = corridor_model or _build_v1_corridor_model(
        document,
        applied_section_set=applied_section_set,
    )
    eg_surface = existing_ground_surface or _resolve_v1_existing_ground_tin_surface(document)
    report_id = f"{corridor.corridor_id or 'corridor'}:earthwork"
    result = EarthworkReportService().build(
        EarthworkReportBuildRequest(
            project_id=corridor.project_id,
            corridor=corridor,
            applied_section_set=applied_section_set,
            existing_ground_surface=eg_surface,
            report_id=report_id,
        )
    )

    focus_station = _focus_station_from_applied_sections(
        applied_section_set,
        preferred_station=preferred_station,
    )
    station_row = _nearest_applied_section_station_row(
        applied_section_set,
        preferred_station=focus_station,
    )
    focused_balance_row = _nearest_balance_row(result.earthwork_model.balance_rows, focus_station)
    focused_haul_zone = _nearest_haul_zone(result.mass_haul_model.haul_zone_rows, focus_station)
    station_values = [
        (float(row.station), f"STA {float(row.station):.3f}")
        for row in list(getattr(applied_section_set, "station_rows", []) or [])
    ]
    navigation_rows = _build_navigation_station_rows(
        station_values,
        current_station=focus_station,
    )

    navigation_rows = _build_navigation_station_rows(
        station_values,
        current_station=focus_station,
    )

    return {
        "corridor": result.corridor,
        "applied_section_set": result.applied_section_set,
        "earthwork_analysis_result": result.analysis_result,
        "quantity_model": result.quantity_model,
        "earthwork_model": result.earthwork_model,
        "mass_haul_model": result.mass_haul_model,
        "quantity_output": result.quantity_output,
        "earthwork_output": result.earthwork_output,
        "mass_haul_output": result.mass_haul_output,
        "station_row": station_row,
        "focused_balance_row": focused_balance_row,
        "focused_haul_zone": focused_haul_zone,
        "station_rows": navigation_rows,
        "key_station_rows": navigation_rows,
        "diagnostic_rows": result.diagnostic_rows,
        "document_objects": {
            "section_set": preferred_section_set,
            "existing_ground_surface": eg_surface,
        },
        "legacy_objects": {},
    }


def build_legacy_document_earthwork_report(
    document,
    *,
    preferred_section_set=None,
    preferred_station: float | None = None,
) -> dict[str, object] | None:
    """Build the older adapter-backed earthwork report path."""

    adapter = LegacyDocumentAdapter()
    project = adapter._find_project(document)
    bundle = adapter.build_preview_bundle(
        document,
        preferred_section_set=preferred_section_set,
    )
    if bundle is None:
        return None

    quantity_model = QuantityBuildService().build(
        QuantityBuildRequest(
            project_id=bundle.corridor.project_id,
            corridor=bundle.corridor,
            applied_section_set=bundle.applied_section_set,
            quantity_model_id=f"{bundle.corridor.corridor_id}:quantity",
        )
    )
    earthwork_model = bundle.earthwork_model
    if earthwork_model is None:
        earthwork_model = EarthworkBalanceService().build(
            EarthworkBalanceBuildRequest(
                project_id=bundle.corridor.project_id,
                corridor=bundle.corridor,
                applied_section_set=bundle.applied_section_set,
                quantity_model=quantity_model,
                earthwork_balance_id=f"{bundle.corridor.corridor_id}:earthwork",
            )
        )
    mass_haul_model = MassHaulService().build(
        MassHaulBuildRequest(
            project_id=bundle.corridor.project_id,
            corridor=bundle.corridor,
            earthwork_balance_model=earthwork_model,
            mass_haul_id=f"{bundle.corridor.corridor_id}:masshaul",
        )
    )

    quantity_output = QuantityOutputMapper().map_quantity_model(quantity_model)
    earthwork_mapper = EarthworkOutputMapper()
    earthwork_output = earthwork_mapper.map_earthwork_balance(earthwork_model)
    mass_haul_output = earthwork_mapper.map_mass_haul(mass_haul_model)
    section_set = preferred_section_set or adapter._resolve_section_set(
        project,
        document,
        preferred_section_set=preferred_section_set,
    )
    alignment = adapter._resolve_alignment_object(project, document)
    profile = adapter._resolve_vertical_alignment_object(project, document)
    cut_fill_calc = adapter._resolve_cut_fill_calc(project, document)
    station_row = adapter.nearest_station_row(section_set, preferred_station=preferred_station)
    focus_station = (
        adapter._safe_float(station_row.get("station", 0.0), 0.0)
        if station_row is not None
        else None
    )
    focused_balance_row = _nearest_balance_row(earthwork_model.balance_rows, focus_station)
    focused_haul_zone = _nearest_haul_zone(mass_haul_model.haul_zone_rows, focus_station)
    station_values = []
    if section_set is not None:
        for row in list(adapter.viewer_station_rows(section_set) or []):
            station_values.append(
                (
                    adapter._safe_float(row.get("station", 0.0), 0.0),
                    str(row.get("label", "") or f"STA {adapter._safe_float(row.get('station', 0.0), 0.0):.3f}"),
                )
            )

    return {
        "corridor": bundle.corridor,
        "applied_section_set": bundle.applied_section_set,
        "quantity_model": quantity_model,
        "earthwork_model": earthwork_model,
        "mass_haul_model": mass_haul_model,
        "quantity_output": quantity_output,
        "earthwork_output": earthwork_output,
        "mass_haul_output": mass_haul_output,
        "station_row": station_row,
        "focused_balance_row": focused_balance_row,
        "focused_haul_zone": focused_haul_zone,
        "station_rows": navigation_rows,
        "key_station_rows": navigation_rows,
        "legacy_objects": {
            "project": project,
            "section_set": section_set,
            "alignment": alignment,
            "profile": profile,
            "cut_fill_calc": cut_fill_calc,
        },
    }


def _resolve_v1_applied_section_set_model(document, *, preferred_section_set=None) -> AppliedSectionSet | None:
    if isinstance(preferred_section_set, AppliedSectionSet):
        return preferred_section_set
    try:
        from ..objects.obj_applied_section import find_v1_applied_section_set, to_applied_section_set

        obj = find_v1_applied_section_set(document, preferred_applied_section_set=preferred_section_set)
        return to_applied_section_set(obj)
    except Exception:
        return None


def _build_v1_corridor_model(document, *, applied_section_set: AppliedSectionSet) -> CorridorModel:
    try:
        from .cmd_build_corridor import build_document_corridor_model

        return build_document_corridor_model(document)
    except Exception:
        return CorridorModel(
            schema_version=1,
            project_id=applied_section_set.project_id,
            corridor_id=applied_section_set.corridor_id or "corridor:main",
            alignment_id=applied_section_set.alignment_id,
            profile_id="",
            label="Earthwork Corridor",
            applied_section_set_ref=applied_section_set.applied_section_set_id,
            sampling_policy=CorridorSamplingPolicy(
                sampling_policy_id=f"{applied_section_set.corridor_id or 'corridor'}:earthwork-sampling",
                station_interval=_station_interval(applied_section_set),
            ),
        )


def _resolve_v1_existing_ground_tin_surface(document):
    try:
        from .cmd_build_corridor import _resolve_corridor_existing_ground_tin_surface

        return _resolve_corridor_existing_ground_tin_surface(document)
    except Exception:
        return None


def _focus_station_from_applied_sections(
    applied_section_set: AppliedSectionSet,
    *,
    preferred_station: float | None,
) -> float | None:
    if preferred_station is not None:
        try:
            return float(preferred_station)
        except Exception:
            pass
    station_rows = list(getattr(applied_section_set, "station_rows", []) or [])
    if not station_rows:
        return None
    return float(getattr(station_rows[0], "station", 0.0) or 0.0)


def _nearest_applied_section_station_row(
    applied_section_set: AppliedSectionSet,
    *,
    preferred_station: float | None,
) -> dict[str, object]:
    station_rows = list(getattr(applied_section_set, "station_rows", []) or [])
    if not station_rows:
        return {}
    if preferred_station is None:
        row = station_rows[0]
    else:
        row = min(station_rows, key=lambda item: abs(float(item.station) - float(preferred_station)))
    station = float(getattr(row, "station", 0.0) or 0.0)
    return {
        "station": station,
        "label": f"STA {station:.3f}",
        "applied_section_id": str(getattr(row, "applied_section_id", "") or ""),
    }


def _station_interval(applied_section_set: AppliedSectionSet) -> float:
    stations = sorted(float(row.station) for row in list(getattr(applied_section_set, "station_rows", []) or []))
    if len(stations) < 2:
        return 0.0
    deltas = [end - start for start, end in zip(stations[:-1], stations[1:]) if end > start]
    return min(deltas) if deltas else 0.0


def build_demo_earthwork_report(
    document_label: str = "",
    *,
    preferred_station: float | None = None,
) -> dict[str, object]:
    """Build a minimal in-memory v1 earthwork report for command bridging."""

    corridor = CorridorModel(
        schema_version=1,
        project_id="corridorroad-v1-demo",
        corridor_id="corridor:v1-demo",
        alignment_id="alignment:v1-demo",
        profile_id="profile:v1-demo",
        label=document_label or "CorridorRoad v1 Demo Corridor",
        sampling_policy=CorridorSamplingPolicy(
            sampling_policy_id="sampling:v1-demo",
            station_interval=20.0,
        ),
    )
    applied_section_set = AppliedSectionSet(
        schema_version=1,
        project_id="corridorroad-v1-demo",
        applied_section_set_id="sections:v1-demo",
        corridor_id=corridor.corridor_id,
        alignment_id=corridor.alignment_id,
        station_rows=[
            AppliedSectionStationRow(
                station_row_id="station:0",
                station=0.0,
                applied_section_id="section:0",
            ),
            AppliedSectionStationRow(
                station_row_id="station:20",
                station=20.0,
                applied_section_id="section:20",
            ),
            AppliedSectionStationRow(
                station_row_id="station:40",
                station=40.0,
                applied_section_id="section:40",
            ),
        ],
        sections=[
            AppliedSection(
                schema_version=1,
                project_id="corridorroad-v1-demo",
                applied_section_id="section:0",
                corridor_id=corridor.corridor_id,
                alignment_id=corridor.alignment_id,
                profile_id=corridor.profile_id,
                label=document_label or corridor.label,
                station=0.0,
                region_id="region:mainline",
                frame=AppliedSectionFrame(
                    station=0.0,
                    x=1000.0,
                    y=2000.0,
                    z=12.0,
                    tangent_direction_deg=0.0,
                    profile_grade=0.02,
                    alignment_status="ok",
                    profile_status="ok",
                ),
                component_rows=_demo_section_components(),
                quantity_rows=[
                    AppliedSectionQuantityFragment(
                        fragment_id="fragment:cut:0",
                        quantity_kind="cut",
                        value=100.0,
                        unit="m3",
                    ),
                    AppliedSectionQuantityFragment(
                        fragment_id="fragment:fill:0",
                        quantity_kind="fill",
                        value=40.0,
                        unit="m3",
                    ),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="corridorroad-v1-demo",
                applied_section_id="section:20",
                corridor_id=corridor.corridor_id,
                alignment_id=corridor.alignment_id,
                profile_id=corridor.profile_id,
                label=document_label or corridor.label,
                station=20.0,
                region_id="region:mainline",
                frame=AppliedSectionFrame(
                    station=20.0,
                    x=1020.0,
                    y=2000.0,
                    z=12.4,
                    tangent_direction_deg=0.0,
                    profile_grade=0.02,
                    alignment_status="ok",
                    profile_status="ok",
                ),
                component_rows=_demo_section_components(),
                quantity_rows=[
                    AppliedSectionQuantityFragment(
                        fragment_id="fragment:cut:20",
                        quantity_kind="cut",
                        value=20.0,
                        unit="m3",
                    ),
                    AppliedSectionQuantityFragment(
                        fragment_id="fragment:fill:20",
                        quantity_kind="fill",
                        value=70.0,
                        unit="m3",
                    ),
                ],
            ),
            AppliedSection(
                schema_version=1,
                project_id="corridorroad-v1-demo",
                applied_section_id="section:40",
                corridor_id=corridor.corridor_id,
                alignment_id=corridor.alignment_id,
                profile_id=corridor.profile_id,
                label=document_label or corridor.label,
                station=40.0,
                region_id="region:mainline",
                frame=AppliedSectionFrame(
                    station=40.0,
                    x=1040.0,
                    y=2000.0,
                    z=12.8,
                    tangent_direction_deg=0.0,
                    profile_grade=0.02,
                    alignment_status="ok",
                    profile_status="ok",
                ),
                component_rows=_demo_section_components(),
            ),
        ],
    )

    quantity_model = QuantityBuildService().build(
        QuantityBuildRequest(
            project_id=corridor.project_id,
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model_id="quantity:v1-demo",
        )
    )
    earthwork_model = EarthworkBalanceService().build(
        EarthworkBalanceBuildRequest(
            project_id=corridor.project_id,
            corridor=corridor,
            applied_section_set=applied_section_set,
            quantity_model=quantity_model,
            earthwork_balance_id="earthwork:v1-demo",
        )
    )
    mass_haul_model = MassHaulService().build(
        MassHaulBuildRequest(
            project_id=corridor.project_id,
            corridor=corridor,
            earthwork_balance_model=earthwork_model,
            mass_haul_id="masshaul:v1-demo",
        )
    )

    quantity_output = QuantityOutputMapper().map_quantity_model(quantity_model)
    earthwork_mapper = EarthworkOutputMapper()
    earthwork_output = earthwork_mapper.map_earthwork_balance(earthwork_model)
    mass_haul_output = earthwork_mapper.map_mass_haul(mass_haul_model)
    focus_station = 0.0 if preferred_station is None else float(preferred_station)
    focused_balance_row = _nearest_balance_row(earthwork_model.balance_rows, focus_station)
    focused_haul_zone = _nearest_haul_zone(mass_haul_model.haul_zone_rows, focus_station)
    navigation_rows = _build_navigation_station_rows(
        [
            (0.0, "STA 0.000"),
            (20.0, "STA 20.000"),
            (40.0, "STA 40.000"),
        ],
        current_station=focus_station,
    )

    return {
        "corridor": corridor,
        "applied_section_set": applied_section_set,
        "quantity_model": quantity_model,
        "earthwork_model": earthwork_model,
        "mass_haul_model": mass_haul_model,
        "quantity_output": quantity_output,
        "earthwork_output": earthwork_output,
        "mass_haul_output": mass_haul_output,
        "station_row": {"station": focus_station, "label": f"STA {focus_station:.3f}"},
        "focused_balance_row": focused_balance_row,
        "focused_haul_zone": focused_haul_zone,
        "station_rows": navigation_rows,
        "key_station_rows": navigation_rows,
        "legacy_objects": {},
    }


def _demo_section_components() -> list[AppliedSectionComponentRow]:
    """Return a practical section template for demo/recovery previews."""

    return [
        AppliedSectionComponentRow("lane:left", "lane", side="left", width=3.5, slope=-0.02, thickness=0.25),
        AppliedSectionComponentRow("lane:right", "lane", side="right", width=3.5, slope=-0.02, thickness=0.25),
        AppliedSectionComponentRow("shoulder:left", "shoulder", side="left", width=1.5, slope=-0.04, thickness=0.20),
        AppliedSectionComponentRow("shoulder:right", "shoulder", side="right", width=1.5, slope=-0.04, thickness=0.20),
        AppliedSectionComponentRow("ditch:left", "ditch", side="left", width=2.4, slope=-0.08),
        AppliedSectionComponentRow("ditch:right", "ditch", side="right", width=2.4, slope=-0.08),
        AppliedSectionComponentRow("daylight:left", "side_slope", side="left", width=8.0, slope=0.33),
        AppliedSectionComponentRow("daylight:right", "side_slope", side="right", width=8.0, slope=0.33),
    ]


def format_earthwork_report(report: dict[str, object]) -> str:
    """Format a concise human-readable earthwork summary."""

    quantity_output = report["quantity_output"]
    earthwork_output = report["earthwork_output"]
    mass_haul_output = report["mass_haul_output"]
    station_row = dict(report.get("station_row", {}) or {})
    focused_balance_row = report.get("focused_balance_row", None)
    focused_haul_zone = report.get("focused_haul_zone", None)

    total_cut = _summary_value(earthwork_output.summary_rows, "total_cut")
    total_fill = _summary_value(earthwork_output.summary_rows, "total_fill")
    curve_count = _summary_value(mass_haul_output.summary_rows, "mass_haul_summary")
    balance_point_count = _summary_value(
        mass_haul_output.summary_rows,
        "balance_point_count",
    )
    final_cumulative_mass = _summary_value(mass_haul_output.summary_rows, "final_cumulative_mass")
    max_surplus_mass = _summary_value(mass_haul_output.summary_rows, "max_surplus_cumulative_mass")
    max_deficit_mass = _summary_value(mass_haul_output.summary_rows, "max_deficit_cumulative_mass")

    return "\n".join(
        [
            "CorridorRoad v1 Earthwork Balance Viewer",
            f"Quantity fragments: {len(quantity_output.fragment_rows)}",
            f"Earthwork windows: {len(earthwork_output.balance_rows)}",
            f"Total cut: {total_cut} m3",
            f"Total fill: {total_fill} m3",
            f"Mass-haul curves: {curve_count}",
            f"Balance points: {balance_point_count}",
            f"Final cumulative mass: {final_cumulative_mass} m3",
            f"Max surplus/deficit: {max_surplus_mass} / {max_deficit_mass} m3",
            f"Key stations: {len(list(report.get('key_station_rows', report.get('station_rows', [])) or []))}",
            *_focus_summary_lines(station_row, focused_balance_row, focused_haul_zone),
        ]
    )


def run_v1_earthwork_balance_command() -> dict[str, object]:
    """Execute the minimal v1 earthwork balance bridge and show a summary."""

    document_label = ""
    preferred_section_set = None
    preferred_station = None
    ui_context = get_ui_context()
    clear_ui_context()
    if App is not None and getattr(App, "ActiveDocument", None) is not None:
        document_label = str(getattr(App.ActiveDocument, "Label", "") or "")
        preferred_section_set, preferred_station = selected_section_target(Gui, App.ActiveDocument)
        if preferred_section_set is None:
            object_name = str(ui_context.get("preferred_section_set_name", "") or "").strip()
            if object_name:
                try:
                    preferred_section_set = App.ActiveDocument.getObject(object_name)
                except Exception:
                    preferred_section_set = None
        if preferred_station is None and ui_context.get("preferred_station", None) is not None:
            try:
                preferred_station = float(ui_context.get("preferred_station"))
            except Exception:
                preferred_station = None

    report = None
    if App is not None and getattr(App, "ActiveDocument", None) is not None:
        report = build_document_earthwork_report(
            App.ActiveDocument,
            preferred_section_set=preferred_section_set,
            preferred_station=preferred_station,
        )
    if report is None:
        report = build_demo_earthwork_report(
            document_label=document_label,
            preferred_station=preferred_station,
        )
    summary_text = format_earthwork_report(report)

    if App is not None:
        App.Console.PrintMessage(summary_text + "\n")

    if Gui is not None:  # pragma: no branch - GUI path only in FreeCAD.
        try:
            Gui.Control.showDialog(EarthworkViewerTaskPanel(report))
        except Exception:
            try:  # pragma: no cover - GUI fallback not available in tests.
                from PySide import QtGui

                QtGui.QMessageBox.information(
                    None,
                    "CorridorRoad v1 Earthwork Balance Viewer",
                    summary_text,
                )
            except Exception:
                pass

    return report


class CmdV1EarthworkBalance:
    """Standalone v1 earthwork balance viewer command."""

    def GetResources(self):
        from freecad.Corridor_Road.misc.resources import icon_path

        return {
            "Pixmap": icon_path("cut_fill.svg"),
            "MenuText": "Earthwork Balance (v1)",
            "ToolTip": "Run the v1 earthwork balance viewer pipeline",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_earthwork_balance_command()


def _summary_value(summary_rows: list[object], kind: str) -> object:
    """Read one summary value by kind from an output payload."""

    for row in summary_rows:
        if getattr(row, "kind", "") == kind:
            return getattr(row, "value", "")
    return ""


def _focus_summary_lines(
    station_row: dict[str, object],
    focused_balance_row,
    focused_haul_zone,
) -> list[str]:
    """Build optional focus lines for one selected station context."""

    lines: list[str] = []
    if station_row:
        station_label = str(
            station_row.get(
                "label",
                f"STA {float(station_row.get('station', 0.0) or 0.0):.3f}",
            )
        )
        lines.append(f"Focus Station: {station_label}")
    if focused_balance_row is not None:
        station_start = getattr(focused_balance_row, "station_start", None)
        station_end = getattr(focused_balance_row, "station_end", None)
        cut_value = getattr(focused_balance_row, "cut_value", 0.0)
        fill_value = getattr(focused_balance_row, "fill_value", 0.0)
        lines.append(f"Focused Window: {float(station_start or 0.0):.3f} -> {float(station_end or 0.0):.3f}")
        lines.append(f"Focused Cut/Fill: {float(cut_value):.3f} / {float(fill_value):.3f} m3")
    if focused_haul_zone is not None:
        zone_kind = str(getattr(focused_haul_zone, "kind", "") or "")
        lines.append(f"Focused Haul Zone: {zone_kind or '(none)'}")
    return lines


def _nearest_balance_row(balance_rows: list[object], station: float | None):
    """Resolve the nearest earthwork balance row for one focus station."""

    if not balance_rows:
        return None
    if station is None:
        return balance_rows[0]
    return min(balance_rows, key=lambda row: _station_interval_distance(row, station))


def _nearest_haul_zone(haul_zone_rows: list[object], station: float | None):
    """Resolve the nearest haul zone for one focus station."""

    if not haul_zone_rows:
        return None
    if station is None:
        return haul_zone_rows[0]
    return min(haul_zone_rows, key=lambda row: _station_interval_distance(row, station))


def _station_interval_distance(row, station: float) -> float:
    """Measure distance from one station to a row interval."""

    station_start = getattr(row, "station_start", None)
    station_end = getattr(row, "station_end", None)
    if station_start is None and station_end is None:
        return abs(float(station))
    if station_start is None:
        station_start = station_end
    if station_end is None:
        station_end = station_start
    lo = float(station_start)
    hi = float(station_end)
    if lo > hi:
        lo, hi = hi, lo
    if lo <= float(station) <= hi:
        return 0.0
    return min(abs(float(station) - lo), abs(float(station) - hi))


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1EarthworkBalance", CmdV1EarthworkBalance())
