import sys
from io import StringIO
from unittest.mock import call, patch

from browser_harness import run


def test_c_flag_executes_code():
    stdout = StringIO()
    with patch.object(sys, "argv", ["browser-harness", "-c", "print('hello from -c')"]), \
         patch("browser_harness.run.ensure_daemon"), \
         patch("browser_harness.run.print_update_banner"), \
         patch("sys.stdout", stdout):
        run.main()
    assert stdout.getvalue().strip() == "hello from -c"


def test_cloud_bootstrap_on_headless_server(monkeypatch):
    """Auto-provisions cloud daemon when no daemon, no local Chrome, and API key is set."""
    monkeypatch.setenv("BROWSER_USE_API_KEY", "test-key")
    with patch.object(sys, "argv", ["browser-harness", "-c", "x = 1"]), \
         patch("browser_harness.run.daemon_alive", return_value=False), \
         patch("browser_harness.run._local_chrome_listening", return_value=False), \
         patch("browser_harness.run.start_remote_daemon") as mock_start, \
         patch("browser_harness.run.ensure_daemon"), \
         patch("browser_harness.run.print_update_banner"):
        run.main()
    mock_start.assert_called_once()


def test_no_cloud_bootstrap_when_chrome_listening(monkeypatch):
    """Does not provision cloud daemon when local Chrome is already running."""
    monkeypatch.setenv("BROWSER_USE_API_KEY", "test-key")
    with patch.object(sys, "argv", ["browser-harness", "-c", "x = 1"]), \
         patch("browser_harness.run.daemon_alive", return_value=False), \
         patch("browser_harness.run._local_chrome_listening", return_value=True), \
         patch("browser_harness.run.start_remote_daemon") as mock_start, \
         patch("browser_harness.run.ensure_daemon"), \
         patch("browser_harness.run.print_update_banner"):
        run.main()
    mock_start.assert_not_called()


def test_no_cloud_bootstrap_when_daemon_alive(monkeypatch):
    """Does not provision cloud daemon when a daemon is already running."""
    monkeypatch.setenv("BROWSER_USE_API_KEY", "test-key")
    with patch.object(sys, "argv", ["browser-harness", "-c", "x = 1"]), \
         patch("browser_harness.run.daemon_alive", return_value=True), \
         patch("browser_harness.run._local_chrome_listening", return_value=False), \
         patch("browser_harness.run.start_remote_daemon") as mock_start, \
         patch("browser_harness.run.ensure_daemon"), \
         patch("browser_harness.run.print_update_banner"):
        run.main()
    mock_start.assert_not_called()


def test_no_cloud_bootstrap_without_api_key(monkeypatch):
    """Does not provision cloud daemon when BROWSER_USE_API_KEY is not set."""
    monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
    with patch.object(sys, "argv", ["browser-harness", "-c", "x = 1"]), \
         patch("browser_harness.run.daemon_alive", return_value=False), \
         patch("browser_harness.run._local_chrome_listening", return_value=False), \
         patch("browser_harness.run.start_remote_daemon") as mock_start, \
         patch("browser_harness.run.ensure_daemon"), \
         patch("browser_harness.run.print_update_banner"):
        run.main()
    mock_start.assert_not_called()


def test_c_flag_does_not_read_stdin():
    stdin_read = []
    fake_stdin = StringIO("should not be read")
    fake_stdin.read = lambda: stdin_read.append(True) or ""

    with patch.object(sys, "argv", ["browser-harness", "-c", "x = 1"]), \
         patch("browser_harness.run.ensure_daemon"), \
         patch("browser_harness.run.print_update_banner"), \
         patch("sys.stdin", fake_stdin):
        run.main()

    assert not stdin_read, "stdin should not be read when -c is passed"
