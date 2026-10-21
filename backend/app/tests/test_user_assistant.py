import json
import uuid
import httpx
import pytest
from httpx import AsyncClient

from app.core.config import settings


async def _new_user(client: AsyncClient) -> dict:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"ua_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Assistant User", "password": "password123"},
    )
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


async def _titles(client: AsyncClient, headers: dict) -> list:
    res = await client.get("/api/v1/tasks", params={"page_size": 100}, headers=headers)
    return [t["title"] for t in res.json()["items"]]


@pytest.mark.asyncio
async def test_builtin_engine_adds_every_task_from_a_multiline_message(client: AsyncClient):
    headers = await _new_user(client)
    res = await client.post(
        "/api/v1/chat/message",
        json={"content": "Create task\nApp building\nFASTTAPI research\nAgentic AI study"},
        headers=headers,
    )
    assert res.json()["tools_executed"].count("create_my_task") == 3
    assert sorted(await _titles(client, headers)) == ["Agentic AI study", "App building", "FASTTAPI research"]


def _fake_llm(monkeypatch, replies: list, sent: list):
    """Stand-in for Gemini's OpenAI-compatible endpoint: returns `replies` in order."""
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    real_post = httpx.AsyncClient.post

    async def fake_post(self, url, *args, json=None, **kwargs):
        if not str(url).startswith(settings.OPENAI_BASE_URL):  # the test client's own calls to the app
            return await real_post(self, url, *args, json=json, **kwargs)
        sent.append(json)
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, httpx.Response):
            return reply
        return httpx.Response(200, json={"choices": [{"message": reply}]})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)


def _tool_call(i: int, title: str) -> dict:
    return {"id": f"call_{i}", "type": "function",
            "function": {"name": "create_my_task", "arguments": json.dumps({"title": title})}}


@pytest.mark.asyncio
async def test_llm_adds_several_tasks_and_prompt_hides_system_data(client: AsyncClient, monkeypatch):
    headers = await _new_user(client)
    sent: list = []
    _fake_llm(monkeypatch, [
        {"role": "assistant", "content": None, "tool_calls": [_tool_call(1, "Write CV"), _tool_call(2, "Book dentist")]},
        {"role": "assistant", "content": "Added both tasks."},
    ], sent)

    res = await client.post("/api/v1/chat/message", json={"content": "add write CV and book dentist"}, headers=headers)
    assert res.json()["assistant_message"]["content"] == "Added both tasks."
    assert sorted(await _titles(client, headers)) == ["Book dentist", "Write CV"]

    system_prompt = sent[0]["messages"][0]["content"]
    assert "System Overview" not in system_prompt  # no user counts for regular users
    assert all(t["function"]["name"].startswith(("list_my", "search_my", "get_my", "create_my", "update_my"))
               for t in sent[0]["tools"])  # no admin tools offered


@pytest.mark.asyncio
async def test_llm_overloaded_once_is_retried(client: AsyncClient, monkeypatch):
    headers = await _new_user(client)
    _fake_llm(monkeypatch, [
        httpx.Response(503, json={"error": {"code": 503, "message": "high demand"}}),
        {"role": "assistant", "content": "GraphQL uses one endpoint."},
    ], [])

    res = await client.post("/api/v1/chat/message", json={"content": "REST vs GraphQL?"}, headers=headers)
    assert res.json()["assistant_message"]["content"] == "GraphQL uses one endpoint."


@pytest.mark.asyncio
async def test_llm_failure_after_tools_does_not_create_tasks_twice(client: AsyncClient, monkeypatch):
    headers = await _new_user(client)
    _fake_llm(monkeypatch, [
        {"role": "assistant", "content": None, "tool_calls": [_tool_call(1, "Create task Only once")]},
        httpx.ReadTimeout("synthesis timed out"),
    ], [])

    res = await client.post("/api/v1/chat/message", json={"content": "Create task Only once"}, headers=headers)
    assert res.status_code == 200
    assert "created successfully" in res.json()["assistant_message"]["content"]
    assert len(await _titles(client, headers)) == 1
