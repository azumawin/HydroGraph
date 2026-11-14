import hydrograph_core
from django.http import HttpRequest, StreamingHttpResponse
from django.http.response import HttpResponseBase
from drf_spectacular.utils import (
    extend_schema,  # pyright: ignore[reportUnknownVariableType]  # stubs: Serializer[Unknown]
)
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
from api.serializers import ReadingInSerializer, reading_payload
from api.stream import events, sse_event


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
def health(_request: Request) -> Response:
    """Liveness probe, also proves the core package is wired in."""
    return Response({"status": "ok", "core_version": hydrograph_core.__version__})


@extend_schema(
    summary="Ingest one sensor reading",
    request=ReadingInSerializer,
    responses={
        201: {
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "value": {"type": "number"},
                "unit": {"type": "string"},
                "evaluation": {
                    "type": "string",
                    "enum": [s.value for s in hydrograph_core.Status],
                },
                "measured_at": {"type": "string", "format": "date-time"},
                "name": {"type": "string"},
                "body_regions": {"type": "array", "items": {"type": "string"}},
                "explanation": {"type": "string"},
            },
        }
    },
)
@api_view(["POST"])
@authentication_classes([])  # no auth yet
@permission_classes([AllowAny])
def readings(request: Request) -> Response:
    """Store the reading and push it to every open stream."""
    serializer = ReadingInSerializer(data=request.data)
    _ = serializer.is_valid(raise_exception=True)
    payload = reading_payload(serializer.save())
    publish(sse_event("reading", payload))
    return Response(payload, status=status.HTTP_201_CREATED)


async def stream(_request: HttpRequest) -> HttpResponseBase:
    """SSE stream of the environments and readings; plain Django, since DRF is sync.

    No auth yet.
    """
    response = StreamingHttpResponse(events(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # stop nginx-style proxies buffering
    return response
