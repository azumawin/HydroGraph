"""Run one isolated demo session, with readiness checks and shared shutdown."""

import argparse
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_free_port(port: int) -> None:
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(
                f"Port {port} is already in use. Stop the existing service before make dev."
            ) from error


def check_services(services: dict[str, subprocess.Popen]) -> None:
    for name, process in services.items():
        code = process.poll()
        if code is not None:
            raise RuntimeError(f"{name} exited unexpectedly (status {code}).")


def wait_for(
    url: str, services: dict[str, subprocess.Popen], timeout: float = 30
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        check_services(services)
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for {url}.")


def stop_services(services: dict[str, subprocess.Popen]) -> None:
    # Each service has its own process group, including uv and its descendants.
    for process in reversed(list(services.values())):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 8
    for process in services.values():
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for process in services.values():
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/healthy.toml")
    parser.add_argument("--speed", type=float)
    parser.add_argument("--bp-demo-interval", type=float)
    parser.add_argument("--glucose-demo-interval", type=float)
    parser.add_argument("--lab-demo-interval", type=float)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    services: dict[str, subprocess.Popen] = {}

    def interrupted(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        require_free_port(8000)
        require_free_port(5173)
        # Every simulator run begins at its configured epoch. Sharing a persistent
        # database mixes runs and lets older runs' future samples mask new ones.
        # Keep the standalone backend's database completely untouched.
        with tempfile.TemporaryDirectory(prefix="hydrograph-dev-") as directory:
            env = {**os.environ, "DJANGO_DB_PATH": str(Path(directory) / "db.sqlite3")}
            env["VITE_BACKEND_URL"] = "http://127.0.0.1:8000"

            def start(name: str, command: list[str], folder: str) -> subprocess.Popen:
                process = subprocess.Popen(
                    command, cwd=ROOT / folder, env=env, start_new_session=True
                )
                services[name] = process
                return process

            try:
                print(
                    f"Fresh demo session: {args.config}; speed={args.speed or 'from config'}.\n"
                    "Previous recordings are kept in the standalone backend database.\n"
                    + (
                        f"Glucose demo: samples every {args.glucose_demo_interval} "
                        "simulated seconds.\n"
                        if args.glucose_demo_interval is not None
                        else "Glucose: every 5 simulated minutes (first at 343s).\n"
                    )
                    + (
                        f"BP demo: paired samples every {args.bp_demo_interval} "
                        "simulated seconds.\n"
                        if args.bp_demo_interval is not None
                        else "BP uses the configured scenario/protocol schedule.\n"
                    )
                    + (
                        f"Assay/specimen demo: samples every {args.lab_demo_interval} "
                        "simulated seconds along each channel's own calendar."
                        if args.lab_demo_interval is not None
                        else "Assays and specimens use their own calendars."
                    ),
                    flush=True,
                )
                migrate = start(
                    "migrations",
                    ["uv", "run", "python", "manage.py", "migrate"],
                    "backend",
                )
                if migrate.wait() != 0:
                    raise RuntimeError("Database migrations failed.")
                del services["migrations"]
                start(
                    "backend",
                    ["uv", "run", "python", "manage.py", "runserver", "--noreload"],
                    "backend",
                )
                start(
                    "frontend",
                    [
                        "./node_modules/.bin/vite",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "5173",
                        "--strictPort",
                    ],
                    "frontend",
                )
                wait_for("http://127.0.0.1:8000/api/health/", services)
                wait_for("http://127.0.0.1:5173/", services)
                command = ["uv", "run", "imitacija", "--config", args.config]
                if args.speed is not None:
                    command.extend(["--speed", str(args.speed)])
                if args.bp_demo_interval is not None:
                    command.extend(["--bp-demo-interval", str(args.bp_demo_interval)])
                if args.glucose_demo_interval is not None:
                    command.extend(
                        ["--glucose-demo-interval", str(args.glucose_demo_interval)]
                    )
                if args.lab_demo_interval is not None:
                    command.extend(["--lab-demo-interval", str(args.lab_demo_interval)])
                simulator = start("simulator", command, "imitacija")
                if not args.no_open:
                    start(
                        "browser",
                        [sys.executable, "-m", "webbrowser", "http://127.0.0.1:5173"],
                        ".",
                    )
                while simulator.poll() is None:
                    check_services(
                        {name: services[name] for name in ("backend", "frontend")}
                    )
                    time.sleep(0.1)
                return simulator.returncode or 0
            finally:
                stop_services(services)
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError) as error:
        print(f"make dev: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
