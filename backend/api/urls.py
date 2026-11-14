from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()
# router.register("nodes", views.NodeViewSet, basename="node")

urlpatterns = [
    path("health/", views.health, name="health"),
    path("readings/", views.readings, name="readings"),
    path("stream/", views.stream, name="stream"),
    path("", include(router.urls)),
]
