"""The mission environment in effect: the latest selection, else core's default."""

from api.models import EnvironmentSelection
from core import DEFAULT_ENVIRONMENT, ENVIRONMENTS, EnvironmentInfo


async def current_environment_id() -> str:
    latest = await EnvironmentSelection.objects.order_by("-selected_at", "-id").afirst()
    if latest is None or latest.environment_id not in ENVIRONMENTS:
        return DEFAULT_ENVIRONMENT
    return latest.environment_id


async def current_environment() -> EnvironmentInfo:
    return ENVIRONMENTS[await current_environment_id()]
