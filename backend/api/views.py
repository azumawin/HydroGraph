import json

from django.http import HttpRequest, JsonResponse, StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

import core
from api.assistant import AssistantError, is_rate_limited, reply
from api.broadcast import publish
from api.contracts import (
    environments_payload,
    finding_payload,
    parse_chat,
    parse_environment,
    parse_history_query,
    parse_reading,
    reading_payload,
)
from api.environment import current_environment, current_environment_id
from api.findings import affected_findings, crew_findings
from api.models import EnvironmentSelection, Reading
from api.stream import events, sse_event


@require_GET
async def health(_request: HttpRequest) -> JsonResponse:
    """Liveness probe, also proves the core package is wired in."""
    return JsonResponse({"status": "ok", "core_version": core.__version__})


@require_GET
async def environments(_request: HttpRequest) -> JsonResponse:
    """The environments the dashboard offers, for the environment switcher."""
    return JsonResponse({"environments": environments_payload()})


@csrf_exempt
@require_http_methods(["GET", "PUT"])
async def environment(request: HttpRequest) -> JsonResponse:
    """The environment in effect; PUT switches it for every dashboard and simulator."""
    if request.method == "PUT":
        payload, error = await _json_body(request)
        if error is not None:
            return error
        environment_id, errors = parse_environment(payload)
        if environment_id is None:
            return JsonResponse(errors, status=400)

        _ = await EnvironmentSelection.objects.acreate(environment_id=environment_id)
        selected = core.ENVIRONMENTS[environment_id]
        publish(sse_event("environment", {"id": environment_id}))
        dose_rate = await (
            Reading.objects.filter(channel="ambient_dose_rate")
            .order_by("-measured_at", "-id")
            .afirst()
        )
        if dose_rate is not None:
            publish(sse_event("reading", reading_payload(dose_rate, selected)))
        for finding, result in (
            await crew_findings(selected, ["radiation_exposure_3_2"])
        ).items():
            publish(sse_event("finding", finding_payload(finding, result)))
    return JsonResponse({"id": await current_environment_id()})


@require_GET
async def health_conditions(_request: HttpRequest) -> JsonResponse:
    """Every finding the latest readings support, for a client without the stream."""
    results = await crew_findings(await current_environment())
    return JsonResponse(
        {
            "findings": [
                finding_payload(finding, result) for finding, result in results.items()
            ]
        }
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
async def readings(request: HttpRequest) -> JsonResponse:
    """GET: reading history per channel. POST: store and push one reading."""
    if request.method == "GET":
        return await reading_history(request)

    payload, error = await _json_body(request)
    if error is not None:
        return error
    scope = request.headers.get("X-Simulation-Scope", "")
    data, errors = parse_reading(payload, scope)
    if data is None:
        return JsonResponse(errors, status=400)

    reading = await Reading.objects.acreate(
        channel=data["channel"],
        value=data["value"],
        measured_at=data["measured_at"],
    )
    environment = await current_environment()
    response = reading_payload(reading, environment)
    publish(sse_event("reading", response))
    affected = await affected_findings(reading.channel, environment)
    for finding, result in affected.items():
        publish(sse_event("finding", finding_payload(finding, result)))
    return JsonResponse(response, status=201)


async def reading_history(request: HttpRequest) -> JsonResponse:
    """Skip channels without readings; grade against the environment in effect."""
    query, errors = parse_history_query(request.GET)
    if query is None:
        return JsonResponse(errors, status=400)

    environment = await current_environment()
    history: dict[str, list[dict[str, object]]] = {}
    for channel in query["channel"] or core.CHANNELS:
        latest = [
            reading
            async for reading in Reading.objects.filter(channel=channel).order_by(
                "-measured_at", "-id"
            )[: query["limit"]]
        ]
        if latest:
            history[channel] = [
                dict(reading_payload(reading, environment))
                for reading in reversed(latest)
            ]
    return JsonResponse({"readings": history})


@csrf_exempt
@require_POST
async def assistant(request: HttpRequest) -> JsonResponse:
    """The LLM's next message, briefed with the live findings and readings."""
    if await is_rate_limited(request):
        return JsonResponse({"detail": "Too many requests."}, status=429)

    payload, error = await _json_body(request)
    if error is not None:
        return error
    messages, errors = parse_chat(payload)
    if messages is None:
        return JsonResponse(errors, status=400)

    try:
        return JsonResponse({"reply": await reply(messages)})
    except AssistantError as error:
        return JsonResponse({"detail": str(error)}, status=503)


@require_GET
async def stream(_request: HttpRequest) -> HttpResponseBase:
    """SSE stream of the dictionary, the snapshot and live telemetry."""
    response = StreamingHttpResponse(events(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


async def _json_body(request: HttpRequest) -> tuple[object, JsonResponse | None]:
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"detail": "Invalid JSON body."}, status=400)
