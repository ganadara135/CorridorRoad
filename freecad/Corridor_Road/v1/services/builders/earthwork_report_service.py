"""V1-native earthwork report builder."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.diagnostics import DiagnosticMessage
from ...models.output.earthwork_output import EarthworkBalanceOutput, MassHaulOutput
from ...models.output.quantity_output import QuantityOutput
from ...models.result.applied_section_set import AppliedSectionSet
from ...models.result.corridor_model import CorridorModel
from ...models.result.earthwork_balance_model import EarthworkBalanceModel
from ...models.result.mass_haul_model import MassHaulModel
from ...models.result.quantity_model import QuantityModel
from ...models.result.tin_surface import TINSurface
from ..mapping import EarthworkOutputMapper, QuantityOutputMapper
from .earthwork_analysis_service import (
    EarthworkAnalysisBuildRequest,
    EarthworkAnalysisResult,
    EarthworkAnalysisService,
)
from .earthwork_balance_service import EarthworkBalanceBuildRequest, EarthworkBalanceService
from .earthwork_quantity_service import EarthworkQuantityBuildRequest, EarthworkQuantityService
from .mass_haul_service import MassHaulBuildRequest, MassHaulService


@dataclass(frozen=True)
class EarthworkReportBuildRequest:
    """Input contract for building a complete v1 earthwork report payload."""

    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    existing_ground_surface: TINSurface | None
    report_id: str
    usable_cut_ratio: float = 0.85


@dataclass(frozen=True)
class EarthworkReportResult:
    """Complete v1 earthwork analysis/result/output bundle."""

    report_id: str
    project_id: str
    corridor: CorridorModel
    applied_section_set: AppliedSectionSet
    analysis_result: EarthworkAnalysisResult
    quantity_model: QuantityModel
    earthwork_model: EarthworkBalanceModel
    mass_haul_model: MassHaulModel
    quantity_output: QuantityOutput
    earthwork_output: EarthworkBalanceOutput
    mass_haul_output: MassHaulOutput
    diagnostic_rows: list[DiagnosticMessage] = field(default_factory=list)
    status: str = "empty"
    notes: str = ""


class EarthworkReportService:
    """Build the v1-native earthwork analysis, balance, and output stack."""

    def __init__(
        self,
        *,
        analysis_service: EarthworkAnalysisService | None = None,
        quantity_service: EarthworkQuantityService | None = None,
        balance_service: EarthworkBalanceService | None = None,
        mass_haul_service: MassHaulService | None = None,
        earthwork_output_mapper: EarthworkOutputMapper | None = None,
        quantity_output_mapper: QuantityOutputMapper | None = None,
    ) -> None:
        self.analysis_service = analysis_service or EarthworkAnalysisService()
        self.quantity_service = quantity_service or EarthworkQuantityService()
        self.balance_service = balance_service or EarthworkBalanceService()
        self.mass_haul_service = mass_haul_service or MassHaulService()
        self.earthwork_output_mapper = earthwork_output_mapper or EarthworkOutputMapper()
        self.quantity_output_mapper = quantity_output_mapper or QuantityOutputMapper()

    def build(self, request: EarthworkReportBuildRequest) -> EarthworkReportResult:
        """Build one complete v1 earthwork report result."""

        analysis_result = self.analysis_service.build(
            EarthworkAnalysisBuildRequest(
                project_id=request.project_id,
                applied_section_set=request.applied_section_set,
                existing_ground_surface=request.existing_ground_surface,
                analysis_id=f"{request.report_id}:analysis",
            )
        )
        quantity_model = self.quantity_service.build(
            EarthworkQuantityBuildRequest(
                project_id=request.project_id,
                corridor=request.corridor,
                applied_section_set=request.applied_section_set,
                earthwork_analysis_result=analysis_result,
                quantity_model_id=f"{request.report_id}:quantity",
            )
        )
        earthwork_model = self.balance_service.build(
            EarthworkBalanceBuildRequest(
                project_id=request.project_id,
                corridor=request.corridor,
                applied_section_set=request.applied_section_set,
                quantity_model=quantity_model,
                earthwork_balance_id=f"{request.report_id}:balance",
                usable_cut_ratio=request.usable_cut_ratio,
            )
        )
        earthwork_model.diagnostic_rows = list(quantity_model.diagnostic_rows)

        mass_haul_model = self.mass_haul_service.build(
            MassHaulBuildRequest(
                project_id=request.project_id,
                corridor=request.corridor,
                earthwork_balance_model=earthwork_model,
                mass_haul_id=f"{request.report_id}:mass-haul",
            )
        )
        mass_haul_model.diagnostic_rows = list(earthwork_model.diagnostic_rows)

        quantity_output = self.quantity_output_mapper.map_quantity_model(quantity_model)
        earthwork_output = self.earthwork_output_mapper.map_earthwork_balance(earthwork_model)
        mass_haul_output = self.earthwork_output_mapper.map_mass_haul(mass_haul_model)
        diagnostics = self._diagnostic_rows(
            analysis_result=analysis_result,
            quantity_model=quantity_model,
            earthwork_model=earthwork_model,
            mass_haul_model=mass_haul_model,
        )

        return EarthworkReportResult(
            report_id=request.report_id,
            project_id=request.project_id,
            corridor=request.corridor,
            applied_section_set=request.applied_section_set,
            analysis_result=analysis_result,
            quantity_model=quantity_model,
            earthwork_model=earthwork_model,
            mass_haul_model=mass_haul_model,
            quantity_output=quantity_output,
            earthwork_output=earthwork_output,
            mass_haul_output=mass_haul_output,
            diagnostic_rows=diagnostics,
            status=self._status(earthwork_model=earthwork_model, diagnostics=diagnostics),
            notes=self._notes(
                analysis_result=analysis_result,
                quantity_model=quantity_model,
                earthwork_model=earthwork_model,
                mass_haul_model=mass_haul_model,
                diagnostics=diagnostics,
            ),
        )

    @staticmethod
    def _diagnostic_rows(
        *,
        analysis_result: EarthworkAnalysisResult,
        quantity_model: QuantityModel,
        earthwork_model: EarthworkBalanceModel,
        mass_haul_model: MassHaulModel,
    ) -> list[DiagnosticMessage]:
        rows: list[DiagnosticMessage] = []
        seen: set[tuple[str, str, str]] = set()
        for source_rows in (
            getattr(analysis_result, "diagnostic_rows", []) or [],
            getattr(quantity_model, "diagnostic_rows", []) or [],
            getattr(earthwork_model, "diagnostic_rows", []) or [],
            getattr(mass_haul_model, "diagnostic_rows", []) or [],
        ):
            for row in list(source_rows or []):
                key = (str(row.severity), str(row.kind), str(row.message))
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
        return rows

    @staticmethod
    def _status(
        *,
        earthwork_model: EarthworkBalanceModel,
        diagnostics: list[DiagnosticMessage],
    ) -> str:
        if not getattr(earthwork_model, "balance_rows", []):
            return "empty"
        if any(row.severity == "error" for row in diagnostics):
            return "partial"
        if diagnostics:
            return "partial"
        return "ok"

    @staticmethod
    def _notes(
        *,
        analysis_result: EarthworkAnalysisResult,
        quantity_model: QuantityModel,
        earthwork_model: EarthworkBalanceModel,
        mass_haul_model: MassHaulModel,
        diagnostics: list[DiagnosticMessage],
    ) -> str:
        return (
            f"Earthwork report built: area_fragments={len(analysis_result.area_fragment_rows)}, "
            f"quantity_fragments={len(quantity_model.fragment_rows)}, "
            f"balance_rows={len(earthwork_model.balance_rows)}, "
            f"mass_curves={len(mass_haul_model.curve_rows)}, "
            f"diagnostics={len(diagnostics)}."
        )
