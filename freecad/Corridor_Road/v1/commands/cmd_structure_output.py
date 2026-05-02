"""Structure output and exchange command helpers for CorridorRoad v1."""

from __future__ import annotations

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except Exception:  # pragma: no cover - FreeCAD is not available in plain Python.
    App = None
    Gui = None

from freecad.Corridor_Road.misc.resources import icon_path
from freecad.Corridor_Road.qt_compat import QtWidgets

from .cmd_build_corridor import (
    apply_v1_structure_output_package,
    build_document_structure_output_package,
    export_document_structure_output_package_ifc,
    export_document_structure_output_package_json,
    structure_output_package_summary,
)
from ..exchange.exchange_package_export import exchange_package_payload
from ..objects.obj_exchange_package import find_v1_exchange_package


def run_v1_structure_output_command(*, document=None):
    """Open the v1 Structure Output panel."""

    doc = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
    if doc is None:
        raise RuntimeError("No active document.")
    panel = V1StructureOutputTaskPanel(document=doc)
    if Gui is not None and hasattr(Gui, "Control"):
        Gui.Control.showDialog(panel)
    return panel


class V1StructureOutputTaskPanel:
    """Small panel for building and exporting v1 structure output packages."""

    def __init__(self, *, document=None):
        self.document = document or (getattr(App, "ActiveDocument", None) if App is not None else None)
        self.form = self._build_ui()
        self._last_structure_output_package = None
        self._refresh_summary()

    def getStandardButtons(self):
        return 0

    def accept(self):
        return self._build_structure_output_package()

    def reject(self):
        if Gui is not None:
            Gui.Control.closeDialog()
        return True

    def _build_ui(self):
        widget = QtWidgets.QWidget()
        widget.setWindowTitle("CorridorRoad v1 - Structure Output")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Structure Output")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        note = QtWidgets.QLabel("Build source-traceable structure output packages and export JSON or IFC handoff files.")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._summary = QtWidgets.QPlainTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setMinimumHeight(220)
        layout.addWidget(self._summary)

        row = QtWidgets.QHBoxLayout()
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.setToolTip("Refresh the persisted package and export-readiness summary.")
        refresh_button.clicked.connect(self._refresh_summary)
        row.addWidget(refresh_button)
        build_button = QtWidgets.QPushButton("Build/Update Package")
        build_button.setToolTip("Build structure solids, quantities, and the persisted exchange package.")
        build_button.clicked.connect(self._build_structure_output_package)
        row.addWidget(build_button)
        export_json_button = QtWidgets.QPushButton("Export JSON")
        export_json_button.setToolTip("Export the normalized persisted exchange package to JSON.")
        export_json_button.clicked.connect(self._export_structure_output_package_json)
        row.addWidget(export_json_button)
        export_ifc_button = QtWidgets.QPushButton("Export IFC")
        export_ifc_button.setToolTip("Export the IFC4 handoff when no blocking readiness diagnostics exist.")
        export_ifc_button.clicked.connect(self._export_structure_output_package_ifc)
        row.addWidget(export_ifc_button)
        row.addStretch(1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        row.addWidget(close_button)
        layout.addLayout(row)
        return widget

    def _refresh_summary(self):
        package_obj = find_v1_exchange_package(self.document)
        lines = [
            "Structure Output workflow",
            "",
            "Build/Update Package creates or updates a persisted v1 ExchangePackage object.",
            "Export JSON writes the normalized exchange package snapshot.",
            "Export IFC writes the IFC4 structure handoff.",
        ]
        if package_obj is not None:
            readiness_status = str(getattr(package_obj, "ExportReadinessStatus", "") or "unknown")
            lines.extend(
                [
                    "",
                    "Current persisted package:",
                    f"Exchange package: {getattr(package_obj, 'ExchangeOutputId', '')}",
                    f"Format: {getattr(package_obj, 'ExchangeFormat', '')}",
                    f"Structure solids: {int(getattr(package_obj, 'StructureSolidCount', 0) or 0)}",
                    f"Structure segments: {int(getattr(package_obj, 'StructureSolidSegmentCount', 0) or 0)}",
                    f"Export readiness: {readiness_status}",
                    f"IFC export: {_ifc_export_state(readiness_status)}",
                    f"Export diagnostics: {int(getattr(package_obj, 'ExportDiagnosticCount', 0) or 0)}",
                    f"Diagnostic summary: {_package_diagnostic_summary(package_obj)}",
                    f"Payload storage: {getattr(package_obj, 'PayloadStorageMode', '') or 'inline'}",
                    f"Payload bytes: {int(getattr(package_obj, 'PayloadByteCount', 0) or 0)}",
                    f"Quantity fragments: {int(getattr(package_obj, 'QuantityFragmentCount', 0) or 0)}",
                    f"Source contexts: {_package_source_context_summary(package_obj)}",
                ]
            )
        else:
            lines.extend(["", "Current persisted package: none"])
        self._summary.setPlainText("\n".join(lines))

    def _build_structure_output_package(self) -> bool:
        try:
            result = build_document_structure_output_package(self.document)
            self._last_structure_output_package = result
            obj = apply_v1_structure_output_package(document=self.document, package_result=result)
            summary = structure_output_package_summary(result)
            message = "\n".join(
                [
                    "Structure output package has been built.",
                    f"Corridor: {summary['corridor_id']}",
                    f"Structure solids: {summary['solid_count']} ({summary['structure_solid_output_id']})",
                    f"Active structures: {summary.get('active_structure_count', 0)} ({_short_ref_list(summary.get('active_structure_refs', []))})",
                    f"Structure segments: {summary['solid_segment_count']}",
                    f"Export readiness: {summary['export_readiness_status']}",
                    f"IFC export: {_ifc_export_state(summary['export_readiness_status'])}",
                    f"Export diagnostics: {summary['export_diagnostic_count']}",
                    f"Diagnostic summary: {_diagnostic_summary(getattr(result.structure_solid_output, 'diagnostic_rows', []) or [])}",
                    f"Quantity fragments: {summary['quantity_fragment_count']} ({summary['quantity_model_id']})",
                    f"Section outputs: {summary.get('section_output_count', 0)}",
                    f"Source contexts: {summary.get('source_context_count', 0)} "
                    f"(side-slope {summary.get('side_slope_source_context_count', 0)}, "
                    f"bench {summary.get('bench_source_context_count', 0)})",
                    f"Exchange package: {summary['exchange_output_id']} [{summary['exchange_format']}]",
                    f"Packaged outputs: {summary['exchange_output_count']}",
                    f"Payload storage: {getattr(obj, 'PayloadStorageMode', '') or 'inline'}",
                    f"Payload bytes: {int(getattr(obj, 'PayloadByteCount', 0) or 0)}",
                    f"Object: {getattr(obj, 'Label', getattr(obj, 'Name', ''))}",
                ]
            )
            self._summary.setPlainText(message)
            _show_message(self.form, "Structure Output", message)
            return True
        except Exception as exc:
            self._summary.setPlainText(f"Structure output package was not built:\n{exc}")
            _show_message(self.form, "Structure Output", f"Structure output package was not built.\n{exc}")
            return False

    def _export_structure_output_package_json(self) -> bool:
        try:
            path, _filter = QtWidgets.QFileDialog.getSaveFileName(
                self.form,
                "Export Structure Exchange Package",
                "structure_exchange_package.json",
                "JSON Files (*.json);;All Files (*)",
            )
            if not path:
                return False
            info = export_document_structure_output_package_json(path, document=self.document)
            package_obj = find_v1_exchange_package(self.document)
            message = "\n".join(
                [
                    "Structure exchange package JSON has been exported.",
                    f"Path: {info['path']}",
                    f"Exchange package: {info['exchange_output_id']}",
                    f"Structure solids: {info['structure_solid_count']}",
                    f"Structure segments: {info['structure_solid_segment_count']}",
                    f"Export readiness: {info['export_readiness_status']}",
                    f"IFC export: {_ifc_export_state(info['export_readiness_status'])}",
                    f"Export diagnostics: {info['export_diagnostic_count']}",
                    f"Diagnostic summary: {_package_diagnostic_summary(package_obj)}",
                    f"Payload storage: {info['payload_storage_mode']}",
                    f"Payload bytes: {info['payload_byte_count']}",
                    f"Quantity fragments: {info['quantity_fragment_count']}",
                    f"Source contexts: {info.get('source_context_count', 0)} "
                    f"(side-slope {info.get('side_slope_source_context_count', 0)}, "
                    f"bench {info.get('bench_source_context_count', 0)})",
                    f"Packaged outputs: {info['packaged_output_count']}",
                ]
            )
            self._summary.setPlainText(message)
            _show_message(self.form, "Structure Output", message)
            return True
        except Exception as exc:
            self._summary.setPlainText(f"Structure exchange package JSON was not exported:\n{exc}")
            _show_message(self.form, "Structure Output", f"Structure exchange package JSON was not exported.\n{exc}")
            return False

    def _export_structure_output_package_ifc(self) -> bool:
        try:
            path, _filter = QtWidgets.QFileDialog.getSaveFileName(
                self.form,
                "Export Structure IFC Handoff",
                "structure_exchange_package.ifc",
                "IFC Files (*.ifc);;All Files (*)",
            )
            if not path:
                return False
            info = export_document_structure_output_package_ifc(path, document=self.document)
            package_obj = find_v1_exchange_package(self.document)
            message = "\n".join(
                [
                    "Structure IFC handoff has been exported.",
                    f"Path: {info['path']}",
                    f"Exchange package: {info['exchange_output_id']}",
                    f"Structure solids: {info['structure_solid_count']}",
                    f"Structure segments: {info['structure_solid_segment_count']}",
                    f"Export readiness: {info['export_readiness_status']}",
                    f"IFC export: {_ifc_export_state(info['export_readiness_status'])}",
                    f"Export diagnostics: {info['export_diagnostic_count']}",
                    f"Diagnostic summary: {_package_diagnostic_summary(package_obj)}",
                    f"IFC entities: {info['ifc_entity_count']}",
                ]
            )
            self._summary.setPlainText(message)
            _show_message(self.form, "Structure Output", message)
            return True
        except Exception as exc:
            self._summary.setPlainText(f"Structure IFC handoff was not exported:\n{exc}")
            _show_message(self.form, "Structure Output", f"Structure IFC handoff was not exported.\n{exc}")
            return False


class CmdV1StructureOutput:
    """FreeCAD command wrapper for v1 Structure Output."""

    def GetResources(self):
        return {
            "Pixmap": icon_path("structure_output.svg"),
            "MenuText": "Structure Output",
            "ToolTip": "Build and export v1 structure output packages",
        }

    def IsActive(self):
        return App is not None and getattr(App, "ActiveDocument", None) is not None

    def Activated(self):
        run_v1_structure_output_command()


def _show_message(parent, title: str, message: str) -> None:
    try:
        QtWidgets.QMessageBox.information(parent, title, message)
    except Exception:
        pass


def _package_diagnostic_summary(package_obj) -> str:
    if package_obj is None:
        return "none"
    try:
        payload = exchange_package_payload(package_obj)
    except Exception:
        return "unavailable"
    return _diagnostic_summary(list(payload.get("export_diagnostic_rows", []) or []))


def _package_source_context_summary(package_obj) -> str:
    if package_obj is None:
        return "none"
    try:
        metadata = exchange_package_payload(package_obj).get("payload_metadata", {}) or {}
    except Exception:
        return "unavailable"
    total = int(metadata.get("source_context_count", 0) or 0)
    side_slope = int(metadata.get("side_slope_source_context_count", 0) or 0)
    bench = int(metadata.get("bench_source_context_count", 0) or 0)
    return f"{total} (side-slope {side_slope}, bench {bench})"


def _diagnostic_summary(rows: list[object]) -> str:
    severity_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    for row in list(rows or []):
        severity = _row_value(row, "severity").strip().lower()
        kind = _row_value(row, "kind").strip()
        if severity:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if kind:
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
    if not severity_counts and not kind_counts:
        return "none"
    severity_order = ["error", "warning", "info"]
    severity_parts = [
        f"{severity} {severity_counts[severity]}"
        for severity in severity_order
        if severity_counts.get(severity, 0)
    ]
    severity_parts.extend(
        f"{severity} {count}"
        for severity, count in sorted(severity_counts.items())
        if severity not in severity_order
    )
    kind_parts = [
        f"{kind} ({count})" if count > 1 else kind
        for kind, count in sorted(kind_counts.items())
    ]
    if severity_parts and kind_parts:
        return f"{', '.join(severity_parts)}; kinds: {', '.join(kind_parts)}"
    if severity_parts:
        return ", ".join(severity_parts)
    return "kinds: " + ", ".join(kind_parts)


def _short_ref_list(values) -> str:
    refs = [str(value or "").strip() for value in list(values or []) if str(value or "").strip()]
    if not refs:
        return "none"
    if len(refs) <= 3:
        return ", ".join(refs)
    return ", ".join(refs[:3]) + f", +{len(refs) - 3} more"


def _ifc_export_state(readiness_status: object) -> str:
    status = str(readiness_status or "").strip().lower()
    if status == "error":
        return "blocked until error diagnostics are resolved"
    if status == "warning":
        return "allowed with warnings"
    if status == "ready":
        return "ready"
    return "unknown"


def _row_value(row: object, key: str) -> str:
    if isinstance(row, dict):
        return str(row.get(key, "") or "")
    return str(getattr(row, key, "") or "")


if Gui is not None and hasattr(Gui, "addCommand"):  # pragma: no cover - FreeCAD registration only.
    Gui.addCommand("CorridorRoad_V1StructureOutput", CmdV1StructureOutput())
