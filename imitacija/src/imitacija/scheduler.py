"""Independent acquisition groups, calendar protocols and immutable result creation."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Literal, Protocol

from .clock import Clock, timestamp
from .frequency import FREQUENCIES, LAB_DEMO_CALENDAR, Calendar, lab_demo_interval
from .models import CGM_WINDOW_S, AstronautProfile, Observation, Reading, Settings
from .physiology import (
    DAY,
    blood_pressure_demo_scale,
    crew_values,
    environment_values,
    glucose_demo_scale,
    monitor_dose_msv,
    startup_crew_values,
)
from .registry import CHANNELS, Channel, effective_channels
from .scenarios import (
    EVA_CHANNELS,
    INFECTION_CHANNELS,
    SANS_CHANNELS,
    eva_balance,
    eva_sweat_values,
    eva_usg,
    hypercapnia_eeg_values,
    hypercapnia_references,
    infection_context_values,
    infection_references,
    sans_values,
)
from .units import convert


class Sink(Protocol):
    """Nonblocking enqueue interface; sampling never awaits a network request."""

    def submit(self, observation: Observation) -> None:
        """Accept a result into bounded transient delivery state."""
        ...


@dataclass(frozen=True)
class Rule:
    """Periodic or sparse protocol rule; paired channels share one acquisition rule."""

    group: str
    phase: float = 0
    interval: float | None = None
    # Set only by the dashboard demo: the sample index maps onto the group's
    # own protocol calendar instead of standing for the acquisition instant.
    calendar: Calendar | None = None
    points: tuple[float, ...] = ()
    repeat: float | None = None
    end: float | None = None
    active_only: bool = False
    burst_start: float | None = None

    def next_after(self, t: float) -> float | None:
        """Find a strictly later event in O(number of protocol points), without history."""
        if self.interval is not None:
            # Anchor to the group's phase instead of accumulating CPU/transport drift.
            step = max(0, math.floor((t - self.phase + 1e-8) / self.interval) + 1)
            result = self.phase + step * self.interval
            if self.burst_start is not None:
                burst_end = self.burst_start + 180
                burst_step = max(0, math.floor((t - self.burst_start + 1e-8) / 0.1) + 1)
                burst = self.burst_start + burst_step * 0.1
                if burst < burst_end - 1e-8:
                    result = min(result, burst)
            if self.active_only:
                # The healthy routine's Gaussian activity is >.05 only during this
                # daily interval. Skip resting time entirely; no 1Hz dry-patch polling.
                span = math.sqrt(-math.log(0.05))
                day = math.floor(result / DAY)
                lower = day * DAY + (17.5 - 0.4 * span) * 3600 + 1
                upper = day * DAY + (17.5 + 0.65 * span) * 3600
                if result < lower:
                    result = math.ceil(lower / self.interval) * self.interval
                elif result >= upper:
                    result = math.ceil((lower + DAY) / self.interval) * self.interval
            return result if self.end is None or result < self.end else None
        candidates: list[float] = []
        for point in self.points:
            candidate = point
            if self.repeat is not None and candidate <= t:
                candidate += (math.floor((t - point) / self.repeat) + 1) * self.repeat
            if candidate > t:
                candidates.append(candidate)
        return min(candidates) if candidates else None


def glucose_window(settings: Settings) -> float:
    """The CGM window in effect: the dashboard demo's, or the specified 5 minutes.

    A result still averages the raw 5-second samples inside its own window, so a
    shorter demo window means fewer of them, never a partial 5-minute mean.
    """
    demo = settings.glucose_demo_interval_s
    return CGM_WINDOW_S if demo is None else demo


def rules(settings: Settings) -> tuple[Rule, ...]:
    """Use NASA-informed demo schedules, not the superseded biochemical polling loop."""
    tests = tuple(
        sorted(
            {
                0.0,
                *(day * DAY + 17 * 3600 for day in settings.exercise_test_days),
                *(
                    day * DAY + 18 * 3600 + minute * 60
                    for day in settings.exercise_test_days
                    for minute in (5, 15, 30)
                ),
            }
        )
    )

    def periodic(group: str, phase: float = 0, *, active: bool = False) -> Rule:
        """Use the same matrix policy that supplies public dictionary metadata."""
        return Rule(group, phase=phase, interval=FREQUENCIES[group].interval_s, active_only=active)

    bp_end = (
        None
        if settings.bp_session_duration_s is None
        else settings.bp_session_start_s + settings.bp_session_duration_s
    )
    # The CGM's own 5-minute window puts its first completed result at 343 s, so
    # a short demo shows one startup point and nothing else. The demo override
    # samples a correspondingly shorter window instead; see glucose_window().
    glucose_demo = settings.glucose_demo_interval_s
    glucose_rule = (
        periodic("glucose", 343)
        if glucose_demo is None
        else Rule("glucose", phase=glucose_demo, interval=glucose_demo)
    )
    scenario_rules = (
        ()
        if settings.sans_scenario is None
        else (
            Rule("cephalic", phase=60, interval=60),
            Rule("eye_screen", points=settings.sans_scenario.eye_screen_times_s),
        )
    )
    return (
        *scenario_rules,
        *((Rule("eeg_cfe", phase=60, interval=60),) if settings.hypercapnia_scenario else ()),
        periodic("heart", FREQUENCIES["heart"].window_s),
        periodic("hrv", 61),
        periodic("respiration", 77),
        periodic("spo2", 0.2),
        periodic("temperature", 0.4),
        glucose_rule,
        periodic("sweat", active=True),
        periodic("sweat_summary", active=True),
        Rule(
            "bp",
            phase=settings.bp_session_start_s,
            interval=3600,
            end=bp_end,
            burst_start=settings.stand_test_start_s,
        ),
        Rule("troponin", points=settings.troponin_event_times_s),
        Rule("lactate", points=tests),
        Rule("vitamin", points=(0,), repeat=30 * DAY),
        Rule("cortisol", points=tuple(h * 3600 for h in (7, 11, 15, 19, 23)), repeat=DAY),
        Rule("il6", points=settings.il6_event_times_s),
        Rule("ntx", points=(7 * DAY,), repeat=7 * DAY),
        Rule("urine", points=(DAY,), repeat=DAY),
        Rule("mass", points=(7 * 3600, 18.5 * 3600), repeat=DAY),
        Rule("usg", points=(7 * 3600, 18.5 * 3600), repeat=DAY),
        Rule("saliva_pcr", points=(9 * 3600,), repeat=2 * DAY),
        Rule("urine_pcr", points=(10 * 3600,), repeat=2 * DAY),
        periodic("co2"),
        periodic("light", 0.6),
        Rule("radiation", interval=settings.radiation_interval_s),
        periodic("radiation_dose", 60),
        Rule("spe", phase=0.8, interval=settings.spe_heartbeat_s),
    )


@dataclass(order=True)
class Event:
    """Sequence breaks heap ties without comparing owner/model objects."""

    due: float
    order: int
    rule: Rule = field(compare=False)
    scope: Literal["crew", "environment"] = field(compare=False)
    owner: str = field(compare=False)


class Scheduler:
    """A single small heap owns collection clocks; HTTP cannot block acquisition."""

    def __init__(self, settings: Settings, clock: Clock, sink: Sink) -> None:
        self.settings, self.clock, self.sink = settings, clock, sink
        self.profiles = {p.id: p for p in settings.crew}
        self.enabled = effective_channels(settings)
        self.events: list[Event] = []
        self.counter = 0
        self.sequences: dict[tuple[str, str], int] = {}
        self.generated = 0
        self.started = False
        for rule in (
            *rules(settings),
            *(
                (
                    Rule("infection_context", phase=60, interval=60),
                    Rule("infection_gfet", phase=60, interval=60),
                )
                if settings.acute_infection_scenario
                else ()
            ),
            *((Rule("eva_sweat", interval=1),) if settings.eva_dehydration_scenario else ()),
        ):
            members = [
                c for c in CHANNELS.values() if c.group == rule.group and c.id in self.enabled
            ]
            if not members:
                continue
            scope = members[0].scope
            owners = tuple(self.profiles) if scope == "crew" else (settings.environment.id,)
            for owner in owners:
                if (
                    rule.group in {"cephalic", "eye_screen"}
                    and settings.sans_scenario is not None
                    and owner != settings.sans_scenario.owner_id
                ):
                    continue
                owner_rule = rule
                eva = settings.eva_dehydration_scenario
                if rule.group == "eva_sweat" and (eva is None or owner != eva.owner_id):
                    continue
                if eva and owner == eva.owner_id:
                    if rule.group in {"sweat", "sweat_summary", "eva_sweat"}:
                        step = 60 if rule.group == "sweat_summary" else 1
                        owner_rule = Rule(
                            rule.group,
                            phase=eva.onset_s + step,
                            interval=step,
                            end=eva.onset_s + eva.eva_duration_s + 1,
                        )
                    elif rule.group in {"mass", "bp"}:
                        owner_rule = Rule(rule.group, phase=60, interval=60)
                    elif rule.group == "usg":
                        owner_rule = Rule("usg", points=eva.usg_event_times_s)
                infection = settings.acute_infection_scenario
                if rule.group in {"infection_context", "infection_gfet"} and (
                    not infection or owner != infection.owner_id
                ):
                    continue
                if infection and owner == infection.owner_id:
                    if rule.group == "bp":
                        owner_rule = Rule("bp", phase=60, interval=60)
                    elif rule.group == "il6":
                        owner_rule = Rule("il6", points=infection.serum_il6_event_times_s)
                    elif rule.group == "saliva_pcr":
                        owner_rule = Rule("saliva_pcr", points=infection.saliva_pcr_event_times_s)
                if rule.group == "bp" and settings.bp_demo_interval_s is not None:
                    # One paired stream replaces the cuff/scenario/stand-test
                    # schedule only when the dashboard demo is explicitly enabled.
                    owner_rule = Rule("bp", interval=settings.bp_demo_interval_s)
                calendar = LAB_DEMO_CALENDAR.get(rule.group)
                if (
                    settings.lab_demo_interval_s is not None
                    and calendar is not None
                    and owner_rule is rule
                ):
                    # Only the untouched protocol calendar is compressed: a
                    # scenario target keeps the schedule its fault gave it.
                    owner_rule = Rule(
                        rule.group,
                        interval=lab_demo_interval(settings.lab_demo_interval_s, settings.speed),
                        calendar=calendar,
                    )
                due = owner_rule.next_after(0)
                if due is not None:
                    self._push(due, owner_rule, scope, owner)

    def set_environment(
        self, *, gravity_g: float, comm_delay_s: float, dose_rate_usv_h: float
    ) -> None:
        """Switch the shared compartment mid-run; later samples use the new values.

        The integrated monitor dose is analytic from t = 0, so a dose-rate change
        carries an offset that keeps it continuous at the switch instant.
        """
        now = self.clock.now()
        old = self.settings.environment
        switched = old.model_copy(
            update={
                "gravity_g": gravity_g,
                "comm_delay_s": comm_delay_s,
                "dose_rate_usv_h": dose_rate_usv_h,
                "dose_offset_msv": 0.0,
            }
        )
        offset = monitor_dose_msv(old, now) - monitor_dose_msv(switched, now)
        switched = switched.model_copy(update={"dose_offset_msv": offset})
        self.settings = self.settings.model_copy(update={"environment": switched})

    def _push(
        self, due: float, rule: Rule, scope: Literal["crew", "environment"], owner: str
    ) -> None:
        """One next event per owner/group bounds schedule memory independently of run length."""
        self.counter += 1
        heapq.heappush(self.events, Event(due, self.counter, rule, scope, owner))

    def _sampled(self, rule: Rule, instant: float) -> float:
        """Protocol time this acquisition stands for, normally the instant itself.

        Under the dashboard demo a sparse group's samples walk its own calendar
        instead (see Calendar), one step per interval. Derived from the instant,
        never from a counter, so a late or coalesced poll cannot shift the walk.
        """
        if rule.calendar is None or rule.interval is None:
            return instant
        return rule.calendar.instant(max(0, round(instant / rule.interval) - 1))

    def acquire(self, event: Event, instant: float) -> None:
        """Create result values at actual acquisition time; late polls coalesce, never replay."""
        profile: AstronautProfile | None = (
            self.profiles.get(event.owner) if event.scope == "crew" else None
        )
        values: dict[str, float | bool | str]
        scenario = self.settings.sans_scenario
        sampled = self._sampled(event.rule, instant)
        if event.rule.group == "eeg_cfe" and self.settings.hypercapnia_scenario is not None:
            values = dict(hypercapnia_eeg_values(sampled, self.settings.hypercapnia_scenario))
        elif event.rule.group in {"cephalic", "eye_screen"} and scenario is not None:
            values = sans_values(event.rule.group, sampled, scenario)
        else:
            values = (
                crew_values(
                    event.rule.group,
                    sampled,
                    profile,
                    self.settings.seed,
                    self.settings.sans_scenario,
                    dehydration=self.settings.eva_dehydration_scenario,
                    infection=self.settings.acute_infection_scenario,
                    hypercapnia=self.settings.hypercapnia_scenario,
                    glucose_window_s=glucose_window(self.settings),
                )
                if profile is not None
                else environment_values(
                    event.rule.group,
                    sampled,
                    self.settings.environment,
                    self.settings.seed,
                    hypercapnia=self.settings.hypercapnia_scenario,
                )
            )
        for name, value in values.items():
            if name not in self.enabled:
                continue
            c = CHANNELS[name]
            # Rate and integrated dose share a latent radiation model but have
            # independent publication clocks. Never emit the sibling on this tick.
            if c.group != event.rule.group:
                continue
            self._publish(
                c, value, event.owner, event.scope, instant, demo=event.rule.calendar is not None
            )

    def _publish(
        self,
        channel: Channel,
        value: float | bool | str,
        owner: str,
        scope: Literal["crew", "environment"],
        instant: float,
        *,
        startup: bool = False,
        demo: bool = False,
    ) -> None:
        """Convert once and enqueue immutable data with explicit sampling provenance."""
        key = (owner, channel.id)
        sequence = self.sequences.get(key, 0) + 1
        self.sequences[key] = sequence
        if channel.group == "bp" and self.settings.bp_demo_interval_s is not None:
            assert isinstance(value, (float, int)) and not isinstance(value, bool)
            value *= blood_pressure_demo_scale(instant, self.settings.seed, owner)
        if channel.group == "glucose" and self.settings.glucose_demo_interval_s is not None:
            assert isinstance(value, (float, int)) and not isinstance(value, bool)
            value *= glucose_demo_scale(instant, self.settings.seed, owner)
        wire_value = (
            value
            if isinstance(value, (bool, str))
            else convert(value, channel.factor, channel.offset)
        )
        reading = Reading(
            channel=channel.id,
            value=wire_value,
            unit=channel.unit,
            measured_at=timestamp(self.settings.start, instant),
        )
        # Startup fixtures are already available profile values, not a newly drawn
        # laboratory specimen. Communication delay still applies to their delivery.
        # A demo-paced assay is held no longer either: the synthetic laboratory
        # hour would outlast the dashboard run that asked for the trend.
        lab_delay = self.settings.lab_delay_s if channel.lab and not (startup or demo) else 0
        self.sink.submit(
            Observation(
                reading=reading,
                scope=scope,
                owner=owner,
                sensor_id=f"{owner}:{channel.group}",
                sequence=sequence,
                acquired_s=instant,
                available_s=instant + lab_delay + self.settings.environment.comm_delay_s,
                # The demo's CGM result averages its own shorter window, so it
                # must not claim the 5 minutes the registry records.
                window_s=0
                if startup
                else glucose_window(self.settings)
                if channel.group == "glucose"
                else channel.window_s,
                sample_kind="startup_baseline" if startup else "scheduled",
            )
        )
        self.generated += 1

    def initialize(self) -> None:
        """Emit exactly one baseline per enabled owner/channel, once per worker run.

        Normal rules are anchored to their original phases and skip time zero,
        so channels that already had a baseline event do not emit a duplicate.
        Resuming this same scheduler never repeats initialization.
        """
        if self.started:
            return
        self.started = True
        for profile in self.settings.crew:
            values = startup_crew_values(profile, self.settings.seed)
            if self.settings.hypercapnia_scenario:
                values.update(
                    hypercapnia_references(0, profile, self.settings.hypercapnia_scenario)
                )
            infection = self.settings.acute_infection_scenario
            if infection and profile.id == infection.owner_id:
                values.update(infection_references(0, profile, infection))
                values["il6_serum"] = infection.baseline_il6_pg_ml
                values.update(infection_context_values(0, infection))
            eva = self.settings.eva_dehydration_scenario
            if eva and profile.id == eva.owner_id:
                values.update(eva_sweat_values(0, eva, startup=True))
                values["body_mass"] = eva_balance(0, profile, eva)["mass_kg"]
                values["urine_specific_gravity"] = eva_usg(0, profile, eva)
            scenario = self.settings.sans_scenario
            if scenario and profile.id == scenario.owner_id:
                values.update(sans_values("cephalic", 0, scenario, startup=True))
                values.update(sans_values("eye_screen", 0, scenario, startup=True))
            for channel in CHANNELS.values():
                if channel.id in SANS_CHANNELS and (
                    not scenario or profile.id != scenario.owner_id
                ):
                    continue
                if channel.id in INFECTION_CHANNELS and (
                    not infection or profile.id != infection.owner_id
                ):
                    continue
                if channel.id in EVA_CHANNELS and (not eva or profile.id != eva.owner_id):
                    continue
                if channel.scope == "crew" and channel.id in self.enabled:
                    self._publish(channel, values[channel.id], profile.id, "crew", 0, startup=True)
        environment = self.settings.environment
        values = {}
        for group in ("co2", "light", "radiation", "spe"):
            values.update(
                environment_values(
                    group,
                    0,
                    environment,
                    self.settings.seed,
                    hypercapnia=self.settings.hypercapnia_scenario,
                )
            )
        for channel in CHANNELS.values():
            if channel.scope == "environment" and channel.id in self.enabled:
                self._publish(
                    channel, values[channel.id], environment.id, "environment", 0, startup=True
                )

    async def run(self, until: float | None = None) -> None:
        """Acquire until a finite logical duration or cancellation (continuous default)."""
        self.initialize()
        while self.events:
            event = self.events[0]
            if until is not None and event.due > until:
                await self.clock.sleep_until(until)
                return
            heapq.heappop(self.events)
            await self.clock.sleep_until(event.due)
            actual = self.clock.now()
            if until is not None and actual > until:
                return
            # A missed finite cuff session must not produce a cuff reading after its end.
            if event.rule.end is None or actual < event.rule.end:
                self.acquire(event, actual)
            if (next_due := event.rule.next_after(actual)) is not None:
                self._push(next_due, event.rule, event.scope, event.owner)
        if until is not None:
            await self.clock.sleep_until(until)
