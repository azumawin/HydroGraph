import json
import urllib.request
from typing import Self, cast

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from api.assistant import is_blocked_model
from api.models import Reading

QUESTION = {"messages": [{"role": "user", "content": "How is the crew member?"}]}


@pytest.fixture(autouse=True)
def fresh_throttle() -> None:
    """The throttle counts live in the cache; each test starts with none."""
    cache.clear()


class FakeResponse:
    body: bytes

    def __init__(self, body: dict[str, object]) -> None:
        self.body = json.dumps(body).encode()

    def read(self, *_: object) -> bytes:
        return self.body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        pass


@pytest.mark.django_db
@override_settings(OLLAMA_API_KEY="test-key", OLLAMA_MODEL="gpt-oss:120b")
def test_reply_is_briefed_with_the_live_readings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = Reading.objects.create(
        channel="heart_rate", value=1.7, measured_at="2026-11-14T08:00:00Z"
    )
    sent: list[dict[str, object]] = []

    def urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        assert timeout > 0
        sent.append(cast("dict[str, object]", json.loads(cast("bytes", request.data))))
        return FakeResponse({"message": {"role": "assistant", "content": " Rest. "}})

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    response = APIClient().post(reverse("assistant"), QUESTION, format="json")

    assert response.status_code == 200
    assert response.json() == {"reply": "Rest."}
    messages = cast("list[dict[str, str]]", sent[0]["messages"])
    assert messages[0]["role"] == "system"
    assert '"heart_rate"' in messages[0]["content"]
    assert messages[1:] == QUESTION["messages"]


@pytest.mark.django_db
@override_settings(OLLAMA_API_KEY="")
def test_missing_key_is_503() -> None:
    response = APIClient().post(reverse("assistant"), QUESTION, format="json")
    assert response.status_code == 503


@pytest.mark.django_db
@override_settings(OLLAMA_API_KEY="test-key", OLLAMA_MODEL="deepseek-v4.1-flash")
def test_blocked_model_is_503() -> None:
    response = APIClient().post(reverse("assistant"), QUESTION, format="json")
    assert response.status_code == 503
    assert "not allowed" in response.json()["detail"]


def test_blocked_models() -> None:
    assert is_blocked_model("qwen3:235b")
    assert is_blocked_model("moonshotai/kimi-k2")
    assert not is_blocked_model("gpt-oss:120b")
    assert not is_blocked_model("mistral-large-4")


@pytest.mark.django_db
def test_empty_conversation_is_400() -> None:
    response = APIClient().post(reverse("assistant"), {"messages": []}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
@override_settings(OLLAMA_API_KEY="test-key", OLLAMA_MODEL="gpt-oss:120b")
def test_eleventh_request_in_a_minute_is_429(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[urllib.request.Request] = []

    def urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        assert timeout > 0
        calls.append(request)
        return FakeResponse({"message": {"role": "assistant", "content": "Rest."}})

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    client = APIClient()

    statuses = [
        client.post(reverse("assistant"), QUESTION, format="json").status_code
        for _ in range(11)
    ]

    assert statuses == [200] * 10 + [429]
    assert len(calls) == 10
