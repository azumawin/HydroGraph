from django.urls import path

from api import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("environments/", views.environments, name="environments"),
    path("environment/", views.environment, name="environment"),
    path("health-conditions/", views.health_conditions, name="health-conditions"),
    path("readings/", views.readings, name="readings"),
    path("assistant/", views.assistant, name="assistant"),
    path("rules/", views.rules, name="rules"),
    path("rules/<str:rule_id>/", views.rule, name="rule"),
    path("stream/", views.stream, name="stream"),
]
