"""Plan/profile viewer command bridge for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in test env.
    App = None
    Gui = None

from ..models.source.alignment_model import AlignmentElement, AlignmentModel
from ..models.source.profile_model import ProfileControlPoint, ProfileModel
from ..services.evaluation import LegacyDocumentAdapter
from ..services.mapping import PlanOutputMapper, ProfileOutputMapper
from ..ui.common import clear_ui_context, get_ui_context
from ..ui.viewers import PlanProfileViewerTaskPanel
from .cmd_earthwork_balance import build_document_earthwork_report
from .selection_context import selected_alignment_profile_target


def _build_key_station_rows(
    station_values: list[tuple[float, str]] | None,
    *,
    current_station: float | None,
) -> list[dict[str, object]]:
    """Build a compact station-navigation payload for the plan/profile viewer."""

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

    candidate_indexes = {
        0,
        max(0, current_index - 2),
        max(0, current_index - 1),
        current_index,
        min(len(unique_rows) - 1, current_index + 1),
        min(len(unique_rows) - 1, current_index + 2),
        len(unique_rows) - 1,
    }

    result = []
    for output_index, row_index in enumerate(sorted(candidate_indexes)):
        station_value, label = unique_rows[row_index]
        if row_index == 0:
            navigation_kind = "first"
        elif row_index == len(unique_rows) - 1:
            navigation_kind = "last"
        elif row_index == current_index:
            navigation_kind = "current"
        elif row_index < current_index:
            navigation_kind = "previous"
        else:
            navigation_kind = "next"
        result.append(
            {
                "index": row_index,
                "station": station_value,
                "label": label or f"STA {station_value:.3f}",
                "navigation_kind": navigation_kind,
                "is_current": bool(row_index == current_index),
                "navigation_order": output_index,
            }
        )
    return result


def build_document_plan_profile_preview(
    document,
    *,
    preferred_alignment=None,
    preferred_profile=None,
) -> dict[str, object] | None:
    """Build a v1 plan/profile viewer payload from a FreeCAD document."""

    adapter = LegacyDocumentAdapter()
    project = adapter._find_project(document)
    alignment_model = adapter.build_alignment_model(
        document,
        preferred_alignment=preferred_alignment,
    )
    profile_model = adapter.build_profile_model(
        document,
        preferred_profile=preferred_profile,
        preferred_alignment=preferred_alignment,
    )
    alignment_object = adapter._resolve_alignment_object(
        project,
        document,
        preferred_alignment=preferred_alignment,
    )
    profile_object = adapter._resolve_vertical_alignment_object(
        project,
        document,
        preferred_profile=preferred_profile,
    )
    if alignment_model is None and profile_model is None:
        return None

    earthwork_model = None
    try:
        report = build_document_earthwork_report(document)
        if report is not None:
            earthwork_model = report.get("earthwork_model")
    except Exception:
        earthwork_model = None

    plan_output = PlanOutputMapper().map_alignment_model(alignment_model) if alignment_model is not None else None
    profile_output = (
        ProfileOutputMapper().map_profile_model(profile_model, earthwork_model)
        if profile_model is not None
        else None
    )
    current_station = None
    station_values: list[tuple[float, str]] = []
    if plan_output is not None:
        for row in list(getattr(plan_output, "station_rows", []) or []):
            station_values.append(
                (
                    float(getattr(row, "station", 0.0) or 0.0),
                    str(getattr(row, "station_label", "") or f"STA {float(getattr(row, 'station', 0.0) or 0.0):.3f}"),
                )
            )
    if profile_output is not None:
        for row in list(getattr(profile_output, "pvi_rows", []) or []):
            station_values.append(
                (
                    float(getattr(row, "station", 0.0) or 0.0),
                    str(getattr(row, "label", "") or f"STA {float(getattr(row, 'station', 0.0) or 0.0):.3f}"),
                )
            )
    if profile_output is not None and getattr(profile_output, "pvi_rows", None):
        current_station = float(getattr(profile_output.pvi_rows[0], "station", 0.0) or 0.0)
    elif plan_output is not None and getattr(plan_output, "station_rows", None):
        current_station = float(getattr(plan_output.station_rows[0], "station", 0.0) or 0.0)
    return {
        "alignment_model": alignment_model,
        "profile_model": profile_model,
        "plan_output": plan_output,
        "profile_output": profile_output,
        "earthwork_model": earthwork_model,
        "key_station_rows": _build_key_station_rows(
            station_values,
            current_station=current_station,
        ),
        "legacy_objects": {
            "project": project,
            "alignment": alignment_object,
            "profile": profile_object,
        },
    }


def build_demo_plan_profile_preview(document_label: str = "") -> dict[str, object]:
    """Build a minimal in-memory plan/profile viewer payload."""

    alignment_model = AlignmentModel(
        schema_version=1,
        project_id="corridorroad-v1-demo",
        alignment_id="alignment:v1-demo",
        label=document_label or "CorridorRoad v1 Demo Alignment",
        geometry_sequence=[
            AlignmentElement(
                element_id="alignment:v1-demo:1",
                kind="tangent",
                station_start=0.0,
                station_end=40.0,
                length=40.0,
                geometry_payload={
                    "x_values": [1000.0, 1040.0],
                    "y_values": [2000.0, 2000.0],
                },
            ),
            AlignmentElement(
                element_id="alignment:v1-demo:2",
                kind="transition_curve",
                station_start=40.0,
                station_end=80.0,
                length=40.0,
                geometry_payload={
                    "x_values": [1040.0, 1070.0, 1080.0],
                    "y_values": [2000.0, 2010.0, 2040.0],
                },
            ),
        ],
    )
    profile_model = ProfileModel(
        schema_version=1,
        project_id="corridorroad-v1-demo",
        profile_id="profile:v1-demo",
        alignment_id=alignment_model.alignment_id,
        label=document_label or "CorridorRoad v1 Demo Profile",
        control_rows=[
            ProfileControlPoint(
                control_point_id="profile:v1-demo:pvi:1",
                station=0.0,
                elevation=12.0,
                kind="grade_break",
            ),
            ProfileControlPoint(
                control_point_id="profile:v1-demo:pvi:2",
                station=40.0,
                elevation=13.5,
                kind="pvi",
            ),
            ProfileControlPoint(
                control_point_id="profile:v1-demo:pvi:3",
                station=80.0,
                elevation=12.8,
                kind="grade_break",
            ),
        ],
    )

    plan_output = PlanOutputMapper().map_alignment_model(alignment_model)
    profile_output = ProfileOutputMapper().map_profile_model(profile_model)
    return {
        "alignment_model": alignment_model,
        "profile_model": profile_model,
        "plan_output": plan_output,
        "profile_output": profile_output,
        "earthwork_model": None,
        "key_station_rows": _build_key_station_rows(
            [
                (0.0, "STA 0.000"),
                (40.0, "STA 40.000"),
                (80.0, "STA 80.000"),
            ],
            current_station=0.0,
        ),
        "legacy_objects": {},
    }


def format_plan_profile_preview(preview: dict[str, object]) -> str:
    """Format a concise human-readable plan/profile viewer summary."""

    alignment_model = preview.get("alignment_model")
    profile_model = preview.get("profile_model")
    plan_output = preview.get("plan_output")
    profile_output = preview.get("profile_output")
    viewer_context = dict(preview.get("viewer_context", {}) or {})

    lines = [
        "CorridorRoad v1 Plan/Profile Viewer",
        f"Alignment: {getattr(alignment_model, 'label', '') or '(missing)'}",
        f"Alignment elements: {len(list(getattr(plan_output, 'geometry_rows', []) or []))}",
        f"Plan stations: {len(list(getattr(plan_output, 'station_rows', []) or []))}",
        f"Profile: {getattr(profile_model, 'label', '') or '(missing)'}",
        f"Profile controls: {len(list(getattr(profile_output, 'pvi_rows', []) or []))}",
        f"Earthwork attachments: {len(list(getattr(profile_output, 'earthwork_rows', []) or []))}",
        f"Key stations: {len(list(preview.get('key_station_rows', []) or []))}",
    ]
    source_panel = str(viewer_context.get("source_panel", "") or "").strip()
    focus_station_label = str(viewer_context.get("focus_station_label", "") or "").strip()
    selected_row = str(viewer_context.get("selected_row_label", "") or "").strip()
    if source_panel:
        lines.append(f"Context Source: {source_panel}")
    if focus_station_label:
        lines.append(f"Focus Station: {focus_station_label}")
    if selected_row:
        lines.append(f"Selected Row: {selected_row}")
    return "\n".join(lines)


def show_v1_plan_profile_preview(
    *,
    document=None,
    preferred_alignment=None,
    preferred_profile=None,
    extra_context: dict[str, object] | None = None,
    app_module=None,
    gui_module=None,
) -> dict[str, object]:
    """Build and show one v1 plan/profile viewer for a given document context."""

    app = App if app_module is None else app_module
    gui = Gui if gui_module is None else gui_module
    active_document = document
    if active_document is None and app is not None:
        active_document = getattr(app, "ActiveDocument", None)

    document_label = ""
    if active_document is not None:
        document_label = str(getattr(active_document, "Label", "") or "")
    preview = None
    if active_document is not None:
        preview = build_document_plan_profile_preview(
            active_document,
            preferred_alignment=preferred_alignment,
            preferred_profile=preferred_profile,
        )
    if preview is None:
        preview = build_demo_plan_profile_preview(document_label=document_label)
    if extra_context:
        preview.update(dict(extra_context))
    preview["key_station_rows"] = list(preview.get("key_station_rows", []) or [])
    summary_text = format_plan_profile_preview(preview)

    if app is not None:
        app.Console.PrintMessage(summary_text + "\n")

    if gui is not None and hasattr(gui, "Control"):  # pragma: no branch - GUI path only in FreeCAD.
        try:
            gui.Control.showDialog(PlanProfileViewerTaskPanel(preview))
        except Exception:
            try:  # pragma: no cover - GUI fallback not available in tests.
                from PySide import QtGui

                QtGui.QMessageBox.information(
                    None,
                    "CorridorRoad v1 Plan/Profile Viewer",
                    summary_text,
                )
            except Exception:
                pass

    return preview


def run_v1_plan_profile_preview_command() -> dict[str, object]:
    """Execute the minimal v1 plan/profile viewer bridge and show a summary."""

    preferred_alignment = None
    preferred_profile = None
    extra_context = None
    ui_context = get_ui_context()
    clear_ui_context()
    if App is not None and getattr(App, "ActiveDocument", None) is not None:
        preferred_alignment, preferred_profile = selected_alignment_profile_target(Gui, App.ActiveDocument)
        if preferred_alignment is None:
            object_name = str(ui_context.get("preferred_alignment_name", "") or "").strip()
            if object_name:
                try:
                    preferred_alignment = App.ActiveDocument.getObject(object_name)
                except Exception:
                    preferred_alignment = None
        if preferred_profile is None:
            object_name = str(ui_context.get("preferred_profile_name", "") or "").strip()
            if object_name:
                try:
                    preferred_profile = App.ActiveDocument.getObject(object_name)
                except Exception:
                    preferred_profile = None
        extra_context = {}
        for key in (
            "viewer_context",
            "station_row",
            "source",
        ):
            if key in ui_context:
                extra_context[key] = ui_context[key]
        if extra_context.get("viewer_context", None):
            viewer_context = dict(extra_context.get("viewer_context", {}) or {})
            if ui_context.get("preferred_station", None) is not None:
                try:
                    viewer_context["focus_station"] = float(ui_context.get("preferred_station"))
                except Exception:
                    pass
            extra_context["viewer_context"] = viewer_context
        if not extra_context:
            extra_context = None

    return show_v1_plan_profile_preview(
        document=getattr(App, "ActiveDocument", None) if App is not None else None,
        preferred_alignment=preferred_alignment,
        preferred_profile=preferred_profile,
        extra_context=extra_context,
        app_module=App,
        gui_module=Gui,
    )


class CmdV1ReviewPlanProfile:
    """Standalone v1 plan/profile viewer command."""

    def GetResources(self):
        from freecad.Corridor_Road.misc.resources import icon_path

        return {
            "Pixmap": icon_path("alignment.svg"),
            "MenuText": "Plan/Profile Review (v1)",
            "ToolTip": "Run the v1 plan/profile viewer pipeline",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_plan_profile_preview_command()


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1ReviewPlanProfile", CmdV1ReviewPlanProfile())
