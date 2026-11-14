"""Validated immutable contracts, configuration, and transport-only observation context."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FrozenModel(BaseModel):
    """Reject unknown configuration fields and accidental mutation of sampled values."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class Reading(FrozenModel):
    """The exact four-field body; acquisition time survives delays and retries."""

    channel: str
    value: float | bool
    unit: str = Field(min_length=1)
    measured_at: datetime

    @field_validator("measured_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        """Require an aware instant and normalize its representation to UTC."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("measured_at must include a timezone")
        return value.astimezone(UTC)


class AstronautProfile(FrozenModel):
    """Synthetic adult baseline, not an imported medical history."""

    id: str = Field(default="crew-1", pattern=r"^[A-Za-z0-9_-]+$")
    sex: Literal["male", "female"] = "male"
    postmenopausal: bool = False
    mass_kg: float = Field(default=75, ge=45, le=120)
    resting_hr_bpm: float = Field(default=66, ge=50, le=85)
    rmssd_ms: float = Field(default=40, ge=20, le=80)
    sbp_mmhg: float = Field(default=114, ge=100, lt=120)
    dbp_mmhg: float = Field(default=73, ge=60, lt=80)
    ntx_baseline: float = Field(default=45, ge=26, le=80)
    vitamin_d_ng_ml: float = Field(default=40, ge=35, le=45)
    # Local patch references are synthetic fixture values, not serum thresholds.
    # Compare like activity/collection conditions when interpreting their changes.
    sweat_reference_rate_l_h: float = Field(default=0.42 / 1800, gt=0, le=0.001)
    sweat_reference_sodium_mmol_l: float = Field(default=44, ge=10, le=100)

    @model_validator(mode="after")
    def coherent(self) -> AstronautProfile:
        """Sex-dependent assay metadata must describe the chosen fixture."""
        if self.postmenopausal and self.sex != "female":
            raise ValueError("postmenopausal applies to female assay profiles")
        return self


class Environment(FrozenModel):
    """Shared compartment configuration; dose is a monitor quantity, never career dose."""

    id: str = Field(default="iss_cabin", pattern=r"^[A-Za-z0-9_-]+$")
    gravity_g: float = Field(default=0, ge=0, le=2)
    comm_delay_s: float = Field(default=0, ge=0, le=3600)
    pressure_pa: float = Field(default=101325, gt=0)
    dose_rate_usv_h: float = Field(default=18, ge=0, le=35)
    initial_monitor_dose_msv: float = Field(default=0, ge=0)


class SansScenario(FrozenModel):
    """Explicit synthetic SANS fixture; durations are demonstration assumptions."""

    id: Literal["FAULT_01_SANS_CEPHALIC"] = "FAULT_01_SANS_CEPHALIC"
    owner_id: str = "crew-1"
    onset_s: float = Field(default=600, ge=0)
    warning_at_s: float = Field(default=1800, gt=0)
    escalate_to_critical: bool = True
    critical_start_s: float = Field(default=2400, ge=0)
    critical_at_s: float = Field(default=3600, gt=0)
    baseline_strain_pct: float = Field(default=0.65, ge=0, lt=1.1)
    warning_strain_pct: float = Field(default=1.55, ge=1.1, le=1.8)
    critical_strain_pct: float = Field(default=2.05, gt=1.8)
    gauge_factor: float = Field(default=15.5, gt=0)
    affected_rmssd_ms: float = Field(default=36, gt=0)
    baseline_icp_indicator_mmhg: float = Field(default=10, ge=0)
    warning_icp_indicator_mmhg: float = Field(default=16.2, ge=0)
    critical_icp_indicator_mmhg: float = Field(default=19, ge=0)
    affected_logmar: float = Field(default=0.2, ge=0)
    eye_screen_times_s: tuple[float, ...] = (1860, 3660)

    @model_validator(mode="after")
    def coherent(self) -> SansScenario:
        if not self.onset_s < self.warning_at_s:
            raise ValueError("warning ramp must have positive duration")
        if not self.warning_at_s <= self.critical_start_s < self.critical_at_s:
            raise ValueError("critical ramp must follow warning with positive duration")
        if any(not math.isfinite(t) or t <= 0 for t in self.eye_screen_times_s):
            raise ValueError("screen times must be finite and positive")
        if tuple(sorted(set(self.eye_screen_times_s))) != self.eye_screen_times_s:
            raise ValueError("screen times must be unique and sorted")
        if not (
            self.baseline_icp_indicator_mmhg
            <= self.warning_icp_indicator_mmhg
            <= self.critical_icp_indicator_mmhg
        ):
            raise ValueError("indicator targets must be nondecreasing")
        return self


class HypercapniaScenario(FrozenModel):
    """Shared-cabin synthetic fault; delays are demonstration assumptions."""

    id: Literal["FAULT_02_HYPERCAPNIA_CO2"] = "FAULT_02_HYPERCAPNIA_CO2"
    environment_id: str = "iss_cabin"
    onset_s: float = Field(default=120, ge=0)
    ramp_duration_s: float = Field(default=90, gt=0)
    compensation_delay_s: float = Field(default=10, ge=0)
    oxygenation_delay_s: float = Field(default=30, ge=0)
    baseline_ppco2_mmhg: float = Field(default=2.2, gt=0, le=3)
    affected_ppco2_mmhg: float = Field(default=4.8, ge=3.5, le=6)
    baseline_respiratory_rate_br_min: float = Field(default=14, gt=0)
    affected_respiratory_rate_br_min: float = Field(default=24, ge=22, le=26)
    affected_heart_rate_bpm: float = Field(default=104, ge=96, le=112)
    baseline_spo2_pct: float = Field(default=97, ge=94, le=100)
    affected_spo2_pct: float = Field(default=92, ge=91, le=93)
    baseline_cfe_ratio: float = Field(default=0.58, gt=0)
    affected_cfe_ratio: float = Field(default=1.28, gt=1.2)

    @model_validator(mode="after")
    def coherent(self) -> HypercapniaScenario:
        if self.compensation_delay_s >= self.oxygenation_delay_s:
            raise ValueError("compensation must precede oxygenation response")
        if self.baseline_respiratory_rate_br_min >= self.affected_respiratory_rate_br_min:
            raise ValueError("respiration must rise")
        if self.baseline_cfe_ratio >= self.affected_cfe_ratio:
            raise ValueError("CFE must rise")
        return self


class EvaDehydrationScenario(FrozenModel):
    """Constant-rate EVA balance and explicitly synthetic clinical responses."""

    id: Literal["FAULT_03_EVA_DEHYDRATION"] = "FAULT_03_EVA_DEHYDRATION"
    owner_id: str = "crew-1"
    onset_s: int = Field(default=600, ge=0)
    eva_duration_s: int = Field(default=9000, gt=0)
    baseline_whole_body_sweat_l_h: float = Field(default=0.045, gt=0)
    active_whole_body_sweat_l_h: float = Field(default=0.820, ge=0.650, le=0.950)
    drink_rate_l_h: float = Field(default=0.100, ge=0)
    whole_body_to_patch_multiplier: float = Field(default=1800, gt=0)
    baseline_sweat_sodium_mmol_l: float = Field(default=38, gt=0)
    active_sweat_sodium_mmol_l: float = Field(default=74, ge=68, le=85)
    response_loss_pct: float = Field(default=2.4, ge=2.1, le=3.2)
    baseline_usg: float = Field(default=1.012, ge=1, le=1.020)
    affected_usg: float = Field(default=1.026, ge=1.024, le=1.030)
    affected_heart_rate_bpm: float = Field(default=122, ge=115, le=132)
    affected_sbp_mmhg: float = Field(default=98, ge=96, le=102)
    affected_dbp_mmhg: float = Field(default=74, gt=0)
    usg_event_times_s: tuple[float, ...] = (600, 3600, 6000, 7800, 9600, 10200)

    @model_validator(mode="after")
    def coherent(self) -> EvaDehydrationScenario:
        if self.eva_duration_s % 60:
            raise ValueError("EVA duration must be a whole number of minutes")
        if self.drink_rate_l_h >= self.active_whole_body_sweat_l_h:
            raise ValueError("intake must be below active sweat loss")
        if self.baseline_whole_body_sweat_l_h >= self.active_whole_body_sweat_l_h:
            raise ValueError("sweat flow must rise")
        if self.baseline_sweat_sodium_mmol_l >= self.active_sweat_sodium_mmol_l:
            raise ValueError("sweat sodium must rise")
        if self.affected_dbp_mmhg >= self.affected_sbp_mmhg:
            raise ValueError("systolic pressure must exceed diastolic")
        if any(not math.isfinite(t) or t <= 0 for t in self.usg_event_times_s):
            raise ValueError("spot times must be finite and positive")
        if tuple(sorted(set(self.usg_event_times_s))) != self.usg_event_times_s:
            raise ValueError("spot times must be unique and sorted")
        return self


class Settings(FrozenModel):
    """All timing is simulation seconds except explicitly named wall-clock fields."""

    start: datetime = datetime(2026, 11, 14, tzinfo=UTC)
    speed: float = Field(default=1, gt=0, le=1e7)
    duration_s: float | None = Field(default=None, gt=0)
    sans_scenario: SansScenario | None = None
    hypercapnia_scenario: HypercapniaScenario | None = None
    eva_dehydration_scenario: EvaDehydrationScenario | None = None
    seed: int = 42
    crew: tuple[AstronautProfile, ...] = (AstronautProfile(),)
    environment: Environment = Environment()
    base_url: str = "http://127.0.0.1:8000"
    data_route: str = "/api/readings/"
    enabled_channels: tuple[str, ...] | None = None
    lab_delay_s: float = Field(default=3600, ge=0, le=30 * 86400)
    bp_session_start_s: float = Field(default=8 * 3600, ge=0)
    bp_session_duration_s: float | None = Field(default=None, gt=0)
    exercise_test_days: tuple[int, ...] = (0,)
    queue_capacity: int = Field(default=512, ge=1, le=100000)
    max_age_s: float = Field(default=86400 * 7, gt=0)
    max_attempts: int = Field(default=3, ge=1, le=10)
    timeout_wall_s: float = Field(default=5, gt=0, le=60)
    backoff_wall_s: float = Field(default=0.5, ge=0, le=10)
    shutdown_drain_wall_s: float = Field(default=5, ge=0, le=60)
    radiation_interval_s: float = Field(default=1, ge=1)
    spe_heartbeat_s: float = Field(default=1, ge=1)
    stand_test_start_s: float | None = Field(default=None, ge=0)
    il6_event_times_s: tuple[float, ...] = (0,)
    troponin_event_times_s: tuple[float, ...] = (0,)

    @field_validator("start")
    @classmethod
    def utc_start(cls, value: datetime) -> datetime:
        """Require explicit UTC mapping; host timezone must not change the run."""
        return Reading.utc_timestamp(value)

    @field_validator("base_url")
    @classmethod
    def http_destination(cls, value: str) -> str:
        """Only explicit HTTP destinations are valid; credentials belong in a header."""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base_url cannot contain credentials, query or fragment")
        return value.rstrip("/")

    @model_validator(mode="after")
    def unique_owners(self) -> Settings:
        """Prevent duplicate crew streams and route errors before any network activity."""
        if len({p.id for p in self.crew}) != len(self.crew):
            raise ValueError("crew IDs must be unique")
        if self.eva_dehydration_scenario is not None:
            eva = self.eva_dehydration_scenario
            if self.sans_scenario or self.hypercapnia_scenario:
                raise ValueError("combined faults are unsupported")
            profiles = {p.id: p for p in self.crew}
            if eva.owner_id not in profiles:
                raise ValueError("EVA requires an existing crew owner")
            profile = profiles[eva.owner_id]
            loss = (
                (eva.active_whole_body_sweat_l_h - eva.drink_rate_l_h) * eva.eva_duration_s / 3600
            )
            if loss >= profile.mass_kg:
                raise ValueError("EVA loss must remain below initial mass")
            if (
                eva.affected_sbp_mmhg >= profile.sbp_mmhg
                or eva.affected_dbp_mmhg > profile.dbp_mmhg
            ):
                raise ValueError("EVA pressure targets must not rise")
            if self.stand_test_start_s is not None or self.bp_session_duration_s is not None:
                raise ValueError("EVA target BP schedule conflicts with session overrides")
        if self.hypercapnia_scenario is not None:
            from .units import MMHG_TO_PA

            fault = self.hypercapnia_scenario
            if self.sans_scenario is not None:
                raise ValueError("combined SANS and hypercapnia scenarios are unsupported")
            if not self.crew or fault.environment_id != self.environment.id:
                raise ValueError("hypercapnia requires crew and the configured environment")
            if fault.affected_ppco2_mmhg * MMHG_TO_PA >= self.environment.pressure_pa:
                raise ValueError("CO2 partial pressure must be below cabin pressure")
            if any(p.resting_hr_bpm >= fault.affected_heart_rate_bpm for p in self.crew):
                raise ValueError("heart rate must rise")
        if self.sans_scenario is not None:
            scenario = self.sans_scenario
            profiles = {p.id: p for p in self.crew}
            if scenario.owner_id not in profiles or self.environment.gravity_g != 0:
                raise ValueError("SANS requires an existing crew owner and gravity_g = 0")
            if scenario.affected_rmssd_ms > profiles[scenario.owner_id].rmssd_ms:
                raise ValueError("SANS RMSSD target must not exceed healthy reference")
        if any(day < 0 for day in self.exercise_test_days):
            raise ValueError("exercise test days cannot be negative")
        for instant in (*self.il6_event_times_s, *self.troponin_event_times_s):
            if not math.isfinite(instant) or instant < 0:
                raise ValueError("assay event times must be finite and nonnegative")
        if not self.data_route.startswith("/") or self.data_route.startswith("//"):
            raise ValueError("data_route must be a path beginning with one slash")
        if "{" in self.data_route or "}" in self.data_route:
            raise ValueError("data_route is shared by all readings and cannot contain placeholders")
        return self


class Observation(FrozenModel):
    """RAM-only delivery item; metadata is sent as headers, never added to the body."""

    reading: Reading
    scope: Literal["crew", "environment"]
    owner: str
    sensor_id: str
    sequence: int
    acquired_s: float
    available_s: float
    window_s: float = 0
    sample_kind: Literal["startup_baseline", "scheduled"] = "scheduled"

    @model_validator(mode="after")
    def timing(self) -> Observation:
        """Do not permit impossible result availability or non-finite model times."""
        for value in (self.acquired_s, self.available_s, self.window_s):
            if not math.isfinite(value) or value < 0:
                raise ValueError("observation times must be finite and nonnegative")
        if self.available_s < self.acquired_s:
            raise ValueError("result cannot precede collection")
        return self
