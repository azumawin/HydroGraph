import hydrograph_core
from django.http import HttpRequest, JsonResponse, StreamingHttpResponse
from django.http.response import HttpResponseBase
from drf_spectacular.utils import extend_schema
from hydrograph_core import ENVIRONMENTS
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from api.broadcast import publish
from api.models import Reading
from api.serializers import ReadingInSerializer, ReadingOutSerializer, reading_payload
from api.stream import events, sse_event

DEFAULT_ENVIRONMENT = "lunar_surface"


@extend_schema(
    summary="Liveness probe",
    responses={
        200: {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "core_version": {"type": "string"},
            },
        }
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request: Request) -> Response:
    """Liveness probe, also proves the core package is wired in."""
    return Response({"status": "ok", "core_version": hydrograph_core.__version__})


@extend_schema(
    summary="Ingest a batch of sensor readings",
    request=ReadingInSerializer(many=True),
    responses={201: ReadingOutSerializer(many=True)},
)
@api_view(["POST"])
@authentication_classes([])  # no auth yet
@permission_classes([AllowAny])
def readings(request: Request) -> Response:
    """Store every reading in the array, or none if any item is invalid."""
    serializer = ReadingInSerializer(data=request.data, many=True)
    _ = serializer.is_valid(raise_exception=True)
    created = Reading.objects.bulk_create(
        Reading(**item) for item in serializer.validated_data
    )
    payloads = [reading_payload(r) for r in created]
    for payload in payloads:
        publish(sse_event("reading", payload))
    return Response(payloads, status=status.HTTP_201_CREATED)


async def stream(request: HttpRequest) -> HttpResponseBase:
    """SSE stream of the environment and readings; plain Django, since DRF is sync.

    ``?environment=`` picks the environment (default ``lunar_surface``); the
    frontend reconnects to switch. No auth yet.
    """
    environment_id = request.GET.get("environment", DEFAULT_ENVIRONMENT)
    if environment_id not in ENVIRONMENTS:
        choices = ", ".join(ENVIRONMENTS)
        return JsonResponse(
            {
                "environment": [
                    f'Unknown environment "{environment_id}". Choose: {choices}.'
                ]
            },
            status=400,
        )
    response = StreamingHttpResponse(
        events(environment_id), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # stop nginx-style proxies buffering
    return response
