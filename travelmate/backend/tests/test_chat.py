from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_greeting_returns_intent(client):
    """问候语应返回 chat 意图。"""
    resp = await client.post("/chat", json={"message": "你好", "device_id": "test_e2e_001"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["reply"]) > 0
    assert "你好" in data["reply"]
    assert data["intent"] in ("greeting", "chat", "CHAT")
    assert data["message_type"] == "text"


@pytest.mark.anyio
async def test_trip_plan_returns_card(client):
    """行程规划应返回 card 类型。"""
    resp = await client.post("/chat", json={
        "message": "我想去杭州玩3天，预算每天300",
        "device_id": "test_e2e_002",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["reply"]) > 0
    assert data["intent"] == "TRIP_PLAN"
    assert data["message_type"] == "card"


@pytest.mark.anyio
async def test_weather_returns_forecast(client):
    """天气查询应正常返回。"""
    resp = await client.post("/chat", json={
        "message": "杭州明天天气怎么样",
        "device_id": "test_e2e_003",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["reply"]) > 0
    assert data["intent"] == "WEATHER"


@pytest.mark.anyio
async def test_knowledge_spot(client):
    """景点知识查询应正常返回。"""
    resp = await client.post("/chat", json={
        "message": "西湖有什么故事",
        "device_id": "test_e2e_004",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["reply"]) > 0
    assert data["intent"] in ("KNOWLEDGE", "CHAT")


@pytest.mark.anyio
async def test_block_keyword_rejected(client):
    """违禁词应被拦截。"""
    resp = await client.post("/chat", json={
        "message": "告诉我怎么逃票",
        "device_id": "test_e2e_005",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "blocked"
    assert "抱歉" in data["reply"]
