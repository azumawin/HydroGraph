"""Master plan section 4: adaptive polling frequency per channel and user state."""

from __future__ import annotations

from enum import Enum
from typing import TypedDict


class UserState(str, Enum):
    """User behavioral state, as in the payload's ``user_state`` field."""

    ACTIVE = "ACTIVE"
    RESTING = "RESTING"
    SLEEPING = "SLEEPING"


class Mode(str, Enum):
    """How a channel is sampled in one state."""

    CONTINUOUS = "continuous"
    PERIODIC = "periodic"
    SUSPENDED = "suspended"
    UNSPECIFIED = "unspecified"


class PollInterval(TypedDict):
    channel: str
    group: str
    state: UserState
    mode: Mode
    min_interval_s: float | None
    max_interval_s: float | None


def poll_interval(channel: str, state: UserState) -> PollInterval:
    r"""
    Section 4: Adaptive polling interval for one telemetry channel.

    References:
        None given in the plan for the polling table.

    Args:
        channel: Payload channel name from the plan's table (``heart_rate``,
            ``cortisol``, ...).
        state: Current user state.

    Returns:
        ``channel``, ``group``, ``state``, ``mode``, ``min_interval_s``,
        ``max_interval_s``. The plan gives "Every 15–30 sec" for
        cardiovascular channels while active, so the two intervals can
        differ; the scheduler may poll anywhere in between. Radiation & SPE
        channels are continuous at 1 Hz (1 s). Suspended and unspecified have
        no interval (``None``). While sleeping:

        - ``cephalic_fluid_index`` is UNSPECIFIED: the group is "Suspended
          (SANS passive)", and passive neck SANS monitoring continues, with
          no rate.
        - ``actigraphy`` is CONTINUOUS with no interval (``None``): the plan
          says "Continuous Actigraphy" but gives no rate.
        - ``eeg_theta_alpha_ratio`` and ``pvt_rt`` are UNSPECIFIED: the plan
          names only actigraphy for sleep.

    Raises:
        ValueError: If ``channel`` is not in the plan's polling table.
    """
    minute, hour = 60.0, 3600.0
    cont = (Mode.CONTINUOUS, 1.0, 1.0)  # 1 Hz
    suspended = (Mode.SUSPENDED, None, None)
    unspecified = (Mode.UNSPECIFIED, None, None)

    # group: (channels, {state: (mode, min interval [s], max interval [s])}), master plan p.6
    table = {
        "Radiation & SPE Safety": (
            ("radiation_dose", "dose_rate", "spe_flag"),
            {
                UserState.ACTIVE: cont,
                UserState.RESTING: cont,
                UserState.SLEEPING: cont,
            },
        ),
        "Cardiovascular Vitals": (
            ("heart_rate", "hrv_rmssd", "bp_sys", "bp_dia"),
            {
                UserState.ACTIVE: (Mode.PERIODIC, 15.0, 30.0),
                UserState.RESTING: (Mode.PERIODIC, 5 * minute, 5 * minute),
                UserState.SLEEPING: (Mode.PERIODIC, 15 * minute, 15 * minute),
            },
        ),
        "Hydrogel Strain & Sweat": (
            ("cephalic_fluid_index", "sweat_rate", "kinematics"),
            {
                UserState.ACTIVE: (Mode.PERIODIC, minute, minute),
                UserState.RESTING: (Mode.PERIODIC, 15 * minute, 15 * minute),
                UserState.SLEEPING: suspended,
            },
        ),
        "GFET Molecular Markers": (
            ("glucose", "lactate", "cortisol", "ntx_pct", "il6"),
            {
                UserState.ACTIVE: (Mode.PERIODIC, 5 * minute, 5 * minute),
                UserState.RESTING: (Mode.PERIODIC, 30 * minute, 30 * minute),
                UserState.SLEEPING: (Mode.PERIODIC, hour, hour),
            },
        ),
        "Neuro-Cognitive & Sleep": (
            ("eeg_theta_alpha_ratio", "pvt_rt", "actigraphy"),
            {
                UserState.ACTIVE: (Mode.PERIODIC, 15 * minute, 15 * minute),
                UserState.RESTING: (Mode.PERIODIC, hour, hour),
                UserState.SLEEPING: unspecified,
            },
        ),
    }

    for group, (channels, by_state) in table.items():
        if channel in channels:
            mode, lo, hi = by_state[state]
            # sleep exceptions the group row cannot carry; see Returns
            if state is UserState.SLEEPING and channel == "cephalic_fluid_index":
                mode, lo, hi = unspecified
            if state is UserState.SLEEPING and channel == "actigraphy":
                mode, lo, hi = Mode.CONTINUOUS, None, None
            return {
                "channel": channel,
                "group": group,
                "state": state,
                "mode": mode,
                "min_interval_s": lo,
                "max_interval_s": hi,
            }

    raise ValueError(f"channel {channel!r} is not in the plan's polling table")


def alert_allowed(channel: str, state: UserState, status: str) -> bool:
    r"""
    Section 4: Whether a channel's status may raise an alert or prompt now.

    References:
        None given in the plan for the polling table.

    Args:
        channel: Payload channel name from the plan's table.
        state: Current user state.
        status: The reading's status value (``"critical"``, ``"warning"``,
            ``"nominal"``, ``"unspecified"``), as in ``hydrograph_core.Status``.

    Returns:
        ``True`` if the alert may fire. Nominal never alerts. Radiation & SPE
        Safety channels always alert ("Hardwired 1 Hz Override: Independent
        of user state"). While sleeping, other channels alert only when
        critical (p.1: "strict circadian sleep-protection locks for
        non-critical telemetry"; p.6: "active hydration prompts lock out").

    Raises:
        ValueError: If ``channel`` is not in the plan's polling table.
    """
    group = poll_interval(channel, state)["group"]

    if status == "nominal":
        return False
    if group == "Radiation & SPE Safety":
        return True
    if state is UserState.SLEEPING:
        return status == "critical"
    return True
