from typing import cast, get_args

import hydrograph_core
from django.http import HttpRequest, StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.views.decorators.http import require_GET
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,  # pyright: ignore[reportUnknownVariableType]  # stubs: Serializer[Unknown]
)
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from api.broadcast import publish
from api.findings import affected_findings
from api.models import Reading
from api.serializers import (
    ReadingIn,
    ReadingInSerializer,
    environments_payload,
    finding_payload,
    reading_payload,
)
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
def health(_request: Request) -> Response:
    """Liveness probe, also proves the core package is wired in."""
    return Response({"status": "ok", "core_version": hydrograph_core.__version__})


@extend_schema(
    summary="The predefined mission environments",
    responses={
        200: {
            "type": "object",
            "properties": {
                "environments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "enum": list(hydrograph_core.ENVIRONMENTS),
                            },
                            "name": {"type": "string"},
                            "gravity_g": {"type": "number"},
                            "comm_delay_rt_s": {"type": "number"},
                            "baseline_dose_rate_usv_h": {"type": "number"},
                            "storm_shelter_available": {"type": "boolean"},
                            "day_length_h": {"type": "number"},
                        },
                    },
                }
            },
        }
    },
)
@api_view(["GET"])
def environments(_request: Request) -> Response:
    """The environments the dashboard offers, for the environment switcher.

    Static, so one fetch is enough; the stream dictionary carries the same list
    for clients that only open the stream.
    """
    return Response({"environments": environments_payload()})


@extend_schema(
    summary="Ingest one sensor reading",
    parameters=[
        OpenApiParameter(
            "X-Simulation-Scope",
            str,
            OpenApiParameter.HEADER,
            required=True,
            enum=["crew", "environment"],
        ),
    ],
    request=ReadingInSerializer,
    responses={
        201: {
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "value": {"oneOf": [{"type": "number"}, {"type": "boolean"}]},
                "unit": {"type": "string"},
                "evaluation": {
                    "type": "string",
                    "enum": list(get_args(hydrograph_core.Evaluation)),
                },
                "measured_at": {"type": "string", "format": "date-time"},
                "scope": {"type": "string", "enum": ["crew", "environment"]},
            },
        }
    },
)
@api_view(["POST"])
def readings(request: Request) -> Response:
    """Store the reading and push it, and the findings it changes, to every stream."""
    scope = request.headers.get("X-Simulation-Scope", "")
    serializer = ReadingInSerializer(data=request.data, context={"scope": scope})
    _ = serializer.is_valid(raise_exception=True)
    data = cast(ReadingIn, serializer.validated_data)
    reading = Reading.objects.create(
        channel=data["channel"],
        value=data["value"],
        measured_at=data["measured_at"],
    )
    payload = reading_payload(reading)
    publish(sse_event("reading", payload))
    for finding, result in affected_findings(reading.channel).items():
        publish(sse_event("finding", finding_payload(finding, result)))
    return Response(payload, status=status.HTTP_201_CREATED)


@require_GET
async def stream(_request: HttpRequest) -> HttpResponseBase:
    """SSE stream of the dictionary and readings; plain Django, since DRF is sync."""
    response = StreamingHttpResponse(events(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # stop nginx-style proxies buffering
    return response
