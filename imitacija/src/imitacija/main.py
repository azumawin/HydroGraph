"""CLI lifecycle, configuration and graceful termination of the push-only worker."""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
import tomllib
from contextlib import nullcontext
from pathlib import Path

import httpx
from pydantic import ValidationError

from .clock import RealClock
from .delivery import Delivery, HttpTransport
from .models import Settings
from .preview import PreviewState, PreviewTransport, serve
from .registry import dictionary
from .scheduler import Scheduler


def load_settings(
    path: Path | None,
    speed: float | None,
    duration: float | None,
    bp_demo_interval: float | None = None,
    glucose_demo_interval: float | None = None,
) -> Settings:
    """Load configuration only; generated observations are never written to this path."""
    raw = tomllib.loads(path.read_text()) if path is not None else {}
    if speed is not None:
        raw["speed"] = speed
    if duration is not None:
        raw["duration_s"] = duration
    if bp_demo_interval is not None:
        raw["bp_demo_interval_s"] = bp_demo_interval
    if glucose_demo_interval is not None:
        raw["glucose_demo_interval_s"] = glucose_demo_interval
    return Settings.model_validate(raw)


async def report(delivery: Delivery) -> None:
    """Periodic aggregate status excludes medical payloads and authentication details."""
    while True:
        await asyncio.sleep(30)
        print(delivery.counters.as_json(), file=sys.stderr)


async def follow_environment(
    client: httpx.AsyncClient, scheduler: Scheduler, settings: Settings
) -> None:
    """Apply the environment selected on the backend whenever it changes.

    The backend's catalog gives each environment's baseline dose rate, gravity and
    round-trip comm delay; the simulator delays results by the one-way half. A
    failed poll is reported once and retried, never fatal to the run.
    """
    catalog: dict[str, dict[str, object]] = {}
    applied: str | None = None
    is_failing = False
    while True:
        try:
            if not catalog:
                listed = await client.get(settings.environments_route)
                _ = listed.raise_for_status()
                catalog = listed.json()["environments"]
            current = await client.get(settings.environment_route)
            _ = current.raise_for_status()
            selected = str(current.json()["id"])
            if selected != applied and selected in catalog:
                chosen = catalog[selected]
                scheduler.set_environment(
                    gravity_g=float(str(chosen["gravity_g"])),
                    comm_delay_s=float(str(chosen["comm_delay_rt_s"])) / 2,
                    dose_rate_usv_h=float(str(chosen["baseline_dose_rate_usv_h"])),
                )
                applied = selected
                print(f"environment: {selected}", file=sys.stderr)
            is_failing = False
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            if not is_failing:
                print(f"environment poll failed, retrying: {error!r}", file=sys.stderr)
            is_failing = True
        await asyncio.sleep(settings.environment_poll_wall_s)


async def run(settings: Settings, preview_port: int | None = None) -> None:
    """Run normal delivery, or opt into a local JSON preview without backend requests."""
    context = serve(settings, preview_port) if preview_port is not None else nullcontext(None)
    with context as preview:
        if preview is not None:
            print(f"JSON preview: {preview.url} (refresh to update)", file=sys.stderr)
        await _run_worker(settings, preview)


async def _run_worker(settings: Settings, preview: PreviewState | None) -> None:
    """Share acquisition and delayed delivery semantics between normal and preview modes."""
    clock = RealClock(settings.speed)
    if preview is not None:
        preview.clock = clock
    headers = (
        {"Authorization": f"Bearer {token}"} if (token := os.getenv("IMITACIJA_TOKEN")) else {}
    )
    async with httpx.AsyncClient(
        base_url=settings.base_url,
        headers=headers,
        timeout=settings.timeout_wall_s,
        follow_redirects=False,
    ) as client:
        delivery = Delivery(
            settings, clock, PreviewTransport(preview) if preview else HttpTransport(client)
        )
        scheduler = Scheduler(settings, clock, delivery)
        print(
            f"simulation run={delivery.run_id} start={settings.start.isoformat()} "
            f"speed={settings.speed} channels={len(scheduler.enabled)}",
            file=sys.stderr,
        )
        if settings.bp_demo_interval_s is not None:
            print(
                "blood pressure demo: paired synthetic trends every "
                f"{settings.bp_demo_interval_s}s",
                file=sys.stderr,
            )
        if settings.glucose_demo_interval_s is not None:
            print(
                "blood sugar demo: synthetic CGM trend every "
                f"{settings.glucose_demo_interval_s}s",
                file=sys.stderr,
            )
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        installed: list[signal.Signals] = []
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
                installed.append(sig)
            except NotImplementedError:
                pass
        sender = asyncio.create_task(delivery.run())
        sampler = asyncio.create_task(scheduler.run(settings.duration_s))
        reporter = asyncio.create_task(report(delivery))
        stopper = asyncio.create_task(stop.wait())
        follower = (
            asyncio.create_task(follow_environment(client, scheduler, settings))
            if settings.follow_backend_environment and preview is None
            else None
        )
        try:
            done, _ = await asyncio.wait(
                (sampler, sender, stopper), return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                task.result()
        finally:
            background = [sampler, reporter, stopper, *([follower] if follower else [])]
            for task in background:
                task.cancel()
            await asyncio.gather(*background, return_exceptions=True)
            await delivery.finish(sender)
            for sig in installed:
                loop.remove_signal_handler(sig)
            print(delivery.counters.as_json(), file=sys.stderr)


def main() -> None:
    """Run telemetry generation or explicitly export its static metadata dictionary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, help="TOML configuration (default: built-in healthy profile)"
    )
    parser.add_argument("--speed", type=float, help="simulation seconds per wall second")
    parser.add_argument("--duration", type=float, help="finite duration in simulation seconds")
    parser.add_argument(
        "--bp-demo-interval",
        type=float,
        help="enable synthetic paired pressure trends at this simulation-second interval",
    )
    parser.add_argument(
        "--glucose-demo-interval",
        type=float,
        help="enable a synthetic CGM trend at this simulation-second interval, instead of "
        "the 5-minute sensor window whose first result lands at 343s",
    )
    parser.add_argument(
        "--dictionary", action="store_true", help="print static metadata JSON and exit"
    )
    parser.add_argument(
        "--validate-config", action="store_true", help="validate configuration and exit"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="show latest JSON at localhost:8080 without backend POSTs",
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="localhost preview port (default 8080)"
    )
    args = parser.parse_args()
    try:
        if not 1 <= args.port <= 65535:
            raise ValueError("preview port must be between 1 and 65535")
        settings = load_settings(
            args.config,
            args.speed,
            args.duration,
            args.bp_demo_interval,
            args.glucose_demo_interval,
        )
        # Validate registry-dependent names even when only exporting configuration.
        Scheduler(settings, RealClock(settings.speed), _DiscardSink())
        if args.dictionary:
            print(
                dictionary(settings.environment, settings.lab_delay_s, settings).model_dump_json(
                    indent=2
                )
            )
        elif args.validate_config:
            print("Configuration and channel registry are valid.")
        else:
            asyncio.run(run(settings, args.port if args.preview else None))
    except (ValidationError, ValueError, OSError) as exc:
        # Do not echo configuration text, secrets, payloads or URLs on validation errors.
        print(
            f"Configuration/startup error ({type(exc).__name__}); check fields and paths.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        pass


class _DiscardSink:
    """Validation-only sink; Scheduler construction does not acquire measurements."""

    def submit(self, observation: object) -> None:
        """Unused during configuration validation."""
        raise RuntimeError("validation must not acquire data")
