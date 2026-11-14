import hydrograph_core
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import Reading
from api.serializers import ReadingInSerializer, ReadingOutSerializer, reading_payload


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
    return Response(
        [reading_payload(r) for r in created], status=status.HTTP_201_CREATED
    )
