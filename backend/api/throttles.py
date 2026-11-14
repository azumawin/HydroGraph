"""Rate limits for the health assistant: every call spends Ollama Cloud credits.

Counted per client IP in Django's default cache, a per-process LocMem cache,
which is enough for a single runserver.
"""

from rest_framework.throttling import AnonRateThrottle


class AssistantBurstThrottle(AnonRateThrottle):
    scope = "assistant"


class AssistantDailyThrottle(AnonRateThrottle):
    scope = "assistant_daily"
