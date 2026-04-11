# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Corridor failure-path diagnostics smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_corridor_failure_diagnostics.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_corridor_loft import CorridorLoft
from freecad.Corridor_Road.objects.obj_section_set import SectionSet


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def _build_missing_source_case():
    doc = App.newDocument("CRCorridorDiagMissingSource")
    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    doc.recompute()

    status = str(getattr(cor, "Status", "") or "")
    export_rows = list(getattr(cor, "ExportSummaryRows", []) or [])
    _assert(status.startswith("Missing SourceSectionSet"), "Missing-source corridor should report missing source status")
    _assert("diagSource=error" in status, "Missing-source status should expose diagSource=error")
    _assert("diagConnectivity=error" in status, "Missing-source status should expose diagConnectivity=error")
    _assert("diagPackaging=ok" in status, "Missing-source status should expose diagPackaging=ok")
    _assert("diagPolicy=ok" in status, "Missing-source status should expose diagPolicy=ok")
    _assert(str(getattr(cor, "DiagnosticSummary", "-") or "-") == "source=error, connectivity=error, packaging=ok, policy=ok", "Missing-source DiagnosticSummary mismatch")
    _assert(str(getattr(cor, "SourceDiagnostic", "-") or "-") == "error|missing_section_set", "Missing-source SourceDiagnostic mismatch")
    _assert(str(getattr(cor, "ConnectivityDiagnostic", "-") or "-") == "error|not_built", "Missing-source ConnectivityDiagnostic mismatch")
    _assert(len(export_rows) == 1 and "diagSource=error" in export_rows[0], "Missing-source export summary should expose diagnostic states")

    App.closeDocument(doc.Name)


def _build_execution_failure_case():
    doc = App.newDocument("CRCorridorDiagExecutionFailure")
    sec = doc.addObject("Part::FeaturePython", "SectionSet")
    SectionSet(sec)
    cor = doc.addObject("Part::FeaturePython", "CorridorLoft")
    CorridorLoft(cor)
    cor.SourceSectionSet = sec
    doc.recompute()

    status = str(getattr(cor, "Status", "") or "")
    export_rows = list(getattr(cor, "ExportSummaryRows", []) or [])
    _assert(status.startswith("ERROR:"), "Execution-failure corridor should report ERROR status")
    _assert("diagSource=ok" in status, "Execution-failure status should expose diagSource=ok")
    _assert("diagConnectivity=error" in status, "Execution-failure status should expose diagConnectivity=error")
    _assert("diagPackaging=ok" in status, "Execution-failure status should expose diagPackaging=ok")
    _assert("diagPolicy=ok" in status, "Execution-failure status should expose diagPolicy=ok")
    _assert(str(getattr(cor, "DiagnosticSummary", "-") or "-") == "source=ok, connectivity=error, packaging=ok, policy=ok", "Execution-failure DiagnosticSummary mismatch")
    _assert(str(getattr(cor, "SourceDiagnostic", "-") or "-") == "ok|section_set", "Execution-failure SourceDiagnostic mismatch")
    _assert(str(getattr(cor, "ConnectivityDiagnostic", "-") or "-").startswith("error|execution_failed|"), "Execution-failure ConnectivityDiagnostic mismatch")
    _assert(len(export_rows) == 1 and "diagConnectivity=error" in export_rows[0], "Execution-failure export summary should expose diagnostic states")

    App.closeDocument(doc.Name)


def run():
    _build_missing_source_case()
    _build_execution_failure_case()
    print("[PASS] Corridor failure-path diagnostics smoke test completed.")


if __name__ == "__main__":
    run()
