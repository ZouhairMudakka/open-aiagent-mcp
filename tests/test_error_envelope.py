import pytest
from fastapi.testclient import TestClient

from src.app import app, agent

client = TestClient(app)


def _ws_send_recv(payload):
    with client.websocket_connect("/ws") as ws:
        ws.send_json(payload)
        first = ws.receive_json()
        # Consume any trailing done message to close cleanly
        try:
            second = ws.receive_json()
        except Exception:
            second = None
        return first, second


def test_missing_prompt_envelope():
    first, second = _ws_send_recv({})
    assert first["type"] == "error"
    assert "Prompt missing" in first["message"]
    assert second is None or second["type"] == "done"


def test_agent_exception_envelope(monkeypatch):
    # Force agent.chat to raise
    def boom(prompt: str):
        raise RuntimeError("forced_agent_error")

    monkeypatch.setattr(agent, "chat", boom)
    first, second = _ws_send_recv({"prompt": "hello"})
    assert first["type"] == "error"
    assert "forced_agent_error" in first["message"]
    assert second["type"] == "done" 