"""Immutable guard artifacts and locked compare-and-swap activation."""

from contextlib import contextmanager
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

BASELINE_SOURCE = "def allow(context):\n    return True\n"


def source_hash(source: str) -> str:
    return sha256(source.encode()).hexdigest()


class StaleVersion(RuntimeError):
    pass


class VersionStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _locked(self):
        self.path.mkdir(parents=True, exist_ok=True)
        with (self.path / ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def current(self) -> str:
        pointer = self.path / "current.json"
        if not pointer.exists():
            return BASELINE_SOURCE
        record = json.loads(pointer.read_text())
        digest = record["source_hash"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid guard version identifier")
        source = (self.path / f"{digest}.py").read_text()
        if source_hash(source) != digest:
            raise ValueError("Guard artifact hash does not match activated version")
        return source

    def promote(self, source: str, *, expected_parent: str, evidence_hash: str):
        with self._locked():
            if source_hash(self.current()) != expected_parent:
                raise StaleVersion("Parent changed during validation; candidate was not activated")
            digest = source_hash(source)
            artifact = self.path / f"{digest}.py"
            try:
                with artifact.open("x") as file:
                    file.write(source)
            except FileExistsError:
                if artifact.read_text() != source:
                    raise ValueError("Existing guard artifact has been modified") from None
            record = {"source_hash": digest, "parent_hash": expected_parent,
                      "evidence_hash": evidence_hash}
            fd, name = tempfile.mkstemp(prefix=".current-", dir=self.path)
            try:
                with os.fdopen(fd, "w") as file:
                    json.dump(record, file, indent=2)
                    file.write("\n")
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(name, self.path / "current.json")
            finally:
                if os.path.exists(name):
                    os.unlink(name)
