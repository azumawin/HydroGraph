"""The mission environment in effect: the latest selection, else core's default."""

from hydrograph_core import DEFAULT_ENVIRONMENT, ENVIRONMENTS, EnvironmentInfo

from api.models import EnvironmentSelection


def current_environment_id() -> str:
    latest = EnvironmentSelection.objects.order_by("-selected_at", "-id").first()
    if latest is None or latest.environment_id not in ENVIRONMENTS:
        return DEFAULT_ENVIRONMENT
    return latest.environment_id


def current_environment() -> EnvironmentInfo:
    return ENVIRONMENTS[current_environment_id()]
