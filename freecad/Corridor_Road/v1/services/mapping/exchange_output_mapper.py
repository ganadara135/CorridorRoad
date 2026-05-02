"""Exchange output mapper for CorridorRoad v1."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass

from ...models.output.base import OutputModelBase
from ...models.output.exchange_output import ExchangeOutput, ExchangeOutputRef


_SIDE_SLOPE_COMPONENT_KINDS = {"side_slope", "bench", "daylight"}
_SIDE_SLOPE_QUANTITY_KINDS = {"bench_surface_length", "slope_face_length"}
_SIDE_SLOPE_MEASUREMENT_KINDS = {"section_side_slope_breakline"}


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
        source_context_rows = self._source_context_rows(request.outputs)
        diagnostic_rows = self._diagnostic_rows(request.outputs)

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
                "structure_solid_count": self._structure_solid_count(request.outputs),
                "structure_solid_segment_count": self._structure_solid_segment_count(request.outputs),
                "source_context_count": len(source_context_rows),
                "side_slope_source_context_count": self._source_context_count(
                    source_context_rows,
                    scope="side_slope",
                ),
                "bench_source_context_count": self._bench_source_context_count(source_context_rows),
                "region_ref_count": len(self._source_ref_values(request.outputs, "region_ref")),
                "assembly_ref_count": len(self._source_ref_values(request.outputs, "assembly_ref")),
                "structure_ref_count": len(self._source_ref_values(request.outputs, "structure_ref")),
                "diagnostic_count": len(diagnostic_rows),
                "diagnostic_error_count": self._diagnostic_count(request.outputs, severity="error"),
                "diagnostic_warning_count": self._diagnostic_count(request.outputs, severity="warning"),
            },
            format_payload={
                "package_kind": request.package_kind,
                "output_ids": [row.output_id for row in output_refs],
                "structure_solid_rows": self._structure_solid_rows(request.outputs),
                "structure_solid_segment_rows": self._structure_solid_segment_rows(request.outputs),
                "source_context_rows": source_context_rows,
                "diagnostic_rows": diagnostic_rows,
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
            "structure_solid_output_id",
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

    def _structure_solid_count(self, outputs: list[OutputModelBase]) -> int:
        return sum(len(list(getattr(output, "solid_rows", []) or [])) for output in list(outputs or []))

    def _structure_solid_segment_count(self, outputs: list[OutputModelBase]) -> int:
        return sum(len(list(getattr(output, "solid_segment_rows", []) or [])) for output in list(outputs or []))

    def _structure_solid_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for output in list(outputs or []):
            output_id = self._output_id(output)
            for row in list(getattr(output, "solid_rows", []) or []):
                payload = asdict(row)
                payload["output_ref"] = output_id
                rows.append(payload)
        return rows

    def _structure_solid_segment_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for output in list(outputs or []):
            output_id = self._output_id(output)
            for row in list(getattr(output, "solid_segment_rows", []) or []):
                payload = asdict(row)
                payload["output_ref"] = output_id
                rows.append(payload)
        return rows

    def _source_context_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        seen: set[tuple[str, str, str, str, str, str, str]] = set()
        for output in list(outputs or []):
            output_id = self._output_id(output)
            output_kind = self._output_kind(output)
            for payload in self._source_context_payloads(output):
                key = (
                    output_id,
                    str(payload.get("context_kind", "") or ""),
                    str(payload.get("region_ref", "") or ""),
                    str(payload.get("assembly_ref", "") or ""),
                    str(payload.get("structure_ref", "") or ""),
                    str(payload.get("component_ref", "") or ""),
                    str(payload.get("source_row_ref", "") or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                payload["context_row_id"] = f"{output_id}:source-context:{len(rows) + 1}"
                payload["output_ref"] = output_id
                payload["output_kind"] = output_kind
                rows.append(payload)
        return rows

    def _source_context_payloads(self, output: OutputModelBase) -> list[dict[str, object]]:
        payloads: list[dict[str, object]] = []
        for row in list(getattr(output, "solid_rows", []) or []):
            payloads.append(
                {
                    "context_kind": "structure_solid",
                    "region_ref": str(getattr(row, "region_ref", "") or ""),
                    "assembly_ref": str(getattr(row, "assembly_ref", "") or ""),
                    "structure_ref": str(getattr(row, "structure_ref", "") or getattr(row, "structure_id", "") or ""),
                    "source_row_ref": str(getattr(row, "output_object_id", "") or ""),
                }
            )
        for row in list(getattr(output, "component_rows", []) or []):
            if not self._is_side_slope_component_row(row):
                continue
            payloads.append(
                {
                    "context_kind": "section_side_slope_component",
                    "scope": "side_slope",
                    "region_ref": str(getattr(row, "region_ref", "") or ""),
                    "assembly_ref": str(getattr(row, "assembly_ref", "") or ""),
                    "structure_ref": self._structure_ref_from_notes(str(getattr(row, "notes", "") or "")),
                    "source_row_ref": str(
                        getattr(row, "component_row_id", "") or getattr(row, "component_id", "") or ""
                    ),
                    "component_ref": str(getattr(row, "component_id", "") or ""),
                    "template_ref": str(getattr(row, "template_ref", "") or ""),
                    "component_kind": str(getattr(row, "kind", "") or ""),
                    "notes": str(getattr(row, "notes", "") or ""),
                }
            )
        for row in list(getattr(output, "fragment_rows", []) or []):
            is_side_slope = self._is_side_slope_quantity_row(row)
            payloads.append(
                {
                    "context_kind": "side_slope_quantity_fragment" if is_side_slope else "quantity_fragment",
                    "scope": "side_slope" if is_side_slope else "",
                    "region_ref": str(getattr(row, "region_ref", "") or ""),
                    "assembly_ref": str(getattr(row, "assembly_ref", "") or ""),
                    "structure_ref": str(getattr(row, "structure_ref", "") or ""),
                    "source_row_ref": str(getattr(row, "fragment_row_id", "") or getattr(row, "fragment_id", "") or ""),
                    "component_ref": str(getattr(row, "component_ref", "") or ""),
                    "quantity_kind": str(getattr(row, "quantity_kind", "") or ""),
                    "measurement_kind": str(getattr(row, "measurement_kind", "") or ""),
                }
            )
        return [
            payload
            for payload in payloads
            if any(str(payload.get(key, "") or "") for key in ("region_ref", "assembly_ref", "structure_ref"))
        ]

    def _is_side_slope_component_row(self, row: object) -> bool:
        kind = str(getattr(row, "kind", "") or "").strip().lower()
        notes = str(getattr(row, "notes", "") or "").strip().lower()
        return kind in _SIDE_SLOPE_COMPONENT_KINDS or "scope=side_slope" in notes

    def _is_side_slope_quantity_row(self, row: object) -> bool:
        quantity_kind = str(getattr(row, "quantity_kind", "") or "").strip().lower()
        measurement_kind = str(getattr(row, "measurement_kind", "") or "").strip().lower()
        return quantity_kind in _SIDE_SLOPE_QUANTITY_KINDS or measurement_kind in _SIDE_SLOPE_MEASUREMENT_KINDS

    def _structure_ref_from_notes(self, notes: str) -> str:
        for note in str(notes or "").split(";"):
            key, separator, value = note.strip().partition("=")
            if separator and key.strip() == "structure_refs":
                return str(value or "").split(",", 1)[0].strip()
        return ""

    def _source_context_count(
        self,
        source_context_rows: list[dict[str, object]],
        *,
        scope: str,
    ) -> int:
        expected = str(scope or "").strip().lower()
        return sum(
            1
            for row in source_context_rows
            if str(row.get("scope", "") or "").strip().lower() == expected
        )

    def _bench_source_context_count(self, source_context_rows: list[dict[str, object]]) -> int:
        return sum(
            1
            for row in source_context_rows
            if str(row.get("component_kind", "") or "").strip().lower() == "bench"
            or str(row.get("quantity_kind", "") or "").strip().lower() == "bench_surface_length"
        )

    def _source_ref_values(self, outputs: list[OutputModelBase], attribute_name: str) -> list[str]:
        return self._unique_list(
            str(row.get(attribute_name, "") or "")
            for row in self._source_context_rows(outputs)
            if str(row.get(attribute_name, "") or "")
        )

    def _diagnostic_rows(self, outputs: list[OutputModelBase]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for output in list(outputs or []):
            output_id = self._output_id(output)
            for row in list(getattr(output, "diagnostic_rows", []) or []):
                if hasattr(row, "__dataclass_fields__"):
                    payload = asdict(row)
                else:
                    payload = {
                        "severity": str(getattr(row, "severity", "") or ""),
                        "kind": str(getattr(row, "kind", "") or ""),
                        "message": str(getattr(row, "message", "") or ""),
                        "notes": str(getattr(row, "notes", "") or ""),
                    }
                payload["output_ref"] = output_id
                rows.append(payload)
        return rows

    def _diagnostic_count(self, outputs: list[OutputModelBase], *, severity: str) -> int:
        expected = str(severity or "").strip().lower()
        return sum(
            1
            for row in self._diagnostic_rows(outputs)
            if str(row.get("severity", "") or "").strip().lower() == expected
        )
