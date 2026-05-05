from browser_harness import _ipc as ipc


# --- identify(): ping payload sanitation ---

class _FakeConn:
    def close(self): pass


def _patch_identify_response(monkeypatch, response):
    """Stub connect() and request() so identify() sees `response` as the JSON
    parsed from the daemon's reply, exactly as it would arrive over the wire."""
    monkeypatch.setattr(ipc, "connect", lambda name, timeout=1.0: (_FakeConn(), "tok"))
    monkeypatch.setattr(ipc, "request", lambda conn, tok, msg: response)


def test_identify_returns_pid_for_well_formed_ping_reply(monkeypatch):
    _patch_identify_response(monkeypatch, {"pong": True, "pid": 4242})

    assert ipc.identify("default", timeout=0.0) == 4242


def test_identify_rejects_boolean_pid(monkeypatch):
    """isinstance(True, int) is True in Python; a hostile or buggy daemon
    that replies {"pid": True} would otherwise yield PID 1 (init on POSIX),
    which os.kill(1, SIGTERM) would target. Reject it explicitly."""
    _patch_identify_response(monkeypatch, {"pong": True, "pid": True})

    assert ipc.identify("default", timeout=0.0) is None


def test_identify_rejects_boolean_false_pid(monkeypatch):
    """False is also an int subclass and would yield PID 0."""
    _patch_identify_response(monkeypatch, {"pong": True, "pid": False})

    assert ipc.identify("default", timeout=0.0) is None


def test_identify_returns_none_when_pid_field_missing(monkeypatch):
    """Pre-upgrade daemons reply {pong: True} only — no pid. identify must
    return None so callers know they have no verified PID to signal, while
    still letting alive-checks via ipc.ping() succeed."""
    _patch_identify_response(monkeypatch, {"pong": True})

    assert ipc.identify("default", timeout=0.0) is None


def test_identify_handles_non_dict_ping_payload(monkeypatch):
    """request() can deserialize any valid JSON value. A stale or hostile
    endpoint replying with a list / scalar / null would crash a naive
    resp.get() with AttributeError; identify must absorb that and return None."""
    for payload in ([1, 2, 3], "hello", 42, None):
        _patch_identify_response(monkeypatch, payload)
        assert ipc.identify("default", timeout=0.0) is None, (
            f"identify() should reject non-dict ping payload: {payload!r}"
        )


def test_identify_returns_none_when_pong_is_not_true(monkeypatch):
    _patch_identify_response(monkeypatch, {"pong": False, "pid": 4242})

    assert ipc.identify("default", timeout=0.0) is None
