"""Exchange output mapper for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import dataclass

from ...models.output.base import OutputModelBase
from ...models.output.exchange_output import ExchangeOutput, ExchangeOutputRef


@dataclass(frozen=True)
class ExchangePackageRequest:
    """Input contract for packaging normalized outputs for exchange."""

    project_id: str
    exchange_output_id: str
    format: str
    package_kind: str
    outputs: list[OutputModelBase]


class ExchangeOutputMapper:
    """Package normalized outputs into one exchange output payload."""

    def map_output_package(self, request: ExchangePackageRequest) -> ExchangeOutput:
        """Create one exchange package from normalized output payloads."""

        output_refs = [
            ExchangeOutputRef(
                ref_id=f"{request.exchange_output_id}:output:{index}",
                output_kind=self._output_kind(output),
                output_id=self._output_id(output),
                schema_version=output.schema_version,
            )
            for index, output in enumerate(request.outputs, start=1)
        ]

        source_refs = self._unique_list(
            ref
            for output in request.outputs
            for ref in output.source_refs
        )
        result_refs = self._unique_list(
            ref
            for output in request.outputs
            for ref in output.result_refs
        )

        return ExchangeOutput(
            schema_version=1,
            project_id=request.project_id,
            exchange_output_id=request.exchange_output_id,
            format=request.format,
            package_kind=request.package_kind,
            label=f"{request.format.upper()} Package",
            selection_scope={
                "scope_kind": "exchange_package",
                "format": request.format,
                "package_kind": request.package_kind,
            },
            source_refs=source_refs,
            result_refs=result_refs,
            output_refs=output_refs,
            payload_metadata={
                "output_count": len(request.outputs),
                "formats": [request.format],
                "output_kinds": [row.output_kind for row in output_refs],
            },
            format_payload={
                "package_kind": request.package_kind,
                "output_ids": [row.output_id for row in output_refs],
            },
        )

    def _output_kind(self, output: OutputModelBase) -> str:
        """Resolve a stable output kind name from one output payload."""

        name = output.__class__.__name__
        if name.endswith("Output"):
            name = name[:-6]
        return name.lower()

    def _output_id(self, output: OutputModelBase) -> str:
        """Resolve the primary output id for one output payload."""

        for attribute_name in (
            "section_output_id",
            "plan_output_id",
            "profile_output_id",
            "surface_output_id",
            "quantity_output_id",
            "earthwork_output_id",
            "mass_haul_output_id",
            "exchange_output_id",
        ):
            value = getattr(output, attribute_name, "")
            if isinstance(value, str) and value:
                return value
        return output.label or output.__class__.__name__.lower()

    def _unique_list(self, values: object) -> list[str]:
        """Preserve order while removing duplicate string refs."""

        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if not isinstance(value, str) or not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered
