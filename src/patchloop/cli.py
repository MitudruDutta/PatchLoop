"""The `patchloop` command. Each subcommand runs one module's existing CLI."""

import importlib
import sys

COMMANDS = {
    "replay": ("patchloop.evaluation.replay", "Replay the reference tasks; --guarded checks a guard"),
    "demo": ("patchloop.evaluation.demo", "Offline before/after comparison with the reference guard"),
    "campaign": ("patchloop.evaluation.campaign", "Run a live tester campaign or a find-repair-retest cycle"),
    "compare": ("patchloop.evaluation.compare", "Compare repair strategies at matched budgets"),
    "reproduce": ("patchloop.evaluation.reproduce", "Replay a downloaded reproduction bundle without model calls"),
    "repair": ("patchloop.repair.loop", "Generate, validate and promote a guard; --verify checks a saved guard"),
    "export": ("patchloop.repair.export", "Export an accepted guard as a reviewable patch"),
    "dashboard": ("patchloop.dashboard", "Start the local dashboard"),
    "providers": ("patchloop.providers", "Check model and search provider access"),
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv or argv[0] not in COMMANDS:
        print("usage: patchloop <command> [options]\n\ncommands:")
        for name, (_, summary) in COMMANDS.items():
            print(f"  {name:<10} {summary}")
        return 0 if argv[:1] in (["-h"], ["--help"]) else 2
    module = importlib.import_module(COMMANDS[argv[0]][0])
    sys.argv = [f"patchloop {argv[0]}", *argv[1:]]
    return module.main()
