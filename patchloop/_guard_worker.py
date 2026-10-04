"""Standalone worker mounted into an otherwise isolated namespace.

No project imports. Never launch this directly on an untrusted candidate;
patchloop.sandbox supplies the namespace, clean environment and limits.
"""

import contextlib
import ctypes
import io
import json
import os
import resource
import sys


class RejectOriginalStream(io.TextIOBase):
    def write(self, value):
        raise RuntimeError("Candidate cannot write to the original worker stream")


def isolated_decision(code, context):
    """Fork the untouched worker for each context, including module state."""
    reader, writer = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(reader)
        try:
            # High-level redirect_stdout alone leaves shared OS descriptors open.
            sink = os.open("/dev/null", os.O_WRONLY)
            os.dup2(sink, 1)
            os.dup2(sink, 2)
            if sink not in (1, 2):
                os.close(sink)
            sys.__stdout__ = sys.__stderr__ = RejectOriginalStream()
            namespace = {}
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                exec(code, namespace)
                value = namespace["allow"](context)
            if type(value) is not bool:
                raise TypeError("Guard must return bool")
            sys.__stdout__.flush()
            sys.__stderr__.flush()
            os.write(writer, b"true" if value else b"false")
        except BaseException:
            os._exit(1)
        os._exit(0)
    os.close(writer)
    try:
        response = os.read(reader, 16)
    finally:
        os.close(reader)
    _, status = os.waitpid(pid, 0)
    if status != 0 or response not in (b"true", b"false"):
        raise RuntimeError("Context execution returned no valid decision")
    return response == b"true"


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    # Child guards share a UID with the trusted worker. Deny opening its
    # descriptors/memory via /proc, even though filesystem mounts are read-only.
    if ctypes.CDLL(None).prctl(4, 0, 0, 0, 0) != 0:  # PR_SET_DUMPABLE
        raise RuntimeError("Cannot isolate worker parent state")
    request = json.loads(sys.stdin.buffer.read(2_000_001))
    code = compile(request["source"], "/candidate.py", "exec")
    decisions = [isolated_decision(code, context) for context in request["contexts"]]
    sys.stdout.write(json.dumps({"decisions": decisions}))


if __name__ == "__main__":
    main()
