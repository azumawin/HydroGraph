"""Run the real stack for each test: Django backend, Vite frontend, simulator, browser.

Every test gets a fresh backend on a temporary SQLite database, so tests never
see each other's readings and never touch backend/db.sqlite3. The frontend dev
server is started once per session and always streams from the same backend
port, which each test's backend reuses.
"""

import os
import socket
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from playwright.sync_api import Page, expect

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
SIMULATOR = ROOT / "imitacija"
START = datetime(2026, 11, 14, 8, 0, tzinfo=UTC)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def venv_python(project: Path) -> str:
    """The project's own interpreter, so stopping it stops the server itself."""
    out = subprocess.run(
        ["uv", "run", "--frozen", "python", "-c", "import sys; print(sys.executable)"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def wait_for(url: str, timeout_s: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=1.0).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise TimeoutError(f"{url} did not come up within {timeout_s}s")


def stop(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@dataclass
class Backend:
    port: int
    db: Path
    python: str
    process: subprocess.Popen[bytes] | None = None
    log: Path = field(init=False)

    def __post_init__(self) -> None:
        self.log = self.db.with_suffix(".log")

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def env(self) -> dict[str, str]:
        return {
            **os.environ,
            "DJANGO_DB_PATH": str(self.db),
            "DJANGO_SETTINGS_MODULE": "config.settings",
        }

    def start(self) -> None:
        if not self.db.exists():
            subprocess.run(
                [self.python, "manage.py", "migrate", "-v", "0"],
                cwd=BACKEND,
                env=self.env,
                check=True,
            )
        with self.log.open("ab") as log:
            self.process = subprocess.Popen(
                [self.python, "manage.py", "runserver", str(self.port), "--noreload"],
                cwd=BACKEND,
                env=self.env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        wait_for(f"{self.url}/api/health/")

    def stop(self) -> None:
        if self.process is not None:
            stop(self.process)
            self.process = None

    def post(
        self,
        channel: str,
        value: float | bool,
        unit: str,
        *,
        minutes: float = 0,
        scope: str = "crew",
    ) -> dict[str, Any]:
        """POST one reading the way the simulator does; return the 201 body."""
        measured_at = (START + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")
        response = httpx.post(
            f"{self.url}/api/readings/",
            json={"channel": channel, "value": value, "unit": unit, "measured_at": measured_at},
            headers={"X-Simulation-Scope": scope},
        )
        assert response.status_code == 201, response.text
        return response.json()

    def server_errors(self) -> list[str]:
        """Logged 4xx/5xx responses; runserver logs nothing for 2xx."""
        text = self.log.read_text(errors="replace")
        return [line for line in text.splitlines() if " /api/" in line and "HTTP" in line]


@dataclass
class Simulation:
    process: subprocess.Popen[bytes]
    output: Path

    def wait(self, timeout_s: float = 120) -> str:
        self.process.wait(timeout=timeout_s)
        return self.output.read_text(errors="replace")

    def counters(self) -> str:
        return self.output.read_text(errors="replace").strip().splitlines()[-1]


@pytest.fixture(scope="session")
def backend_port() -> int:
    return free_port()


@pytest.fixture(scope="session")
def backend_python() -> str:
    return venv_python(BACKEND)


@pytest.fixture(scope="session")
def simulator_python() -> str:
    return venv_python(SIMULATOR)


@pytest.fixture
def backend(tmp_path: Path, backend_port: int, backend_python: str) -> Iterator[Backend]:
    server = Backend(port=backend_port, db=tmp_path / "db.sqlite3", python=backend_python)
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def frontend(backend_port: int) -> Iterator[str]:
    vite = FRONTEND / "node_modules" / ".bin" / "vite"
    if not vite.exists():
        pytest.fail("frontend dependencies missing: run `make sync`")
    port = free_port()
    process = subprocess.Popen(
        [str(vite), "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=FRONTEND,
        env={**os.environ, "VITE_BACKEND_URL": f"http://127.0.0.1:{backend_port}"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    wait_for(url)
    yield url
    stop(process)


@pytest.fixture
def simulate(backend: Backend, simulator_python: str, tmp_path: Path):
    """Start the simulator on one of its configs against this test's backend."""
    started: list[subprocess.Popen[bytes]] = []

    def run(config: str, *, speed: float, duration: float) -> Simulation:
        source = (SIMULATOR / "config" / config).read_text()
        lines = [line for line in source.splitlines() if not line.startswith("base_url")]
        settings = tmp_path / config
        settings.write_text(f'base_url = "{backend.url}"\n' + "\n".join(lines) + "\n")
        output = tmp_path / f"{config}.out"
        with output.open("wb") as out:
            process = subprocess.Popen(
                [
                    simulator_python,
                    "-m",
                    "imitacija",
                    "--config",
                    str(settings),
                    "--speed",
                    str(speed),
                    "--duration",
                    str(duration),
                ],
                cwd=SIMULATOR,
                stdout=out,
                stderr=subprocess.STDOUT,
            )
        started.append(process)
        return Simulation(process, output)

    yield run
    for process in started:
        if process.poll() is None:
            stop(process)


@pytest.fixture
def dashboard(page: Page, frontend: str, backend: Backend) -> Page:
    """The dashboard, connected: the stream's dictionary has arrived."""
    page.goto(frontend)
    expect(page.locator(".vitals-dashboard-reading-status").first).not_to_have_text("Loading")
    return page


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict[str, Any]) -> dict[str, Any]:
    # E2E_CHROMIUM points at an already installed chromium, skipping a download.
    executable = os.environ.get("E2E_CHROMIUM")
    return {**browser_type_launch_args, **({"executable_path": executable} if executable else {})}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    return {
        **browser_context_args,
        "locale": "en-US",
        "timezone_id": "UTC",
        "viewport": {"width": 1440, "height": 900},
    }
