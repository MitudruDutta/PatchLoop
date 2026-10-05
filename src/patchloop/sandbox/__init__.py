"""Linux-only, fail-closed execution of one generated guard function.

The candidate sees only explicitly supplied JSON contexts, runtime libraries,
and a read-only standalone runner. It has no project/data/test/secret mounts.
This is a bounded execution boundary, not a universal kernel-isolation proof.
"""

import ast
from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
from uuid import uuid4


class SandboxError(RuntimeError):
    pass


def validate_source(source: str):
    if not isinstance(source, str) or len(source.encode()) > 65_536:
        raise SandboxError("Candidate source exceeds 64 KiB limit")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise SandboxError("Candidate is not valid Python") from None
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise SandboxError("Candidate must contain only def allow(context)")
    function = tree.body[0]
    args = function.args
    if (function.name != "allow" or function.decorator_list or function.returns
            or len(args.args) != 1 or args.args[0].arg != "context" or args.args[0].annotation
            or args.posonlyargs or args.kwonlyargs or args.vararg or args.kwarg or args.defaults):
        raise SandboxError("Candidate must define undecorated allow(context) without annotations")


@dataclass(frozen=True)
class SandboxGuard:
    source: str
    timeout: float = 5.0
    interface: str = "fixed"
    backend: str = field(default_factory=lambda: os.getenv("PATCHLOOP_SANDBOX", "bwrap"))

    def __post_init__(self):
        validate_source(self.source)
        if self.interface not in {"fixed", "adapter"}:
            raise ValueError("Unknown guard interface")
        if self.backend not in {"bwrap", "docker"}:
            raise ValueError("Choose bwrap or docker isolation")
        if not 0 < self.timeout <= 30:
            raise ValueError("Sandbox timeout must be between 0 and 30 seconds")

    @property
    def source_hash(self) -> str:
        return sha256(self.source.encode()).hexdigest()

    def __call__(self, context: dict) -> bool:
        return self.decide_many([context])[0]

    def decide_many(self, contexts: list[dict]) -> list[bool]:
        payload = json.dumps({"source": self.source, "contexts": contexts}).encode()
        if len(payload) > 2_000_000 or len(contexts) > 10_000:
            raise SandboxError("Context batch exceeds sandbox input limits")
        container = None
        if self.backend == "docker":
            docker = shutil.which("docker")
            if not docker:
                raise SandboxError("Docker is required for container isolation; no unsafe fallback")
            container = f"patchloop-guard-{uuid4().hex}"
            command = [docker, "run", "--rm", "--name", container, "--pull", "never",
                "--network", "none", "--ipc", "none", "--read-only", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--pids-limit", "24",
                "--memory", "384m", "--memory-swap", "384m", "--cpus", "1",
                "--user", "65534:65534", "--workdir", "/", "--log-driver", "none",
                "--interactive", "patchloop-guard:local"]
        else:
            bwrap = shutil.which("bwrap")
            if not bwrap or not Path("/usr/bin/python3").exists():
                raise SandboxError("Linux bubblewrap and /usr/bin/python3 are required; no unsafe fallback")
            command = [bwrap, "--unshare-all", "--die-with-parent", "--new-session",
                       "--cap-drop", "ALL", "--ro-bind", "/usr", "/usr"]
            for path in ("/lib", "/lib64"):
                if Path(path).exists():
                    command.extend(["--ro-bind", path, path])
            command.extend(["--proc", "/proc", "--dev", "/dev",
                            "--ro-bind", str(Path(__file__).with_name("worker.py")),
                            "/worker.py", "--remount-ro", "/", "--remount-ro", "/dev",
                            "--chdir", "/", "--",
                            "/usr/bin/python3", "-I", "-S", "/worker.py"])
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            try:
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=output,
                                           stderr=errors, start_new_session=True,
                                           env={"PATH": "/usr/bin", "LANG": "C.UTF-8"})
                try:
                    process.communicate(payload, timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                    raise SandboxError("Candidate exceeded wall-time limit") from None
                if process.returncode:
                    raise SandboxError("Candidate or sandbox failed; no successful decision recorded")
                output.seek(0)
                response = json.loads(output.read(1_048_577))
            except (OSError, ValueError):
                raise SandboxError("Sandbox returned no valid decision response") from None
            finally:
                if container is not None:
                    # Killing the attached CLI alone would leave its worker alive.
                    try:
                        subprocess.run([docker, "rm", "--force", container], timeout=10,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env={"PATH": "/usr/bin", "LANG": "C.UTF-8"}, check=False)
                    except (OSError, subprocess.TimeoutExpired):
                        raise SandboxError("Container cleanup failed; stop further candidate execution") from None
        if (not isinstance(response, dict) or set(response) != {"decisions"}
                or not isinstance(response["decisions"], list)
                or len(response["decisions"]) != len(contexts)
                or any(type(value) is not bool for value in response["decisions"])):
            raise SandboxError("Sandbox returned malformed decisions")
        return response["decisions"]
