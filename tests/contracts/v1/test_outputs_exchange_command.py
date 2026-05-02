from freecad.Corridor_Road.commands.cmd_outputs_exchange import CmdOutputsExchange


def test_outputs_exchange_command_uses_outputs_exchange_icon() -> None:
    resources = CmdOutputsExchange().GetResources()

    assert resources["MenuText"] == "Outputs & Exchange"
    assert str(resources["Pixmap"]).replace("\\", "/").endswith("outputs_exchange.svg")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[PASS] outputs exchange command tests completed.")
