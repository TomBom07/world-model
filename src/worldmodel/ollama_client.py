from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}


class OllamaUnavailable(RuntimeError):
    pass


def ollama_base_url() -> str:
    raw = os.getenv("ROOK_OLLAMA_URL", DEFAULT_OLLAMA_URL).strip().rstrip("/")
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urlparse(raw)
    if parsed.scheme != "http" or parsed.hostname not in _ALLOWED_HOSTS:
        raise OllamaUnavailable(
            "ROOK_OLLAMA_URL must point to local Ollama on localhost/127.0.0.1."
        )
    return raw


def _request_json(
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 1.2,
) -> dict[str, Any]:
    base = ollama_base_url()
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{base}{path}",
        data=body,
        method="GET" if body is None else "POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - loopback URL only
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise OllamaUnavailable(f"Ollama returned HTTP {error.code}: {detail[:300]}") from error
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise OllamaUnavailable(f"Could not reach local Ollama at {base}: {error}") from error


def list_models() -> list[dict[str, Any]]:
    payload = _request_json("/api/tags", timeout=1.0)
    models: list[dict[str, Any]] = []
    for item in payload.get("models", []):
        name = str(item.get("name") or item.get("model") or "").strip()
        if not name:
            continue
        details = item.get("details") or {}
        models.append(
            {
                "name": name,
                "size": int(item.get("size") or 0),
                "parameter_size": str(details.get("parameter_size") or ""),
                "quantization": str(details.get("quantization_level") or ""),
                "family": str(details.get("family") or ""),
            }
        )
    return models


def status() -> dict[str, Any]:
    try:
        models = list_models()
    except OllamaUnavailable as error:
        return {
            "available": False,
            "base_url": DEFAULT_OLLAMA_URL,
            "models": [],
            "error": str(error),
        }

    return {
        "available": True,
        "base_url": ollama_base_url(),
        "models": models,
        "error": None,
    }


def _system_prompt(*, context: str, evidence: dict[str, Any], engine_hint: str | None) -> str:
    serialized = json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
    hint = (engine_hint or "").strip()
    return f"""You are Rook, a local scientific reasoning copilot running through Ollama.

Your job is to reason conversationally ABOUT the evidence produced by Rook's scientific engine. The engine evidence below is the source of truth. Do not invent measurements, experiments, equations, probabilities, model scores, dataset facts, or causal conclusions that are not supported by it.

Rules:
- Clearly separate observation, prediction, hypothesis, mechanism, and causality.
- A good fit or holdout score is not proof of causality.
- In synthetic Market/Physics/Discovery worlds, do not generalize the result into a claim about the real world.
- Never turn market research outputs into investment advice or claim live alpha.
- If the evidence is insufficient, say exactly what is missing and propose a test or additional data.
- You may propose new hypotheses creatively, but label them as hypotheses and explain how they could be falsified.
- Prefer concise, clear prose over jargon. Use equations only when they materially help.
- Never claim that you executed a new experiment unless the supplied evidence says it was executed.
- If the engine hint conflicts with the evidence JSON, trust the evidence JSON.

Current Rook context: {context}

ENGINE EVIDENCE (JSON):
{serialized}

ENGINE INTERPRETER HINT:
{hint if hint else "No deterministic interpreter hint was supplied."}
"""


def chat(
    *,
    model: str,
    context: str,
    evidence: dict[str, Any],
    messages: list[dict[str, str]],
    engine_hint: str | None = None,
) -> dict[str, Any]:
    installed = {item["name"] for item in list_models()}
    if not installed:
        raise OllamaUnavailable("Ollama is running but no local models are installed.")
    if model not in installed:
        raise OllamaUnavailable(f"Model {model!r} is not installed in local Ollama.")

    clean_messages: list[dict[str, str]] = []
    for message in messages[-16:]:
        role = message.get("role")
        content = str(message.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        clean_messages.append({"role": role, "content": content[:8000]})

    payload = {
        "model": model,
        "stream": False,
        "keep_alive": "10m",
        "messages": [
            {
                "role": "system",
                "content": _system_prompt(
                    context=context,
                    evidence=evidence,
                    engine_hint=engine_hint,
                ),
            },
            *clean_messages,
        ],
        "options": {
            "temperature": 0.25,
        },
    }
    response = _request_json("/api/chat", payload=payload, timeout=180.0)
    message = response.get("message") or {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise OllamaUnavailable("Ollama returned an empty chat response.")

    return {
        "content": content,
        "model": str(response.get("model") or model),
        "done": bool(response.get("done", True)),
        "total_duration": int(response.get("total_duration") or 0),
        "eval_count": int(response.get("eval_count") or 0),
    }
