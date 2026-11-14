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
        ``max_interval_s``. The plan gives "Every 15 – 30 sec" for
        cardiovascular channels while active, so the two intervals can
        differ; the scheduler may poll anywhere in between. Continuous is
        1 Hz (1 s). Suspended and unspecified have no interval (``None``).
        While sleeping:

        - ``cephalic_fluid_index`` is UNSPECIFIED: the group is "Suspended /
          Paused", but the plan also says passive SANS tracking continues,
          with no rate.
        - ``eeg_theta_alpha_ratio`` is hourly ("Hourly EEG").
        - ``pvt_reaction_time`` is UNSPECIFIED: the plan names only
          actigraphy and EEG for sleep.

    Raises:
        ValueError: If ``channel`` is not in the plan's polling table.
    """
    minute, hour = 60.0, 3600.0
    cont = (Mode.CONTINUOUS, 1.0, 1.0)  # 1 Hz
    suspended = (Mode.SUSPENDED, None, None)
    unspecified = (Mode.UNSPECIFIED, None, None)

    # group: (channels, {state: (mode, min interval [s], max interval [s])}), master plan p.4-5
    table = {
        "Environmental & Safety": (
            ("radiation_dose", "dose_rate", "spe_flag"),
            {
                UserState.ACTIVE: cont,
                UserState.RESTING: cont,
                UserState.SLEEPING: cont,
            },
        ),
        "Cardiovascular Vitals": (
            ("heart_rate", "hrv_rmssd", "bp_systolic", "bp_diastolic"),
            {
                UserState.ACTIVE: (Mode.PERIODIC, 15.0, 30.0),
                UserState.RESTING: (Mode.PERIODIC, 5 * minute, 5 * minute),
                UserState.SLEEPING: (Mode.PERIODIC, 15 * minute, 15 * minute),
            },
        ),
        "Biomechanics & Fluids": (
            ("cephalic_fluid_index", "sweat_rate", "joint_kinematics"),
            {
                UserState.ACTIVE: (Mode.PERIODIC, minute, minute),
                UserState.RESTING: (Mode.PERIODIC, 15 * minute, 15 * minute),
                UserState.SLEEPING: suspended,
            },
        ),
        "Metabolic & GFET Markers": (
            ("glucose", "lactate", "cortisol", "bone_ntx_pct_baseline"),
            {
                UserState.ACTIVE: (Mode.PERIODIC, 5 * minute, 5 * minute),
                UserState.RESTING: (Mode.PERIODIC, 30 * minute, 30 * minute),
                UserState.SLEEPING: (Mode.PERIODIC, hour, hour),
            },
        ),
        "Neuro-Cognitive": (
            ("eeg_theta_alpha_ratio", "pvt_reaction_time"),
            {
                UserState.ACTIVE: (Mode.PERIODIC, 15 * minute, 15 * minute),
                UserState.RESTING: (Mode.PERIODIC, hour, hour),
                UserState.SLEEPING: (Mode.PERIODIC, hour, hour),
            },
        ),
    }

    for group, (channels, by_state) in table.items():
        if channel in channels:
            mode, lo, hi = by_state[state]
            # sleep exceptions the group row cannot carry; see Returns
            if state is UserState.SLEEPING and channel in (
                "cephalic_fluid_index",
                "pvt_reaction_time",
            ):
                mode, lo, hi = unspecified
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
            ``"nominal"``, ``"unspecified"``), as in ``hydrogfn.Status``.

    Returns:
        ``True`` if the alert may fire. Nominal never alerts. Environmental &
        Safety channels always alert ("Non-Negotiable Override: Independent
        of user state"). While sleeping, other channels alert only when
        critical (p.1: "strict sleep-protection locks for non-critical
        telemetry"; p.4: "active hydration prompts lock out").

    Raises:
        ValueError: If ``channel`` is not in the plan's polling table.
    """
    group = poll_interval(channel, state)["group"]

    if status == "nominal":
        return False
    if group == "Environmental & Safety":
        return True
    if state is UserState.SLEEPING:
        return status == "critical"
    return True
