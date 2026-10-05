"""Local-only dashboard for synthetic conversations and bounded repair jobs."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import secrets
from threading import Lock
from urllib.parse import urlsplit
from uuid import uuid4
import zipfile

from patchloop.evaluation.agent import SupportSession
from patchloop.evaluation.campaign import BudgetedClient, run_campaign, run_cycle, scenarios
from patchloop.repair.loop import write_json
from patchloop.providers import NebiusClient, ProviderError
from patchloop.sandbox import SandboxGuard
from patchloop.repair.versions import VersionStore

STATIC = Path(__file__).with_name("web")


class LocalProduct:
    def __init__(self, store, output, model, client=None):
        self.store, self.output, self.model = Path(store), Path(output), model
        self.client = BudgetedClient(client, requests=80) if client is not None else None
        self.sessions, self.jobs = {}, {}
        self.lock = Lock()
        self.provider_lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.active = None

    def provider(self):
        with self.provider_lock:
            if self.client is None:
                self.client = BudgetedClient(NebiusClient(), requests=80)
            return self.client

    def state(self):
        guard = VersionStore(self.store).current_guard(default_interface="adapter")
        return {"model": self.model or None, "configured": bool(self.model and
            (self.client is not None or os.getenv("NEBIUS_API_KEY"))),
            "source_hash": guard.source_hash, "interface": guard.interface, "source": guard.source,
            "activated": (self.store / "current.json").exists(),
            "model_requests": self.client.calls if self.client else 0, "request_limit": 80,
            "active_job": self.active, "scope": "Local synthetic retail. Lookup is fixture identification, not production authentication.",
            "example": scenarios(b"dashboard-example", 1)[0]}

    def start(self, mode):
        with self.lock:
            if len(self.sessions) >= 8:
                raise ValueError("Local session limit reached; restart the server")
            if mode not in {"active", "baseline", "reference"}:
                raise ValueError("Unknown conversation condition")
            identifier = secrets.token_urlsafe(24)
            guard = VersionStore(self.store).current_guard(default_interface="adapter") if mode == "active" else None
            self.sessions[identifier] = (SupportSession(self.provider(), self.model,
                guard=guard, reference=mode == "reference"), Lock())
            return {"session_id": identifier, "conversation": self.sessions[identifier][0].view()}

    def turn(self, identifier, text):
        if identifier not in self.sessions:
            raise ValueError("Unknown session")
        session, lock = self.sessions[identifier]
        if not lock.acquire(blocking=False):
            raise ValueError("This conversation is already running")
        try:
            view = session.turn(text)
            directory = self.output / "sessions" / identifier
            directory.mkdir(parents=True, exist_ok=True)
            write_json(directory / "conversation.json", view)
            return view
        finally:
            lock.release()

    def challenge(self, cycle):
        with self.lock:
            if not self.model:
                raise ValueError("Set NEBIUS_MODEL in the server environment")
            self.provider()
            if self.active is not None:
                raise ValueError("A challenge is already running")
            if len(self.jobs) >= 8:
                raise ValueError("Local job limit reached; restart the server")
            identifier = uuid4().hex
            self.active = identifier
            self.jobs[identifier] = {"id": identifier, "status": "running", "result": None, "patch": None}
        self.executor.submit(self._run_job, identifier, cycle)
        return deepcopy(self.jobs[identifier])

    def _run_job(self, identifier, cycle):
        output = self.output / identifier
        try:
            if cycle:
                result = run_cycle(output, self.store, self.model, client=self.provider())
                snapshot = result.get("after_guard") or result["before_guard"]
                guard = SandboxGuard(snapshot["source"], interface=snapshot["interface"])
                campaign = result.get("after") or result["before"]
            else:
                guard = VersionStore(self.store).current_guard(default_interface="adapter")
                result = run_campaign(output, self.provider(), self.model,
                    cases=scenarios(secrets.token_bytes(32), 1),
                    guard=guard, turns=2)
                campaign = result
            patch = None
            if cycle and (result.get("repair") or {}).get("attempts"):
                attempts = result["repair"]["attempts"]
                entry = attempts[-1]
                directory = output / "repair" / f"candidate-{entry['attempt']}"
                patch = {"source": (directory / "guard.py").read_text() if (directory / "guard.py").exists() else None,
                    "diff": (directory / "guard.patch").read_text() if (directory / "guard.patch").exists() else None,
                    "validation": entry.get("validation"), "status": entry["status"]}
            with self.lock:
                conversation = campaign["scenarios"][0]["conversation"]
                events = [item["event"] for item in conversation["timeline"] if item["kind"] == "tool"]
                reproduction = {"interface": guard.interface, "source_hash": guard.source_hash,
                    "timeline": conversation["timeline"], "expected": {"source_hash": guard.source_hash,
                        "events": events, "calls": len(events),
                        "executed_violations": sum(bool(e["executed_violations"]) for e in events),
                        "errors": sum(e["outcome"] == "error" for e in events)}}
                self.jobs[identifier].update(status="finished", result=result, patch=patch,
                                            source=guard.source, reproduction=reproduction)
        except Exception:
            # No exception body: deployment/provider paths may contain private data.
            with self.lock:
                self.jobs[identifier].update(status="failed", error="Job failed; inspect local artifacts")
        finally:
            with self.lock:
                self.active = None

    def job(self, identifier):
        with self.lock:
            if identifier not in self.jobs:
                raise ValueError("Unknown job")
            return deepcopy(self.jobs[identifier])

    def bundle(self, identifier):
        job = self.job(identifier)
        if job["status"] != "finished":
            raise ValueError("A completed job is required")
        record = job["reproduction"]
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("guard.py", job["source"])
            archive.writestr("reproduce.json", json.dumps(record, indent=2))
            archive.writestr("README.txt", "Use the same PatchLoop checkout and Python environment.\n"
                "python -m patchloop.evaluation.reproduce reproduce.json --guard guard.py\n"
                "This replays recorded calls without inference and checks the recorded effects.\n"
                "For fresh private checks and complete utility replay:\n"
                f"python -m patchloop.repair --verify guard.py --interface {record['interface']}\n"
                "The bundle excludes credentials, model request payloads and private evaluator seeds.\n")
        return buffer.getvalue()


def handler(product):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def valid_host(self):
            port = self.server.server_address[1]
            return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

        def send(self, status, body, content_type="application/json", extra=None):
            data = json.dumps(body).encode() if content_type == "application/json" else body
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            for name, value in (extra or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {"error": "Local host required"})
            path = urlsplit(self.path).path
            try:
                if path == "/api/state":
                    return self.send(200, product.state())
                if path.startswith("/api/jobs/"):
                    return self.send(200, product.job(path.rsplit("/", 1)[1]))
                if path.startswith("/api/bundle/"):
                    return self.send(200, product.bundle(path.rsplit("/", 1)[1]), "application/zip",
                                     {"Content-Disposition": 'attachment; filename="patchloop-reproduction.zip"'})
                files = {"/": ("index.html", "text/html; charset=utf-8"),
                         "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                         "/style.css": ("style.css", "text/css; charset=utf-8")}
                if path not in files:
                    return self.send(404, {"error": "Not found"})
                filename, mime = files[path]
                return self.send(200, (STATIC / filename).read_bytes(), mime)
            except ValueError as exc:
                self.send(400, {"error": str(exc)})
            except Exception:
                self.send(500, {"error": "Local artifact could not be read"})

        def do_POST(self):
            if (not self.valid_host() or self.headers.get("Origin") != f"http://{self.headers.get('Host')}"
                    or self.headers.get("Content-Type") != "application/json"):
                return self.send(403, {"error": "Same-origin JSON request required"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 16000:
                    raise ValueError("Request size outside local limits")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("Request must be an object")
                path = urlsplit(self.path).path
                if path == "/api/session":
                    return self.send(200, product.start(payload.get("mode", "active")))
                if path == "/api/turn":
                    return self.send(200, product.turn(payload["session_id"], payload["text"]))
                if path == "/api/challenge":
                    if type(payload.get("cycle", False)) is not bool:
                        raise ValueError("Cycle must be a boolean")
                    return self.send(202, product.challenge(payload.get("cycle", False)))
                self.send(404, {"error": "Not found"})
            except (ValueError, KeyError, ProviderError) as exc:
                self.send(400, {"error": str(exc) if not isinstance(exc, KeyError) else "Missing request field"})
            except Exception:
                self.send(500, {"error": "Local operation failed"})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--store", type=Path, default=Path("artifacts/product-versions"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/product"))
    args = parser.parse_args()
    product = LocalProduct(args.store, args.output, os.getenv("NEBIUS_MODEL", ""))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(product))
    print(f"PatchLoop local dashboard: http://127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        product.executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
