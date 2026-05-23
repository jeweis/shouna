import base64
import json

import pytest

from app.core import ai_client
from app.core.ai_client import AnthropicCompatibleClient, OpenAICompatibleClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    requests = []
    response_payload = {}

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, url, headers=None, json=None):
        self.requests.append({"url": url, "headers": headers, "json": json})
        return FakeResponse(self.response_payload)


@pytest.fixture(autouse=True)
def reset_fake_client(monkeypatch):
    FakeAsyncClient.requests = []
    monkeypatch.setattr(ai_client.httpx, "AsyncClient", FakeAsyncClient)


@pytest.mark.asyncio
async def test_openai_client_builds_vision_payload_and_parses_result():
    FakeAsyncClient.response_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "name": "灰色针织衫",
                            "description": "灰色厚针织材质，适合冬季保暖",
                            "suggested_location": "衣柜",
                            "tags": ["衣服", "针织衫", "灰色"],
                            "confidence": 0.92,
                        }
                    )
                }
            }
        ]
    }
    image_bytes = b"fake image bytes"

    result = await OpenAICompatibleClient(
        api_key="openai-key",
        base_url="https://openai.example/v1/",
        model="gpt-4o-mini",
    ).analyze_image(image_bytes)

    assert result is not None
    assert result.name == "灰色针织衫"
    assert result.description == "灰色厚针织材质，适合冬季保暖"
    assert result.suggested_location == "衣柜"
    assert result.tags == ["衣服", "针织衫", "灰色"]
    assert result.confidence == 0.92

    request = FakeAsyncClient.requests[0]
    assert request["url"] == "https://openai.example/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer openai-key"
    assert request["json"]["model"] == "gpt-4o-mini"
    assert request["json"]["response_format"] == {"type": "json_object"}
    content = request["json"]["messages"][0]["content"]
    assert "description" in content[0]["text"]
    expected_data_uri = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("utf-8")
    assert content[1]["image_url"]["url"] == expected_data_uri


@pytest.mark.asyncio
async def test_anthropic_client_builds_vision_payload_and_parses_result():
    FakeAsyncClient.response_payload = {
        "content": [
            {
                "text": json.dumps(
                    {
                        "name": "蓝色保温杯",
                        "description": "蓝色金属杯身，适合日常饮水",
                        "suggested_location": "厨房台面",
                        "tags": ["杯子", "蓝色", "金属"],
                        "confidence": 0.88,
                    }
                )
            }
        ]
    }
    image_bytes = b"anthropic image bytes"

    result = await AnthropicCompatibleClient(
        api_key="anthropic-key",
        base_url="https://anthropic.example/v1/",
        model="claude-3-5-sonnet-latest",
    ).analyze_image(image_bytes)

    assert result is not None
    assert result.name == "蓝色保温杯"
    assert result.description == "蓝色金属杯身，适合日常饮水"
    assert result.suggested_location == "厨房台面"
    assert result.tags == ["杯子", "蓝色", "金属"]
    assert result.confidence == 0.88

    request = FakeAsyncClient.requests[0]
    assert request["url"] == "https://anthropic.example/v1/messages"
    assert request["headers"]["x-api-key"] == "anthropic-key"
    assert request["headers"]["anthropic-version"] == "2023-06-01"
    assert request["json"]["model"] == "claude-3-5-sonnet-latest"
    content = request["json"]["messages"][0]["content"]
    assert content[0]["type"] == "image"
    assert content[0]["source"] == {
        "type": "base64",
        "media_type": "image/jpeg",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }
    assert content[1]["type"] == "text"
    assert "description" in content[1]["text"]
