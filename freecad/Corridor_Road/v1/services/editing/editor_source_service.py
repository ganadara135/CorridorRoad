"""UI-independent source-edit preparation for v1 editors.

These services validate draft identity and table contracts without reading a
FreeCAD document or constructing Qt widgets. Persistence remains an explicit
command/object-adapter step after preparation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Iterable, TypeVar

from ...models.source.alignment_model import AlignmentModel
from ...models.source.assembly_model import AssemblySubassemblyModel
from ...models.source.drainage_model import DrainageModel
from ...models.source.profile_model import ProfileModel
from ...models.source.structure_model import StructureModel
from ...models.source.subassembly_definition_model import SubassemblyLibrary


SourceT = TypeVar("SourceT")


@dataclass(frozen=True)
class PreparedSourceEdit(Generic[SourceT]):
    """Non-mutating result at the editor Apply/Save boundary."""

    model: SourceT
    source_id: str
    row_count: int
    diagnostics: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return not any(row.startswith("error|") for row in self.diagnostics)


@dataclass(frozen=True)
class SourceEditorViewModel(Generic[SourceT]):
    """Qt-independent editor summary for complex table state."""

    source: SourceT
    source_id: str
    row_count: int
    diagnostics: tuple[str, ...] = ()


def prepare_structure_edit(model: StructureModel) -> PreparedSourceEdit[StructureModel]:
    return _prepare_model(
        model,
        StructureModel,
        source_id=getattr(model, "structure_model_id", ""),
        rows=getattr(model, "structure_rows", ()),
        row_id="structure_id",
    )


def prepare_profile_edit(model: ProfileModel) -> PreparedSourceEdit[ProfileModel]:
    return _prepare_model(
        model,
        ProfileModel,
        source_id=getattr(model, "profile_id", ""),
        rows=getattr(model, "control_rows", ()),
        row_id="control_point_id",
    )


def prepare_alignment_edit(model: AlignmentModel) -> PreparedSourceEdit[AlignmentModel]:
    return _prepare_model(
        model,
        AlignmentModel,
        source_id=getattr(model, "alignment_id", ""),
        rows=getattr(model, "geometry_sequence", ()),
        row_id="element_id",
    )


def prepare_drainage_edit(model: DrainageModel) -> PreparedSourceEdit[DrainageModel]:
    return _prepare_model(
        model,
        DrainageModel,
        source_id=getattr(model, "drainage_model_id", ""),
        rows=getattr(model, "element_rows", ()),
        row_id="drainage_element_id",
    )


def prepare_assembly_edit(
    model: AssemblySubassemblyModel,
) -> PreparedSourceEdit[AssemblySubassemblyModel]:
    templates = list(getattr(model, "template_rows", ()) or ())
    rows = [row for template in templates for row in (getattr(template, "subassembly_rows", ()) or ())]
    return _prepare_model(
        model,
        AssemblySubassemblyModel,
        source_id=getattr(model, "assembly_id", ""),
        rows=rows,
        row_id="subassembly_id",
    )


def prepare_subassembly_library_edit(
    model: SubassemblyLibrary,
) -> PreparedSourceEdit[SubassemblyLibrary]:
    return _prepare_model(
        model,
        SubassemblyLibrary,
        source_id=getattr(model, "library_id", ""),
        rows=getattr(model, "definition_rows", ()),
        row_id="definition_id",
    )


def editor_view_model(prepared: PreparedSourceEdit[SourceT]) -> SourceEditorViewModel[SourceT]:
    return SourceEditorViewModel(
        source=prepared.model,
        source_id=prepared.source_id,
        row_count=prepared.row_count,
        diagnostics=prepared.diagnostics,
    )


def prepare_profile_control_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return _prepare_mapping_rows(rows, row_id="control_point_id")


def prepare_profile_vertical_curve_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return _prepare_mapping_rows(rows, row_id="curve_id")


def prepare_alignment_element_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return _prepare_mapping_rows(rows, row_id="element_id")


def _prepare_model(model, expected_type, *, source_id: object, rows, row_id: str):
    if not isinstance(model, expected_type):
        raise TypeError(f"Expected {expected_type.__name__}, got {type(model).__name__}.")
    normalized_rows = list(rows or ())
    diagnostics = _identity_diagnostics(normalized_rows, row_id=row_id)
    source_text = str(source_id or "").strip()
    if not source_text:
        diagnostics.insert(0, f"warning|source_id_missing|{expected_type.__name__}")
    return PreparedSourceEdit(
        model=model,
        source_id=source_text,
        row_count=len(normalized_rows),
        diagnostics=tuple(diagnostics),
    )


def _prepare_mapping_rows(rows: Iterable[dict[str, object]], *, row_id: str) -> list[dict[str, object]]:
    normalized = [dict(row or {}) for row in rows]
    diagnostics = _identity_diagnostics(normalized, row_id=row_id)
    errors = [row for row in diagnostics if row.startswith("error|")]
    if errors:
        raise ValueError("; ".join(errors))
    return normalized


def _identity_diagnostics(rows, *, row_id: str) -> list[str]:
    seen: set[str] = set()
    diagnostics: list[str] = []
    for index, row in enumerate(rows, start=1):
        value = row.get(row_id, "") if isinstance(row, dict) else getattr(row, row_id, "")
        identity = str(value or "").strip()
        if not identity:
            diagnostics.append(f"warning|row_id_missing|{row_id}|row={index}")
            continue
        if identity in seen:
            diagnostics.append(f"error|row_id_duplicate|{row_id}|{identity}")
        seen.add(identity)
    return diagnostics


__all__ = [
    "PreparedSourceEdit",
    "SourceEditorViewModel",
    "editor_view_model",
    "prepare_alignment_edit",
    "prepare_alignment_element_rows",
    "prepare_assembly_edit",
    "prepare_drainage_edit",
    "prepare_profile_control_rows",
    "prepare_profile_edit",
    "prepare_profile_vertical_curve_rows",
    "prepare_structure_edit",
    "prepare_subassembly_library_edit",
]
