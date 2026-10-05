import importlib

import pytest

from patchloop import cli


@pytest.mark.parametrize("name", sorted(cli.COMMANDS))
def test_every_command_resolves_to_a_module_main(name):
    assert callable(importlib.import_module(cli.COMMANDS[name][0]).main)


def test_unknown_command_prints_usage_and_fails(capsys):
    assert cli.main(["nonsense"]) == 2
    assert "usage: patchloop" in capsys.readouterr().out
    assert cli.main(["--help"]) == 0


def test_subcommand_receives_its_own_arguments(monkeypatch):
    seen = {}
    monkeypatch.setattr("patchloop.evaluation.replay.main", lambda: seen.setdefault("argv", __import__("sys").argv[:]) and 0)
    cli.main(["replay", "--guarded"])
    assert seen["argv"] == ["patchloop replay", "--guarded"]
