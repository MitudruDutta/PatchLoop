"""Standalone worker mounted into an otherwise isolated namespace.

No project imports. Never launch this directly on an untrusted candidate;
patchloop.sandbox supplies the namespace, clean environment and limits.
"""

import contextlib
import io
import json
import os
import resource
import sys


def isolated_decision(code, context):
    """Fork the untouched worker for each context, including module state."""
    reader, writer = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(reader)
        try:
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
    request = json.loads(sys.stdin.buffer.read(2_000_001))
    code = compile(request["source"], "/candidate.py", "exec")
    decisions = [isolated_decision(code, context) for context in request["contexts"]]
    sys.stdout.write(json.dumps({"decisions": decisions}))


if __name__ == "__main__":
    main()
