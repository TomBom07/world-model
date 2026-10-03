from __future__ import annotations

import json
import re
from typing import Any

from .ollama_client import chat as ollama_chat


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?s*([sS]*?)```", cleaned, flags=re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Local AI did not return a JSON world plan.")

    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as error:
        raise ValueError(f"Local AI returned invalid JSON: {error}") from error

    if not isinstance(value, dict):
        raise ValueError("Local AI world plan must be a JSON object.")
    return value


def propose_world_plan(
    *,
    model: str,
    project: dict[str, Any],
    sources: list[dict[str, Any]],
    existing_entities: list[dict[str, Any]],
    brief: str = "",
) -> dict[str, Any]:
    evidence = {
        "project": project,
        "sources": sources[:20],
        "existing_entities": existing_entities[:30],
    }

    prompt = f"""Build an initial editable Rook world model for this project.

Project goal:
{project.get("goal") or "No explicit goal supplied."}

Additional user brief:
{brief or "None."}

Return JSON only, with exactly this shape:
{{
  "entities": [
    {{"name":"...", "kind":"company|person|metric|event|policy|technology|concept", "value":0.0}}
  ],
  "relations": [
    {{"source":"entity name", "target":"entity name", "relation":"short verb phrase", "weight":0.5, "confidence":0.5}}
  ],
  "claims": [
    {{"text":"...", "status":"hypothesis", "confidence":0.5}}
  ],
  "forecasts": [
    {{"question":"binary, resolvable future claim", "probability":0.5, "horizon":"...", "rationale":"..."}}
  ]
}}

Rules:
- Maximum 16 entities, 24 relations, 10 claims, 8 forecasts.
- Do not pretend facts are known when they are not in the supplied evidence.
- Claims should be competing explanations or testable hypotheses.
- Forecasts must be binary enough to resolve later and probabilities must be between 0 and 1.
- Relationship weights are sensitivity assumptions, not causal truth. Use modest magnitudes, normally between -1 and 1.
- If evidence is sparse, prefer explicit hypotheses over fabricated factual detail.
- Do not include markdown outside the JSON.
"""

    response = ollama_chat(
        model=model,
        context="world_builder",
        evidence=evidence,
        messages=[{"role": "user", "content": prompt}],
        engine_hint="Create a compact editable world structure; do not invent unsupported evidence.",
    )
    plan = extract_json_object(response["content"])
    plan["_model"] = response["model"]
    return plan


def normalize_world_plan(plan: dict[str, Any]) -> dict[str, Any]:
    raw_entities = plan.get("entities") if isinstance(plan.get("entities"), list) else []
    raw_relations = plan.get("relations") if isinstance(plan.get("relations"), list) else []
    raw_claims = plan.get("claims") if isinstance(plan.get("claims"), list) else []
    raw_forecasts = plan.get("forecasts") if isinstance(plan.get("forecasts"), list) else []

    entities = []
    seen = set()
    for item in raw_entities[:16]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        try:
            value = float(item.get("value") or 0.0)
        except (TypeError, ValueError):
            value = 0.0
        entities.append(
            {
                "name": name[:160],
                "kind": str(item.get("kind") or "concept")[:60],
                "value": value,
            }
        )

    valid_names = {item["name"].lower(): item["name"] for item in entities}

    relations = []
    for item in raw_relations[:24]:
        if not isinstance(item, dict):
            continue
        source = valid_names.get(str(item.get("source") or "").strip().lower())
        target = valid_names.get(str(item.get("target") or "").strip().lower())
        if not source or not target or source == target:
            continue
        try:
            weight = max(-5.0, min(5.0, float(item.get("weight", 0.0))))
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            continue
        relations.append(
            {
                "source": source,
                "target": target,
                "relation": str(item.get("relation") or "influences")[:160],
                "weight": weight,
                "confidence": confidence,
            }
        )

    claims = []
    for item in raw_claims[:10]:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        claims.append(
            {
                "text": text[:4000],
                "status": str(item.get("status") or "hypothesis")[:40],
                "confidence": confidence,
            }
        )

    forecasts = []
    for item in raw_forecasts[:8]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        try:
            probability = max(0.0, min(1.0, float(item.get("probability", 0.5))))
        except (TypeError, ValueError):
            probability = 0.5
        forecasts.append(
            {
                "question": question[:4000],
                "probability": probability,
                "horizon": str(item.get("horizon") or "")[:160],
                "rationale": str(item.get("rationale") or "")[:10_000],
            }
        )

    return {
        "entities": entities,
        "relations": relations,
        "claims": claims,
        "forecasts": forecasts,
        "model": str(plan.get("_model") or ""),
    }
