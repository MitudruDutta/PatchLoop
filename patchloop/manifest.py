"""Trusted archive identity contract shared by repair and replay."""

from hashlib import sha256
import json
from pathlib import Path

from patchloop.apps import tau_retail as app


def load_manifest() -> dict:
    manifest = json.loads(Path(__file__).with_name("utility_manifest.json").read_text())
    actual = sha256((app.HERE / "reference_calls.json").read_bytes()).hexdigest()
    if manifest["reference_sha256"] != actual:
        raise ValueError("Reference archive changed; utility manifest requires fresh review")
    if not set(manifest["excluded_from_preservation"]) <= {t["id"] for t in app.reference_calls()}:
        raise ValueError("Utility manifest references unknown tasks")
    return manifest
