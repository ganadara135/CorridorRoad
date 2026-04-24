from freecad.Corridor_Road.commands.cmd_review_alignment import (
    build_alignment_review_text,
    run_alignment_review_command,
)


class _Console:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def PrintWarning(self, text: str) -> None:
        self.messages.append(str(text))


class _App:
    def __init__(self, document=None) -> None:
        self.ActiveDocument = document
        self.Console = _Console()


class _Alignment:
    def __init__(self, label: str) -> None:
        self.Label = label
        self.Name = "HorizontalAlignment001"


def test_build_alignment_review_text_includes_next_step() -> None:
    text = build_alignment_review_text(
        document=None,
        alignment=_Alignment("Mainline A"),
        selected_row_label="IP Row 2 | X=50.000 | Y=0.000",
        focus_station_label="STA 50.000 m",
        summary_lines=["Min radius ok"],
    )

    assert "CorridorRoad Alignment Review" in text
    assert "Mainline A" in text
    assert "STA 50.000 m" in text
    assert "Generate Stations after the alignment is stable." in text


def test_run_alignment_review_command_uses_resolved_alignment() -> None:
    calls: list[dict[str, object]] = []
    app = _App(document="DemoDoc")
    alignment = _Alignment("Resolved Alignment")

    result = run_alignment_review_command(
        app_module=app,
        gui_module=None,
        resolve_alignment=lambda doc: alignment,
        show_review=lambda **kwargs: calls.append(kwargs),
    )

    assert result is alignment
    assert len(calls) == 1
    assert calls[0]["document"] == "DemoDoc"
    assert calls[0]["alignment"] is alignment
