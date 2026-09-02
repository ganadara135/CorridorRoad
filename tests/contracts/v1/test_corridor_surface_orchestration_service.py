from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from freecad.Corridor_Road.v1.commands import cmd_build_corridor
from freecad.Corridor_Road.v1.services.builders import (
    CorridorSurfaceGeometryBuildRequest,
    CorridorSurfaceGeometryBuildResult,
    CorridorSurfaceOrchestrationService,
)


class _FakeGeometryService:
    def __init__(self, *, failing_role: str = "") -> None:
        self.calls: list[tuple[str, object]] = []
        self.failing_role = failing_role

    def _build(self, role: str, request: object):
        self.calls.append((role, request))
        if role == self.failing_role:
            raise ValueError(f"{role} failed")
        return SimpleNamespace(surface_id=request.surface_id, built_role=role)

    def build_design_surface(self, request: object):
        return self._build("design", request)

    def build_subgrade_surface(self, request: object):
        return self._build("subgrade", request)

    def build_daylight_surface(self, request: object):
        return self._build("daylight", request)

    def build_drainage_surface(self, request: object):
        return self._build("drainage", request)


@pytest.mark.parametrize(
    ("role", "surface_kind"),
    [
        ("design", "design_surface"),
        ("subgrade", "subgrade_surface"),
        ("daylight", "daylight_surface"),
        ("drainage", "drainage_surface"),
    ],
)
def test_orchestration_routes_typed_surface_roles(role: str, surface_kind: str) -> None:
    geometry_request = SimpleNamespace(surface_id=f"surface:{role}")
    geometry_service = _FakeGeometryService()

    result = CorridorSurfaceOrchestrationService(geometry_service).build(
        CorridorSurfaceGeometryBuildRequest(role, geometry_request)
    )

    assert isinstance(result, CorridorSurfaceGeometryBuildResult)
    assert result.status == "ready"
    assert result.surface_role == role
    assert result.surface_kind == surface_kind
    assert result.surface_id == f"surface:{role}"
    assert result.tin_surface.built_role == role
    assert result.diagnostic_rows == ()
    assert geometry_service.calls == [(role, geometry_request)]


@pytest.mark.parametrize(
    ("alias", "role"),
    [
        ("design_surface", "design"),
        ("fg_surface", "design"),
        ("subgrade_surface", "subgrade"),
        ("daylight_surface", "daylight"),
        ("slope_face_surface", "daylight"),
        ("drainage_surface", "drainage"),
    ],
)
def test_orchestration_normalizes_existing_surface_role_aliases(alias: str, role: str) -> None:
    geometry_service = _FakeGeometryService()

    result = CorridorSurfaceOrchestrationService(geometry_service).build(
        CorridorSurfaceGeometryBuildRequest(
            alias,
            SimpleNamespace(surface_id="surface:test"),
        )
    )

    assert result.status == "ready"
    assert result.surface_role == role
    assert geometry_service.calls[0][0] == role


def test_orchestration_returns_typed_unsupported_role_diagnostic() -> None:
    geometry_service = _FakeGeometryService()

    result = CorridorSurfaceOrchestrationService(geometry_service).build(
        CorridorSurfaceGeometryBuildRequest(
            "intersection",
            SimpleNamespace(surface_id="surface:intersection"),
        )
    )

    assert result.status == "unsupported"
    assert result.surface_role == "intersection"
    assert result.surface_kind == ""
    assert result.tin_surface is None
    assert result.diagnostic_rows == ("unsupported_surface_role:intersection",)
    assert result.error_message == "Unsupported corridor surface role: intersection"
    assert geometry_service.calls == []


def test_orchestration_returns_typed_build_failure_diagnostic() -> None:
    geometry_service = _FakeGeometryService(failing_role="daylight")

    result = CorridorSurfaceOrchestrationService(geometry_service).build(
        CorridorSurfaceGeometryBuildRequest(
            "daylight",
            SimpleNamespace(surface_id="surface:daylight"),
        )
    )

    assert result.status == "error"
    assert result.tin_surface is None
    assert result.diagnostic_rows == (
        "surface_build_failed:daylight:ValueError:daylight failed",
    )
    assert result.error_message == "daylight failed"


def test_command_result_adapter_preserves_original_failure_message() -> None:
    surface = SimpleNamespace(surface_id="surface:ready")
    ready = CorridorSurfaceGeometryBuildResult(
        surface_role="design",
        surface_kind="design_surface",
        surface_id="surface:ready",
        status="ready",
        tin_surface=surface,
    )
    failed = CorridorSurfaceGeometryBuildResult(
        surface_role="design",
        surface_kind="design_surface",
        surface_id="surface:failed",
        status="error",
        diagnostic_rows=("surface_build_failed:design:ValueError:original failure",),
        error_message="original failure",
    )

    assert cmd_build_corridor._tin_surface_from_corridor_surface_build_result(
        ready
    ) is surface
    with pytest.raises(RuntimeError, match="^original failure$"):
        cmd_build_corridor._tin_surface_from_corridor_surface_build_result(failed)


def test_top_level_preview_builds_do_not_call_geometry_service_directly() -> None:
    source = inspect.getsource(cmd_build_corridor)

    assert "CorridorSurfaceGeometryService().build_design_surface" not in source
    assert "CorridorSurfaceGeometryService().build_subgrade_surface" not in source
    assert "CorridorSurfaceGeometryService().build_daylight_surface" not in source
    assert "CorridorSurfaceGeometryService().build_drainage_surface" not in source


def test_region_surface_specs_use_roles_without_command_owned_builder_names() -> None:
    specs = cmd_build_corridor._region_surface_role_specs("region:test")

    assert [spec["role"] for spec in specs] == [
        "design",
        "subgrade",
        "daylight",
        "drainage",
    ]
    assert all("builder" not in spec for spec in specs)
