"""The `patchloop` command. Each subcommand runs one module's existing CLI."""

import importlib
import sys

COMMANDS = {
    "report": ("patchloop.sdk.report", "Summarize SDK recordings by tool and decision"),
    "doctor": ("patchloop.sdk.doctor", "Check a PatchLoop setup for gaps in protection"),
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
