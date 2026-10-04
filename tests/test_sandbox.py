import os

import pytest

from patchloop.sandbox import SandboxError, SandboxGuard


def test_decisions_are_computed_inside_namespace():
    guard = SandboxGuard('def allow(context):\n    return context["owner_id"] == context["authenticated_user_id"]\n')
    assert guard.decide_many([
        {"owner_id": "one", "authenticated_user_id": "one"},
        {"owner_id": "other", "authenticated_user_id": "one"},
    ]) == [True, False]


def test_host_credentials_and_project_files_are_not_visible(monkeypatch, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("not mounted")
    monkeypatch.setenv("NEBIUS_API_KEY", "not-passed-to-candidate")
    source = f'''def allow(context):
    import os
    return "NEBIUS_API_KEY" not in os.environ and not os.path.exists({str(secret)!r})
'''
    assert SandboxGuard(source)({}) is True


def test_network_is_unshared():
    source = '''def allow(context):
    import socket
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=0.1)
    except OSError:
        return True
    return False
'''
    assert SandboxGuard(source)({}) is True


@pytest.mark.parametrize("source", [
    "def allow(context):\n    return 1\n",
    "def allow(context):\n    raise RuntimeError('fake success')\n",
    "def allow(context):\n    import os\n    os._exit(0)\n",
    "def allow(context):\n    import sys\n    sys.__stdout__.write('forged output')\n    return True\n",
])
def test_invalid_and_forged_output_never_scores_success(source):
    with pytest.raises(SandboxError):
        SandboxGuard(source)({})


def test_infinite_candidate_is_terminated():
    with pytest.raises(SandboxError, match="wall-time"):
        SandboxGuard("def allow(context):\n    while True: pass\n", timeout=0.2)({})


def test_missing_runtime_fails_closed(monkeypatch):
    monkeypatch.setattr("patchloop.sandbox.shutil.which", lambda name: None)
    with pytest.raises(SandboxError, match="no unsafe fallback"):
        SandboxGuard("def allow(context):\n    return True\n")({})


def test_candidate_cannot_rewrite_runner():
    source = '''def allow(context):
    try:
        open("/worker.py", "w").write("forged")
    except OSError:
        return True
    return False
'''
    assert SandboxGuard(source)({}) is True


def test_top_level_code_rejected_before_execution():
    with pytest.raises(SandboxError, match="only def"):
        SandboxGuard("open('/tmp/unsafe', 'w');\ndef allow(context): return True\n")


@pytest.mark.parametrize("source", [
    '''def allow(context):
    global counter
    counter = globals().get("counter", 0) + 1
    return counter == 1
''',
    '''def allow(context):
    import builtins
    builtins.counter = getattr(builtins, "counter", 0) + 1
    return builtins.counter == 1
''',
])
def test_batch_contexts_have_fresh_namespace_and_module_state(source):
    guard = SandboxGuard(source)
    assert guard.decide_many([{}, {}, {}]) == [True, True, True]
    assert [guard({}) for _ in range(3)] == [True, True, True]


@pytest.mark.parametrize("path", ["/tmp/shared-state", "/shared-state", "/dev/shared-state",
                                  "/dev/shm/shared-state"])
def test_contexts_cannot_communicate_through_shared_files(path):
    source = f'''def allow(context):
    import os
    if os.path.exists({path!r}):
        return False
    try:
        with open({path!r}, "w") as file:
            file.write("state from another context")
    except OSError:
        return True
    return False
'''
    assert SandboxGuard(source).decide_many([{}, {}]) == [True, True]
