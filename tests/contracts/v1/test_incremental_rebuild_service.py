import pytest

from freecad.Corridor_Road.v1.models.result.incremental_rebuild import IncrementalStageRecord
from freecad.Corridor_Road.v1.services.evaluation.incremental_rebuild_service import IncrementalRebuildService


def test_presentation_only_change_reuses_accepted_result() -> None:
    service = IncrementalRebuildService()
    engineering_input = {"alignment": [0.0, 10.0], "visibility": True, "style": "review"}
    first = service.decide(
        stage_name="applied_sections",
        service_version="2",
        engineering_input=engineering_input,
    )
    execution = service.execute(
        decision=first,
        service_version="2",
        builder=lambda: {"sections": [0.0, 10.0]},
        consumed_source_refs=("alignment:main",),
    )

    second = service.decide(
        stage_name="applied_sections",
        service_version="2",
        engineering_input={"alignment": [0.0, 10.0], "visibility": False, "style": "print"},
        previous_record=execution.record,
    )
    reused = service.execute(
        decision=second,
        service_version="2",
        builder=lambda: pytest.fail("builder must not run for an unchanged engineering fingerprint"),
        previous_result=execution.result,
        previous_record=execution.record,
    )

    assert second.reuse_previous is True
    assert reused.result is execution.result
    assert reused.diagnostics == ("accepted_result_reused",)


def test_source_service_and_dependency_changes_report_explicit_stale_reasons() -> None:
    service = IncrementalRebuildService()
    previous = IncrementalStageRecord(
        stage_name="surface_model",
        service_version="1",
        input_fingerprint=service.engineering_fingerprint({"corridor": "a"}),
        accepted=True,
    )

    decision = service.decide(
        stage_name="surface_model",
        service_version="2",
        engineering_input={"corridor": "b"},
        previous_record=previous,
        dependency_changed_stages=("corridor_model",),
    )

    assert decision.rebuild_required is True
    assert decision.changed_stages == ("corridor_model",)
    assert decision.stale_reasons == (
        "service_version_changed",
        "engineering_input_changed",
        "dependency_result_changed",
    )


def test_failed_builder_does_not_replace_previous_accepted_record() -> None:
    service = IncrementalRebuildService()
    previous = IncrementalStageRecord(
        stage_name="corridor_model",
        service_version="1",
        input_fingerprint="sha256:old",
        result_fingerprint="sha256:accepted",
        accepted=True,
    )
    decision = service.decide(
        stage_name="corridor_model",
        service_version="1",
        engineering_input={"applied_sections": "changed"},
        previous_record=previous,
    )

    with pytest.raises(RuntimeError, match="interrupted"):
        service.execute(
            decision=decision,
            service_version="1",
            builder=lambda: (_ for _ in ()).throw(RuntimeError("interrupted")),
            previous_result={"accepted": True},
            previous_record=previous,
        )

    assert previous.accepted is True
    assert previous.result_fingerprint == "sha256:accepted"


def test_successful_build_records_duration_refs_and_changed_stages() -> None:
    ticks = iter((10.0, 10.025))
    service = IncrementalRebuildService(clock=lambda: next(ticks))
    decision = service.decide(
        stage_name="corridor_model",
        service_version="3",
        engineering_input={"applied_sections": "set:1"},
        dependency_changed_stages=("applied_sections",),
    )

    execution = service.execute(
        decision=decision,
        service_version="3",
        builder=lambda: {"corridor": "result:1"},
        consumed_source_refs=("alignment:main", "alignment:main"),
        consumed_result_refs=("applied-sections:main",),
    )

    assert execution.record.accepted is True
    assert execution.record.duration_ms == pytest.approx(25.0)
    assert execution.record.consumed_source_refs == ("alignment:main",)
    assert execution.record.consumed_result_refs == ("applied-sections:main",)
    assert execution.record.changed_stages == ("applied_sections", "corridor_model")
