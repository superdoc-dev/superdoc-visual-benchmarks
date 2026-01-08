"""Vite dev server management for SuperDoc harness."""

import atexit
import os
import re
import select
import signal
import subprocess
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

from .version import ensure_node_modules, get_workspace_path

DEFAULT_PORT = 9106
SERVER_TIMEOUT_S = 60


def is_url_reachable(url: str, timeout_s: float = 2.0) -> bool:
    """Check if a URL is reachable.

    Args:
        url: URL to check.
        timeout_s: Timeout in seconds.

    Returns:
        True if reachable.
    """
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=timeout_s):
            return True
    except (URLError, OSError):
        return False


def _terminate_process(proc: subprocess.Popen) -> None:
    """Terminate a process and its children."""
    if proc.poll() is not None:
        return
    try:
        if hasattr(os, "killpg"):
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
        proc.wait(timeout=5)
    except (ProcessLookupError, OSError):
        pass


def start_vite_server(
    timeout_s: int = SERVER_TIMEOUT_S,
    verbose: bool = False,
) -> tuple[subprocess.Popen, str]:
    """Start the Vite dev server for the SuperDoc harness.

    Ensures node_modules are installed, then starts the dev server.

    Args:
        timeout_s: Timeout waiting for server to start.
        verbose: Print server output.

    Returns:
        Tuple of (process, url).

    Raises:
        RuntimeError: If server fails to start.
    """
    # Ensure workspace and node_modules exist
    ensure_node_modules()
    workspace = get_workspace_path()

    cmd = ["npm", "run", "dev"]
    proc = subprocess.Popen(
        cmd,
        cwd=str(workspace),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
    )
    atexit.register(_terminate_process, proc)

    url_matcher = re.compile(r"(http://(?:localhost|127\.0\.0\.1):\d+/?)")
    lines: list[str] = []
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        if proc.poll() is not None:
            break
        if proc.stdout is None:
            break
        ready, _, _ = select.select([proc.stdout], [], [], 0.25)
        if not ready:
            continue
        line = proc.stdout.readline()
        if not line:
            continue
        if verbose:
            print(line, end="")
        lines.append(line.rstrip())
        match = url_matcher.search(line)
        if match:
            url = match.group(1)
            # Ensure URL ends with /
            if not url.endswith("/"):
                url += "/"
            if is_url_reachable(url, timeout_s=2.0):
                return proc, url

    tail = "\n".join(lines[-12:])
    raise RuntimeError(
        f"Failed to start Vite dev server or detect its URL.\n"
        f"Last output:\n{tail}"
    )


def stop_server(proc: subprocess.Popen) -> None:
    """Stop a running server process.

    Args:
        proc: The server process to stop.
    """
    _terminate_process(proc)


class ViteServer:
    """Context manager for Vite dev server lifecycle."""

    def __init__(self, timeout_s: int = SERVER_TIMEOUT_S, verbose: bool = False):
        self.timeout_s = timeout_s
        self.verbose = verbose
        self._proc: subprocess.Popen | None = None
        self._url: str | None = None

    def __enter__(self) -> "ViteServer":
        self._proc, self._url = start_vite_server(
            timeout_s=self.timeout_s,
            verbose=self.verbose,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._proc:
            stop_server(self._proc)
            self._proc = None

    @property
    def url(self) -> str:
        """Get the server URL."""
        if self._url is None:
            raise RuntimeError("Server not started")
        return self._url

    @property
    def process(self) -> subprocess.Popen:
        """Get the server process."""
        if self._proc is None:
            raise RuntimeError("Server not started")
        return self._proc
