from http.server import ThreadingHTTPServer
import io
import json
from threading import Thread
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

import pytest

from patchloop.dashboard import LocalProduct, handler
from patchloop.providers import ProviderError
from patchloop.reproduce import reproduce
from patchloop.versions import BASELINE_SOURCE, VersionStore, source_hash


class TestClient:
    def chat(self, messages, **kwargs):
        return {"message": {"role": "assistant", "content": "Synthetic conversation ready."},
                "request_id": "offline-scripted", "usage": {"total_tokens": 2}}

    def complete(self, messages, **kwargs):
        return {"content": "Show me my orders.", "request_id": "offline-scripted", "usage": {"total_tokens": 2}}


@pytest.fixture
def local(tmp_path):
    product = LocalProduct(tmp_path / "versions", tmp_path / "jobs", "nvidia/test-nemotron", TestClient())
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(product))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield product, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    thread.join()
    product.executor.shutdown(wait=True)


def request(base, path, payload=None, **headers):
    data = json.dumps(payload).encode() if payload is not None else None
    if data is not None:
        headers = {"Origin": base, "Content-Type": "application/json", **headers}
    return urlopen(Request(base + path, data=data, headers=headers), timeout=10)


def test_html_api_conversation_and_no_nextjs(local):
    product, base = local
    with request(base, "/") as response:
        assert b"Challenge this version" in response.read()
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    state = json.load(request(base, "/api/state"))
    assert state["source_hash"] == source_hash(BASELINE_SOURCE)
    session = json.load(request(base, "/api/session", {"mode": "active"}))
    view = json.load(request(base, "/api/turn", {"session_id": session["session_id"], "text": "Hello"}))
    assert view["timeline"][-1]["text"] == "Synthetic conversation ready."
    assert view["messages"][-1]["role"] == "assistant"
    assert product.client.calls == 1


def test_origin_host_and_path_boundaries(local):
    _, base = local
    for path, payload, headers, status in [
        ("/api/session", {}, {"Origin": "https://untrusted.invalid"}, 403),
        ("/api/state", None, {"Host": "untrusted.invalid"}, 403),
        ("/../.env", None, {}, 404),
        ("/api/turn", {"session_id": "missing", "text": "hello"}, {}, 400),
    ]:
        with pytest.raises(HTTPError) as error:
            request(base, path, payload, **headers)
        assert error.value.code == status


def test_job_bundle_freezes_source_and_observed_results(local):
    product, base = local
    job = json.load(request(base, "/api/challenge", {"cycle": False}))
    deadline = time.monotonic() + 10
    while product.job(job["id"])["status"] == "running" and time.monotonic() < deadline:
        time.sleep(.02)
    done = product.job(job["id"])
    assert done["status"] == "finished", done
    # Changing the current version must not change the evidence bundle.
    VersionStore(product.store).promote("def allow(context):\n    return False\n",
        expected_parent=source_hash(BASELINE_SOURCE), evidence_hash="test")
    data = request(base, "/api/bundle/" + job["id"]).read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert set(archive.namelist()) == {"guard.py", "reproduce.json", "README.txt"}
        record = json.loads(archive.read("reproduce.json"))
        source = archive.read("guard.py").decode()
        assert source == BASELINE_SOURCE
        assert reproduce(record, source)["calls"] == 0
        record["expected"]["calls"] += 1
        with pytest.raises(ValueError, match="effects"):
            reproduce(record, source)


def test_failed_cycle_keeps_report_and_does_not_publish_success(local, monkeypatch):
    from patchloop import dashboard
    product, base = local
    monkeypatch.setattr(dashboard, "run_cycle", lambda *args, **kwargs: (_ for _ in ()).throw(ProviderError("failed")))
    job = product.challenge(True)
    product.executor.shutdown(wait=True)
    assert product.job(job["id"])["status"] == "failed"
    assert product.active is None


def test_one_running_challenge_and_session_limits(local):
    product, _ = local
    product.active = "running"
    with pytest.raises(ValueError, match="already running"):
        product.challenge(False)
    product.active = None
    for _ in range(8):
        product.start("reference")
    with pytest.raises(ValueError, match="session limit"):
        product.start("active")
