from __future__ import annotations

import pytest

from worldmodel import ollama_client


def test_ollama_status_lists_local_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ollama_client,
        "_request_json",
        lambda path, **kwargs: {
            "models": [
                {
                    "name": "qwen3:8b",
                    "size": 5_000_000_000,
                    "details": {
                        "parameter_size": "8B",
                        "quantization_level": "Q4_K_M",
                        "family": "qwen3",
                    },
                }
            ]
        },
    )

    result = ollama_client.status()

    assert result["available"] is True
    assert result["models"][0]["name"] == "qwen3:8b"
    assert result["models"][0]["parameter_size"] == "8B"


def test_ollama_chat_includes_engine_evidence_and_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_request(path: str, **kwargs):
        if path == "/api/tags":
            return {"models": [{"name": "qwen3:8b", "details": {}}]}
        assert path == "/api/chat"
        seen["payload"] = kwargs["payload"]
        return {
            "model": "qwen3:8b",
            "message": {"role": "assistant", "content": "The evidence supports a predictive relationship."},
            "done": True,
            "eval_count": 42,
        }

    monkeypatch.setattr(ollama_client, "_request_json", fake_request)

    result = ollama_client.chat(
        model="qwen3:8b",
        context="custom",
        evidence={"holdout_r2": 0.91, "causal": False},
        messages=[{"role": "user", "content": "What did you find?"}],
        engine_hint="The holdout score is strong, but this is not causal proof.",
    )

    payload = seen["payload"]
    assert isinstance(payload, dict)
    system = payload["messages"][0]["content"]
    assert '"holdout_r2":0.91' in system
    assert "not causal proof" in system
    assert payload["stream"] is False
    assert result["model"] == "qwen3:8b"
    assert "predictive relationship" in result["content"]


def test_ollama_rejects_non_loopback_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROOK_OLLAMA_URL", "http://example.com:11434")

    with pytest.raises(ollama_client.OllamaUnavailable):
        ollama_client.ollama_base_url()
