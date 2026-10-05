"""Replay a dashboard evidence bundle offline, verifying its source and effects."""

import argparse
import json
from pathlib import Path

from patchloop.agent import replay_conversation
from patchloop.sandbox import SandboxGuard


def reproduce(record, source):
    guard = SandboxGuard(source, interface=record["interface"])
    if guard.source_hash != record["source_hash"]:
        raise ValueError("Bundle guard hash mismatch")
    actual = replay_conversation(record["timeline"], guard=guard)
    if json.dumps(actual, sort_keys=True) != json.dumps(record["expected"], sort_keys=True):
        raise ValueError("Recorded effects did not reproduce")
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--guard", type=Path, required=True)
    args = parser.parse_args()
    result = reproduce(json.loads(args.record.read_text()), args.guard.read_text())
    print(json.dumps({key: value for key, value in result.items() if key != "events"}))


if __name__ == "__main__":
    main()
