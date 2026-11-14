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

from api.assistant import AssistantError, ChatMessage, reply
from api.broadcast import publish
from api.environment import current_environment, current_environment_id
from api.findings import affected_findings, crew_findings
from api.models import EnvironmentSelection, Reading
from api.serializers import (
    ChatSerializer,
    EnvironmentSelectionSerializer,
    HistoryQuery,
    HistoryQuerySerializer,
    ReadingIn,
    ReadingInSerializer,
    ReadingPayload,
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
                    "type": "object",
                    "description": "Keyed by environment id, in dropdown order.",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
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


ENVIRONMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "enum": list(hydrograph_core.ENVIRONMENTS)}
    },
}


@extend_schema(
    methods=["GET"],
    summary="The mission environment in effect",
    responses={200: ENVIRONMENT_SCHEMA},
)
@extend_schema(
    methods=["PUT"],
    summary="Switch the mission environment",
    request=EnvironmentSelectionSerializer,
    responses={200: ENVIRONMENT_SCHEMA},
)
@api_view(["GET", "PUT"])
def environment(request: Request) -> Response:
    """The environment in effect; PUT switches it for every dashboard and simulator.

    A switch is pushed to every stream, with the latest dose-rate reading and
    the radiation finding re-graded, since both depend on the environment.
    """
    if request.method == "PUT":
        serializer = EnvironmentSelectionSerializer(data=request.data)
        _ = serializer.is_valid(raise_exception=True)
        environment_id = cast("dict[str, str]", serializer.validated_data)["id"]
        _ = EnvironmentSelection.objects.create(environment_id=environment_id)
        selected = hydrograph_core.ENVIRONMENTS[environment_id]
        publish(sse_event("environment", {"id": environment_id}))
        dose_rate = (
            Reading.objects.filter(channel="ambient_dose_rate")
            .order_by("-measured_at", "-id")
            .first()
        )
        if dose_rate is not None:
            publish(sse_event("reading", reading_payload(dose_rate, selected)))
        for finding, result in crew_findings(
            selected, ["radiation_exposure_3_2"]
        ).items():
            publish(sse_event("finding", finding_payload(finding, result)))
    return Response({"id": current_environment_id()})


READING_SCHEMA = {
    "type": "object",
    "properties": {
        "channel": {"type": "string"},
        "value": {"oneOf": [{"type": "number"}, {"type": "boolean"}]},
        "measured_at": {"type": "string", "format": "date-time"},
        "evaluation": {
            "type": "string",
            "enum": list(get_args(hydrograph_core.Evaluation)),
        },
    },
}


@extend_schema(
    methods=["GET"],
    summary="Reading history per channel",
    parameters=[
        OpenApiParameter(
            "channel",
            str,
            OpenApiParameter.QUERY,
            many=True,
            description="Repeat for several; all channels when omitted.",
        ),
        OpenApiParameter(
            "limit",
            int,
            OpenApiParameter.QUERY,
            description="Latest readings per channel, 1-1000 (default 120).",
        ),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "readings": {
                    "type": "object",
                    "description": "Channel to its readings, oldest first.",
                    "additionalProperties": {"type": "array", "items": READING_SCHEMA},
                }
            },
        }
    },
)
@extend_schema(
    methods=["POST"],
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
    responses={201: READING_SCHEMA},
)
@api_view(["GET", "POST"])
def readings(request: Request) -> Response:
    """GET: the latest ``limit`` readings per channel, oldest first, so a client
    can fill its charts on load. POST: store a reading and push it, and the
    findings it changes, to every stream.
    """
    if request.method == "GET":
        return reading_history(request)
    scope = request.headers.get("X-Simulation-Scope", "")
    serializer = ReadingInSerializer(data=request.data, context={"scope": scope})
    _ = serializer.is_valid(raise_exception=True)
    data = cast(ReadingIn, serializer.validated_data)
    reading = Reading.objects.create(
        channel=data["channel"],
        value=data["value"],
        measured_at=data["measured_at"],
    )
    environment = current_environment()
    payload = reading_payload(reading, environment)
    publish(sse_event("reading", payload))
    for finding, result in affected_findings(reading.channel, environment).items():
        publish(sse_event("finding", finding_payload(finding, result)))
    return Response(payload, status=status.HTTP_201_CREATED)


def reading_history(request: Request) -> Response:
    """Channels without readings are left out; grading uses the environment in
    effect, as the stream does."""
    query = HistoryQuerySerializer(
        data={
            "channel": request.query_params.getlist("channel"),
            "limit": request.query_params.get("limit", 120),
        }
    )
    _ = query.is_valid(raise_exception=True)
    data = cast(HistoryQuery, query.validated_data)
    environment = current_environment()
    history: dict[str, list[ReadingPayload]] = {}
    for channel in data["channel"] or hydrograph_core.CHANNELS:
        latest = list(
            Reading.objects.filter(channel=channel).order_by("-measured_at", "-id")[
                : data["limit"]
            ]
        )
        if latest:
            history[channel] = [
                reading_payload(r, environment) for r in reversed(latest)
            ]
    return Response({"readings": history})


@extend_schema(
    summary="Ask the health assistant",
    request=ChatSerializer,
    responses={
        200: {"type": "object", "properties": {"reply": {"type": "string"}}},
        503: {"type": "object", "properties": {"detail": {"type": "string"}}},
    },
)
@api_view(["POST"])
def assistant(request: Request) -> Response:
    """The LLM's next message, briefed with the live findings and readings."""
    serializer = ChatSerializer(data=request.data)
    _ = serializer.is_valid(raise_exception=True)
    data = cast("dict[str, list[ChatMessage]]", serializer.validated_data)
    try:
        return Response({"reply": reply(data["messages"])})
    except AssistantError as error:
        return Response(
            {"detail": str(error)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@require_GET
async def stream(_request: HttpRequest) -> HttpResponseBase:
    """SSE stream of the dictionary and readings; plain Django, since DRF is sync."""
    response = StreamingHttpResponse(events(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # stop nginx-style proxies buffering
    return response
