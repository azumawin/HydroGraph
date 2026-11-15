"""Auditable registry: specimen-specific units, acquisition groups and sources."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .frequency import FREQUENCIES, LAB_DEMO_CALENDAR, lab_demo_interval
from .models import Environment, FrozenModel, Settings
from .scenarios import EVA_CHANNELS, HYPERCAPNIA_CHANNELS, INFECTION_CHANNELS, SANS_CHANNELS
from .units import MMHG_TO_PA

NASA = "https://www.nasa.gov/wp-content/uploads/2024/09/ochmo-std-100-1a-rev-a-signed.pdf"
SOURCES: dict[str, str] = {
    "vitals": "https://www.medlineplus.gov/ency/article/002341.htm",
    "hr": "https://www.heart.org/en/healthy-living/exercise-and-physical-activity/fitness-basics/target-heart-rates/",
    "hrv": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5010946/",
    "bp": "https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings/",
    "spo2": "https://www.medlineplus.gov/lab-tests/pulse-oximetry/",
    "glucose": "https://www.niddk.nih.gov/health-information/diabetes/overview/managing-diabetes/continuous-glucose-monitoring",
    "cortisol": "https://www.mayocliniclabs.com/test-catalog/overview/623604",
    "troponin": "https://testguide.labmed.uw.edu/view/TROPBC?tabs=yes",
    "lactate": "https://www.mayocliniclabs.com/test-catalog/Overview/601685",
    "ntx": "https://testguide.labmed.uw.edu/view/RUNTXP",
    "vitamin": "https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/",
    "il6": "https://www.mayocliniclabs.com/test-catalog/overview/618776",
    "sweat": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9942894/",
    "viral": "https://www.nature.com/articles/s41526-017-0015-y",
    "usg": "https://www.medlineplus.gov/ency/article/003587.htm",
    "urine": "https://www.auajournals.org/doi/10.1016/j.juro.2014.05.006",
    "co2": "https://www.nasa.gov/reference/6-0-natural-and-induced-environments-vol-2/",
    "radiation": "https://ntrs.nasa.gov/api/citations/20240011436/downloads/BEAM-Report-NASA-TP-new.pdf",
    "light": "https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3001571",
}


@dataclass(frozen=True)
class Channel:
    """Source values are converted once at the transport boundary, never reinterpreted."""

    id: str
    name: str
    group: str
    domain: str
    specimen: str
    source_unit: str
    unit: str
    method: str
    schedule: str
    source: str
    factor: float = 1
    offset: float = 0
    window_s: float = 0
    lab: bool = False
    scope: Literal["crew", "environment"] = "crew"

    @property
    def body_regions(self) -> tuple[str, ...]:
        """Environment records have no body region or implied astronaut ownership."""
        return (
            ()
            if self.scope == "environment"
            else (("heart", "chest") if self.domain == "cardiovascular" else ("body",))
        )


def channel(
    id: str,
    name: str,
    group: str,
    domain: str,
    specimen: str,
    source_unit: str,
    unit: str,
    method: str,
    schedule: str,
    source: str,
    *,
    factor: float = 1,
    offset: float = 0,
    window: float = 0,
    lab: bool = False,
    scope: Literal["crew", "environment"] = "crew",
) -> Channel:
    """Keep each registry entry compact while requiring acquisition metadata."""
    return Channel(
        id,
        name,
        group,
        domain,
        specimen,
        source_unit,
        unit,
        method,
        schedule,
        SOURCES.get(source, source),
        factor,
        offset,
        window,
        lab,
        scope,
    )


_CHANNELS = (
    channel(
        "il6_pg_mL",
        "Synthetic GFET IL-6",
        "infection_gfet",
        "immune",
        "interstitial fixture",
        "pg/mL",
        "kg/m^3",
        "Synthetic concentration; not calibrated serum equivalence",
        "60s",
        "docs/badscenario4.md",
        factor=1e-9,
    ),
    channel(
        "consciousness_level",
        "Configured consciousness",
        "infection_context",
        "neurological",
        "state fixture",
        "ACVPU",
        "ACVPU",
        "Configured ACVPU state, not an examination",
        "60s",
        "docs/badscenario4.md",
    ),
    channel(
        "supplemental_o2",
        "Supplemental oxygen",
        "infection_context",
        "respiratory",
        "state fixture",
        "boolean",
        "boolean",
        "Configured oxygen context",
        "60s",
        "docs/badscenario4.md",
    ),
    channel(
        "post_ared_exercise_window",
        "Post-ARED window",
        "infection_context",
        "immune",
        "state fixture",
        "boolean",
        "boolean",
        "Configured exercise context",
        "60s",
        "docs/badscenario4.md",
    ),
    channel(
        "whole_body_sweat_rate",
        "Whole-body sweat fixture",
        "eva_sweat",
        "hydration",
        "whole body",
        "L/h",
        "m^3/s",
        "Synthetic whole-body flow; patch scale is an assumption",
        "1s during EVA",
        "docs/badscenario3.md",
        factor=1 / 3_600_000,
    ),
    channel(
        "eeg_cfe_ratio",
        "Synthetic theta/alpha ratio",
        "eeg_cfe",
        "neurocognitive",
        "model fixture",
        "1",
        "1",
        "Mean synthetic ratio fixture; no raw EEG or FFT",
        "60s",
        "docs/hydrogfn_unhealthy_simulation_specification (1).md",
    ),
    channel(
        "jugular_strain_pct",
        "Jugular reference strain",
        "cephalic",
        "neuro-ocular",
        "neck patch",
        "%",
        "1",
        "Synthetic strain trend; no pulse waveform",
        "60s",
        "docs/hydrogfn_unhealthy_simulation_specification (1).md",
        factor=0.01,
    ),
    channel(
        "delta_R_over_R0",
        "Fractional resistance change",
        "cephalic",
        "neuro-ocular",
        "neck patch",
        "1",
        "1",
        "Gauge factor times fractional strain",
        "60s",
        "docs/hydrogfn_unhealthy_simulation_specification (1).md",
    ),
    channel(
        "icp_risk_indicator_mmHg",
        "Synthetic ICP risk indicator",
        "cephalic",
        "neuro-ocular",
        "model fixture",
        "mmHg",
        "Pa",
        "Uncalibrated synthetic proxy, not measured ICP",
        "60s",
        "docs/hydrogfn_unhealthy_simulation_specification (1).md",
        factor=MMHG_TO_PA,
    ),
    channel(
        "visual_acuity_logmar",
        "Visual acuity LogMAR",
        "eye_screen",
        "neuro-ocular",
        "simulated screen",
        "logMAR",
        "1",
        "Synthetic logarithmic visual-screen result",
        "events",
        "docs/hydrogfn_unhealthy_simulation_specification (1).md",
    ),
    channel(
        "amsler_grid_distortion",
        "Amsler distortion",
        "eye_screen",
        "neuro-ocular",
        "simulated screen",
        "boolean",
        "boolean",
        "Synthetic completed screen result",
        "events",
        "docs/hydrogfn_unhealthy_simulation_specification (1).md",
    ),
    channel(
        "heart_rate",
        "Heart rate",
        "heart",
        "cardiovascular",
        "wearable",
        "bpm",
        "s^-1",
        "Synthetic pulse",
        "10s (6 measurements/minute), independent of activity",
        "hr",
        factor=1 / 60,
    ),
    channel(
        "hrv_rmssd",
        "NN interval RMSSD",
        "hrv",
        "cardiovascular",
        "NN intervals",
        "ms",
        "s",
        "RMSSD of generated beat intervals",
        "300s nonoverlapping windows",
        "hrv",
        factor=0.001,
        window=300,
    ),
    channel(
        "bp_systolic",
        "Systolic blood pressure",
        "bp",
        "cardiovascular",
        "cuff",
        "mmHg",
        "Pa",
        "Paired synthetic cuff",
        "hourly in configured session",
        "bp",
        factor=MMHG_TO_PA,
    ),
    channel(
        "bp_diastolic",
        "Diastolic blood pressure",
        "bp",
        "cardiovascular",
        "cuff",
        "mmHg",
        "Pa",
        "Paired synthetic cuff",
        "hourly in configured session",
        "bp",
        factor=MMHG_TO_PA,
    ),
    channel(
        "spo2",
        "Peripheral oxygen saturation",
        "spo2",
        "respiratory",
        "pulse oximeter",
        "%",
        "1",
        "Synthetic pulse oximetry",
        "30s at phase 5s",
        "spo2",
        factor=0.01,
    ),
    channel(
        "body_temperature",
        "Core-equivalent temperature",
        "temperature",
        "general",
        "ZHF estimate",
        "degC",
        "K",
        "Synthetic lagged core-equivalent estimate",
        "60s at phase 11s",
        "vitals",
        offset=273.15,
    ),
    channel(
        "respiratory_rate",
        "Respiratory rate",
        "respiration",
        "respiratory",
        "wearable",
        "min^-1",
        "s^-1",
        "60-second respiratory estimate",
        "6s after initial 30s observation window; first at 31s",
        "vitals",
        factor=1 / 60,
        window=30,
    ),
    channel(
        "glucose",
        "Interstitial glucose",
        "glucose",
        "metabolic",
        "interstitial fluid",
        "mmol/L",
        "mol/m^3",
        "Synthetic CGM with meal lag",
        "300s at phase 43s",
        "glucose",
    ),
    channel(
        "cortisol_saliva",
        "Salivary cortisol",
        "cortisol",
        "endocrine",
        "saliva",
        "nmol/L",
        "mol/m^3",
        "Synthetic Mayo SALCC-compatible fixture",
        "days 0,30,... at 07:00/07:30/13:00/17:00/23:00",
        "cortisol",
        factor=1e-6,
        lab=True,
    ),
    channel(
        "troponin_i",
        "High sensitivity troponin I",
        "troponin",
        "cardiovascular",
        "serum",
        "ng/L",
        "kg/m^3",
        "UW Beckman hs-cTnI synthetic fixture",
        "baseline only",
        "troponin",
        factor=1e-9,
        lab=True,
    ),
    channel(
        "lactate",
        "Plasma lactate",
        "lactate",
        "metabolic",
        "plasma",
        "mmol/L",
        "mol/m^3",
        "Synthetic plasma lactate fixture",
        "baseline + exercise-test pre/5/15/30 min recovery",
        "lactate",
        lab=True,
    ),
    channel(
        "urinary_ntx",
        "Urinary NTx/creatinine",
        "ntx",
        "bone",
        "24h urine",
        "nmol BCE/mmol creatinine",
        "mol BCE/mol creatinine",
        "UW CLIA-compatible synthetic fixture",
        "24h collections starting FD15/30/60/120/180",
        "ntx",
        factor=1e-6,
        window=86400,
        lab=True,
    ),
    channel(
        "bone_ntx_pct_baseline",
        "NTx baseline change",
        "ntx",
        "bone",
        "24h urine",
        "% change",
        "1",
        "100*(NTx/baseline-1), then percent-to-fraction",
        "paired with urinary NTx",
        "ntx",
        factor=0.01,
        window=86400,
        lab=True,
    ),
    channel(
        "vitamin_d_25oh",
        "25-OH vitamin D",
        "vitamin",
        "nutrition",
        "serum",
        "ng/mL",
        "mol/m^3",
        "Synthetic serum 25-OH D fixture; conventional 2.5 nmol/L per ng/mL",
        "baseline then every 30 mission days",
        "vitamin",
        factor=2.5e-6,
        lab=True,
    ),
    channel(
        "il6_serum",
        "Serum IL-6",
        "il6",
        "immune",
        "serum",
        "pg/mL",
        "kg/m^3",
        "Mayo IL6DX-compatible fixture, not NASA plasma research assay",
        "FD15/30/60/120/180",
        "il6",
        factor=1e-9,
        lab=True,
    ),
    channel(
        "sweat_sodium_concentration",
        "Local sweat sodium",
        "sweat",
        "hydration",
        "local sweat",
        "mmol/L",
        "mol/m^3",
        "Filled local patch, 10 cm^2 modeled area",
        "60s while local flow sufficient",
        "sweat",
        window=60,
    ),
    channel(
        "sweat_sodium_flux",
        "Local sweat sodium loss",
        "sweat_summary",
        "hydration",
        "local sweat",
        "mmol/h",
        "mol/s",
        "Matching local concentration times local flow",
        "paired with sweat rate",
        "sweat",
        factor=1 / 3_600_000,
        window=60,
    ),
    channel(
        "sweat_rate",
        "Local sweat flow",
        "sweat",
        "hydration",
        "local sweat",
        "L/h",
        "m^3/s",
        "Synthetic 10 cm^2 patch flow; not whole-body sweat rate",
        "60s during sufficient sweating",
        "sweat",
        factor=1 / 3_600_000,
        window=60,
    ),
    channel(
        "viral_ebv_detected",
        "EBV DNA detected",
        "saliva_pcr",
        "immune",
        "saliva",
        "boolean",
        "boolean",
        "Synthetic PCR fixture; illustrative detection limit 2 copies/reaction",
        "days 0/2/4/6 around each 30-day demo session, 09:00",
        "viral",
        lab=True,
    ),
    channel(
        "viral_vzv_detected",
        "VZV DNA detected",
        "saliva_pcr",
        "immune",
        "saliva",
        "boolean",
        "boolean",
        "Synthetic PCR fixture; illustrative detection limit 2 copies/reaction",
        "paired with EBV saliva",
        "viral",
        lab=True,
    ),
    channel(
        "viral_cmv_detected",
        "CMV DNA detected",
        "urine_pcr",
        "immune",
        "spot urine",
        "boolean",
        "boolean",
        "Synthetic PCR fixture; illustrative detection limit 2 copies/reaction",
        "every 30 days at 10:00",
        "viral",
        lab=True,
    ),
    channel(
        "body_mass",
        "Body mass",
        "mass",
        "nutrition",
        "mass device",
        "kg",
        "kg",
        "Synthetic inertial mass estimate",
        "FD7 then every 30 days",
        NASA,
    ),
    channel(
        "urine_specific_gravity",
        "Urine specific gravity",
        "usg",
        "hydration",
        "spot urine",
        "1",
        "1",
        "Prompted synthetic spot-urine fixture",
        "completed nutrition collection sessions",
        "usg",
        window=86400,
        lab=True,
    ),
    channel(
        "urine_volume_24h",
        "24-hour urine volume",
        "urine",
        "renal",
        "24h urine",
        "L",
        "m^3",
        "Integral of model urine flow over completed collection",
        "end of FD15/30/60/120/180-started collections",
        "urine",
        factor=0.001,
        window=86400,
    ),
    channel(
        "ambient_ppco2",
        "Cabin CO2 partial pressure",
        "co2",
        "environment",
        "cabin atmosphere",
        "Pa",
        "Pa",
        "Synthetic compartment monitor",
        "2s",
        "co2",
        scope="environment",
    ),
    channel(
        "ambient_light_lux",
        "Ambient photopic light",
        "light",
        "environment",
        "cabin light",
        "lux",
        "lx",
        "Synthetic compartment photometer; no spectral/at-eye inference",
        "60s at phase 7s",
        "light",
        scope="environment",
    ),
    channel(
        "ambient_dose_rate",
        "Monitor dose-equivalent rate",
        "radiation",
        "environment",
        "radiation monitor",
        "uSv/h",
        "Sv/s",
        "Modeled monitor equivalent dose, not absorbed Gy",
        "60s or configured",
        "radiation",
        factor=1 / 3_600_000_000,
        scope="environment",
    ),
    channel(
        "ambient_integrated_dose",
        "Integrated monitor dose equivalent",
        "radiation_dose",
        "environment",
        "radiation monitor",
        "mSv",
        "Sv",
        "Exact integral of the same modeled monitor rate",
        "6s at phase 2s; independent of rate publication",
        "radiation",
        factor=0.001,
        scope="environment",
    ),
    channel(
        "spe_flag",
        "Solar particle event flag",
        "spe",
        "environment",
        "event feed",
        "boolean",
        "boolean",
        "Healthy fixture with heartbeat",
        "60s heartbeat or configured",
        "radiation",
        scope="environment",
    ),
)
# The matrix policy is authoritative for both runtime windows and the dictionary.
CHANNELS = {
    item.id: replace(
        item,
        schedule=FREQUENCIES[item.group].description,
        window_s=FREQUENCIES[item.group].window_s,
    )
    for item in _CHANNELS
}


def effective_channels(settings: Settings) -> set[str]:
    enabled = (
        set(settings.enabled_channels)
        if settings.enabled_channels is not None
        else set(CHANNELS) - (SANS_CHANNELS if settings.sans_scenario is None else set())
    )
    if settings.enabled_channels is None and settings.hypercapnia_scenario is None:
        enabled -= HYPERCAPNIA_CHANNELS
    if settings.hypercapnia_scenario is None and enabled & HYPERCAPNIA_CHANNELS:
        raise ValueError("CFE channel requires hypercapnia_scenario configuration")
    if settings.enabled_channels is None and settings.eva_dehydration_scenario is None:
        enabled -= EVA_CHANNELS
    if settings.eva_dehydration_scenario is None and enabled & EVA_CHANNELS:
        raise ValueError("whole-body sweat requires eva_dehydration_scenario")
    if settings.enabled_channels is None and settings.acute_infection_scenario is None:
        enabled -= INFECTION_CHANNELS
    if settings.acute_infection_scenario is None and enabled & INFECTION_CHANNELS:
        raise ValueError("infection channels require acute_infection_scenario")
    if unknown := enabled - CHANNELS.keys():
        raise ValueError(f"unknown enabled channels: {sorted(unknown)}")
    if settings.sans_scenario is None and enabled & SANS_CHANNELS:
        raise ValueError("SANS channels require sans_scenario configuration")
    return enabled


EXCLUDED = (
    "sleep/stages/debt",
    "mood/PHQ9/GAD7",
    "raw EEG acquisition/spectral processing and PVT",
    "headache and interactive visual-screen control",
    "kinematics/exercise compliance",
    "cephalic impedance and calibrated measured ICP",
    "physical hydrogel/GFET sensor models",
    "NEWS2/qSOFA/diagnosis/recommendations (backend-owned)",
    "postural changes/shock index/weekly and endocrine slopes (backend-owned)",
)


class ChannelMetadata(FrozenModel):
    """Dictionary record extends the fields required by nigelNote."""

    channel: str
    name: str
    domain: str
    body_regions: tuple[str, ...]
    explanation: str
    scope: str
    specimen: str
    source_unit: str
    unit: str
    method: str
    collection_schedule: str
    window_s: float
    availability_delay_s: float
    citations: tuple[str, ...]
    value_schema: str
    raw_acquisition_hz: float | None = None
    frequency_matrix_rows: tuple[int, ...] = ()
    frequency_basis: str = "docs/frequency_table.md"
    enabled: bool = True


class Dictionary(FrozenModel):
    """Static dictionary is explicitly exportable; it contains no generated readings."""

    version: str = "1"
    environment: Environment
    channels: tuple[ChannelMetadata, ...]
    excluded: tuple[str, ...] = EXCLUDED
    sans_scenario: dict[str, object] | None = None
    hypercapnia_scenario: dict[str, object] | None = None
    eva_dehydration_scenario: dict[str, object] | None = None
    acute_infection_scenario: dict[str, object] | None = None
    startup_behavior: str = (
        "One immediately available synthetic startup_baseline per enabled owner/channel, "
        "then the listed schedule. Startup has no completed collection window or lab delay; "
        "communication delay still applies. Headers and preview metadata identify sample kind."
    )


def dictionary(
    environment: Environment,
    lab_delay_s: float,
    settings: Settings | None = None,
) -> Dictionary:
    """Describe all channels and the explicitly synthetic laboratory processing delay."""
    overrides: dict[str, str] = {}
    if settings is not None:
        overrides = {
            "bp": f"hourly from {settings.bp_session_start_s}s; "
            f"duration={settings.bp_session_duration_s or 'unlimited'}s; "
            f"10Hz/180s stand-test starts={settings.stand_test_start_s}",
            "il6": f"gated assay events at run seconds {settings.il6_event_times_s}",
            "troponin": f"assay events at run seconds {settings.troponin_event_times_s}",
            "radiation": f"every {settings.radiation_interval_s} simulation seconds",
            "spe": f"heartbeat every {settings.spe_heartbeat_s} simulation seconds",
            "lactate": f"baseline plus exercise tests on days {settings.exercise_test_days}; "
            "17:00 pre-test and 18:05/18:15/18:30 recovery",
        }
    if settings and settings.sans_scenario:
        overrides["eye_screen"] = f"screen events at {settings.sans_scenario.eye_screen_times_s}"
    if settings and settings.eva_dehydration_scenario:
        overrides.update(
            {
                "mass": "EVA target: synthetic 60s points; other crew retain daily schedule",
                "bp": "EVA target: synthetic paired 60s estimates",
                "usg": (
                    "EVA target synthetic spots: "
                    f"{settings.eva_dehydration_scenario.usg_event_times_s}"
                ),
                "sweat": "EVA target: complete 1s windows during EVA; other crew: active/wet",
                "sweat_summary": "EVA target: complete active 60s means; other crew: active/wet",
            }
        )
    if settings and settings.acute_infection_scenario:
        fault = settings.acute_infection_scenario
        overrides.update(
            {
                "bp": "infection target: synthetic minute BP; others: healthy schedule",
                "il6": f"infection target specimens at {fault.serum_il6_event_times_s}",
                "saliva_pcr": f"infection target specimens at {fault.saliva_pcr_event_times_s}",
            }
        )
    if settings and settings.bp_demo_interval_s is not None:
        overrides["bp"] = (
            f"dashboard demo: paired synthetic trends every {settings.bp_demo_interval_s}s; "
            "replaces cuff, scenario and stand-test timing"
        )
    if settings and settings.glucose_demo_interval_s is not None:
        overrides["glucose"] = (
            f"dashboard demo: synthetic trend every {settings.glucose_demo_interval_s}s, "
            f"averaging that window's raw samples; replaces the 5-minute CGM window"
        )
    if settings and settings.lab_demo_interval_s is not None:
        effective = lab_demo_interval(settings.lab_demo_interval_s, settings.speed)
        for group, calendar in LAB_DEMO_CALENDAR.items():
            overrides[group] = (
                f"dashboard demo: every {effective}s, each sample "
                f"{calendar.step}s further along this channel's own calendar from "
                f"{calendar.first}s; results are not held for laboratory processing"
            )
    return Dictionary(
        environment=environment,
        acute_infection_scenario=(
            settings.acute_infection_scenario.model_dump(mode="json")
            if settings and settings.acute_infection_scenario
            else None
        ),
        eva_dehydration_scenario=(
            settings.eva_dehydration_scenario.model_dump(mode="json")
            if settings and settings.eva_dehydration_scenario
            else None
        ),
        hypercapnia_scenario=(
            settings.hypercapnia_scenario.model_dump(mode="json")
            if settings and settings.hypercapnia_scenario
            else None
        ),
        sans_scenario=(
            settings.sans_scenario.model_dump(mode="json")
            if settings and settings.sans_scenario
            else None
        ),
        channels=tuple(
            ChannelMetadata(
                channel=c.id,
                name=c.name,
                domain=c.domain,
                body_regions=c.body_regions,
                explanation=f"{c.method}. Simulation assumptions: "
                "NASA_MONITORING_PLAN.md and docs/model_assumptions.md.",
                scope=c.scope,
                specimen=c.specimen,
                source_unit=c.source_unit,
                unit=c.unit,
                method=(
                    c.method + "; synthetic dashboard trend with bounded variation"
                    if c.group == "glucose"
                    and settings is not None
                    and settings.glucose_demo_interval_s is not None
                    else c.method + "; synthetic dashboard trend with bounded paired variation"
                    if c.group == "bp"
                    and settings is not None
                    and settings.bp_demo_interval_s is not None
                    else c.method + "; stand-test burst uses synthetic continuous pressure, not "
                    "10Hz cuff inflation"
                    if c.group == "bp"
                    and settings is not None
                    and settings.stand_test_start_s is not None
                    else c.method
                ),
                collection_schedule=overrides.get(c.group, c.schedule),
                window_s=(
                    settings.glucose_demo_interval_s
                    if c.group == "glucose"
                    and settings
                    and settings.glucose_demo_interval_s is not None
                    else c.window_s
                ),
                availability_delay_s=(
                    0
                    if settings is not None
                    and settings.lab_demo_interval_s is not None
                    and c.group in LAB_DEMO_CALENDAR
                    else lab_delay_s
                    if c.lab
                    else 0
                ),
                citations=(c.source,),
                value_schema="enum:ALERT,CONFUSION,VOICE,PAIN,UNRESPONSIVE"
                if c.unit == "ACVPU"
                else "boolean"
                if c.unit == "boolean"
                else "number",
                raw_acquisition_hz=FREQUENCIES[c.group].raw_hz,
                frequency_matrix_rows=FREQUENCIES[c.group].rows,
                frequency_basis=(
                    "explicit dashboard demo override"
                    if (c.group == "bp" and settings and settings.bp_demo_interval_s is not None)
                    or (
                        c.group == "glucose"
                        and settings
                        and settings.glucose_demo_interval_s is not None
                    )
                    or (
                        c.group in LAB_DEMO_CALENDAR
                        and settings
                        and settings.lab_demo_interval_s is not None
                    )
                    else "docs/frequency_table.md"
                ),
                enabled=settings is None or c.id in effective_channels(settings),
            )
            for c in CHANNELS.values()
        ),
    )
