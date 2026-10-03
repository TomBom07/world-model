from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import numpy as np


def forecast_calibration(forecasts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    resolved = [item for item in forecasts if item.get("status") == "resolved" and item.get("outcome") in {0, 1}]
    if not resolved:
        return {
            "resolved": 0,
            "mean_brier_score": None,
            "accuracy_at_50": None,
            "buckets": [],
        }

    briers = [
        float(item.get("brier_score"))
        if item.get("brier_score") is not None
        else (float(item["probability"]) - int(item["outcome"])) ** 2
        for item in resolved
    ]
    accuracy = np.mean([
        int((float(item["probability"]) >= 0.5) == bool(item["outcome"]))
        for item in resolved
    ])

    buckets = []
    for lower in np.arange(0.0, 1.0, 0.2):
        upper = min(1.0, lower + 0.2)
        items = [
            item for item in resolved
            if lower <= float(item["probability"]) <= upper
            and (upper == 1.0 or float(item["probability"]) < upper)
        ]
        if not items:
            continue
        buckets.append(
            {
                "range": [round(float(lower), 2), round(float(upper), 2)],
                "count": len(items),
                "mean_probability": float(np.mean([float(item["probability"]) for item in items])),
                "observed_frequency": float(np.mean([int(item["outcome"]) for item in items])),
            }
        )

    return {
        "resolved": len(resolved),
        "mean_brier_score": float(np.mean(briers)),
        "accuracy_at_50": float(accuracy),
        "buckets": buckets,
    }


def simulate_world(
    *,
    entities: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    shocks: dict[str, float],
    runs: int = 2000,
    steps: int = 4,
    noise: float = 0.04,
    seed: int = 7,
) -> dict[str, Any]:
    if not entities:
        raise ValueError("Add at least one entity before running a simulation.")
    if not 100 <= runs <= 20_000:
        raise ValueError("Simulation runs must be between 100 and 20,000.")
    if not 1 <= steps <= 12:
        raise ValueError("Simulation steps must be between 1 and 12.")
    if not 0.0 <= noise <= 0.5:
        raise ValueError("Simulation noise must be between 0 and 0.5.")

    ids = [item["id"] for item in entities]
    names = [item["name"] for item in entities]
    index = {entity_id: i for i, entity_id in enumerate(ids)}
    name_index = {name.lower(): i for i, name in enumerate(names)}

    baseline = np.asarray(
        [float((item.get("attributes") or {}).get("value", 0.0)) for item in entities],
        dtype=float,
    )

    relation_rows: list[tuple[int, int, float]] = []
    for relation in relations:
        if relation["source_id"] not in index or relation["target_id"] not in index:
            continue
        effective = float(relation.get("weight", 0.0)) * float(relation.get("confidence", 0.5))
        relation_rows.append((index[relation["source_id"]], index[relation["target_id"]], effective))

    shock_vector = np.zeros(len(entities), dtype=float)
    applied: dict[str, float] = {}
    for key, delta in shocks.items():
        idx = index.get(key)
        if idx is None:
            idx = name_index.get(str(key).lower())
        if idx is None:
            raise ValueError(f"Unknown shocked entity: {key}")
        shock_vector[idx] += float(delta)
        applied[names[idx]] = applied.get(names[idx], 0.0) + float(delta)

    rng = np.random.default_rng(seed)
    outcomes = np.empty((runs, len(entities)), dtype=float)

    for run in range(runs):
        state = baseline + shock_vector
        for _ in range(steps):
            propagated = np.zeros(len(entities), dtype=float)
            for source_idx, target_idx, effective in relation_rows:
                propagated[target_idx] += state[source_idx] * effective
            stochastic = rng.normal(0.0, noise, size=len(entities))
            state = baseline + shock_vector + propagated + stochastic
            state = np.clip(state, -1e6, 1e6)
        outcomes[run] = state

    rows = []
    for i, entity in enumerate(entities):
        values = outcomes[:, i]
        rows.append(
            {
                "id": entity["id"],
                "name": entity["name"],
                "kind": entity.get("kind", "concept"),
                "baseline": float(baseline[i]),
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "p05": float(np.quantile(values, 0.05)),
                "p50": float(np.quantile(values, 0.50)),
                "p95": float(np.quantile(values, 0.95)),
                "mean_change": float(np.mean(values) - baseline[i]),
            }
        )

    rows.sort(key=lambda item: abs(float(item["mean_change"])), reverse=True)
    return {
        "engine": "weighted_graph_monte_carlo_v1",
        "runs": runs,
        "steps": steps,
        "noise": noise,
        "seed": seed,
        "shocks": applied,
        "outcomes": rows,
        "boundary": (
            "This scenario propagates user-specified shocks through the stored weighted world graph. "
            "It is a structural sensitivity simulation, not a calibrated forecast unless the graph weights "
            "and uncertainty have been empirically validated."
        ),
    }


def business_summary(observations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        grouped[str(row["metric"])].append(row)

    metrics = []
    for metric, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: str(item["observed_at"]))
        values = np.asarray([float(item["value"]) for item in ordered], dtype=float)
        latest = float(values[-1])
        previous = float(values[-2]) if len(values) >= 2 else None
        delta = None if previous is None else latest - previous
        pct_change = None if previous in {None, 0.0} else delta / abs(previous)
        if len(values) >= 2:
            x = np.arange(len(values), dtype=float)
            slope = float(np.polyfit(x, values, 1)[0])
        else:
            slope = 0.0

        metrics.append(
            {
                "metric": metric,
                "unit": ordered[-1].get("unit", ""),
                "latest": latest,
                "previous": previous,
                "change": delta,
                "pct_change": pct_change,
                "trend_per_observation": slope,
                "observations": len(values),
                "last_observed_at": ordered[-1]["observed_at"],
            }
        )

    metrics.sort(key=lambda item: item["metric"].lower())
    return {"metrics": metrics, "metric_count": len(metrics)}


def world_health(snapshot: dict[str, Any]) -> dict[str, Any]:
    entities = snapshot.get("entities", [])
    relations = snapshot.get("relations", [])
    claims = snapshot.get("claims", [])
    sources = snapshot.get("sources", [])
    forecasts = snapshot.get("forecasts", [])

    unresolved_claims = sum(1 for item in claims if item.get("status") in {"hypothesis", "uncertain"})
    open_forecasts = sum(1 for item in forecasts if item.get("status") == "open")

    evidence_density = 0.0
    if claims:
        evidence_density = float(np.mean([len(item.get("evidence") or []) for item in claims]))

    graph_density = 0.0
    if len(entities) > 1:
        graph_density = len(relations) / (len(entities) * (len(entities) - 1))

    return {
        "entities": len(entities),
        "relations": len(relations),
        "claims": len(claims),
        "sources": len(sources),
        "open_forecasts": open_forecasts,
        "unresolved_claims": unresolved_claims,
        "mean_claim_evidence_count": evidence_density,
        "graph_density": float(graph_density),
        "forecast_calibration": forecast_calibration(forecasts),
    }


def build_living_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    project = snapshot["project"]
    claims = snapshot.get("claims", [])
    forecasts = snapshot.get("forecasts", [])
    simulations = snapshot.get("simulations", [])
    sources = snapshot.get("sources", [])
    observations = snapshot.get("observations", [])

    supported = sorted(claims, key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
    open_forecasts = [item for item in forecasts if item.get("status") == "open"]
    resolved_forecasts = [item for item in forecasts if item.get("status") == "resolved"]

    executive = (
        f"{project['name']} currently contains {len(snapshot.get('entities', []))} entities, "
        f"{len(snapshot.get('relations', []))} modeled relationships, {len(claims)} explicit claims, "
        f"and {len(open_forecasts)} outstanding forecasts."
    )
    if supported:
        executive += f" The highest-confidence stored claim is: {supported[0]['text']}"

    return {
        "project": {
            "name": project["name"],
            "kind": project["kind"],
            "goal": project["goal"],
            "updated_at": project["updated_at"],
        },
        "executive_summary": executive,
        "world_state": {
            "health": world_health(snapshot),
            "entities": snapshot.get("entities", []),
            "relations": snapshot.get("relations", []),
        },
        "competing_claims": supported[:12],
        "forecasts": {
            "open": open_forecasts[:20],
            "resolved": resolved_forecasts[:20],
            "calibration": forecast_calibration(forecasts),
        },
        "recent_simulations": simulations[:8],
        "business": business_summary(observations),
        "paper_trading": snapshot.get("paper", {}),
        "evidence": sources[:30],
        "limitations": [
            "Stored graph relations are assumptions unless separately validated by evidence.",
            "Scenario simulation is sensitivity analysis unless parameters have been calibrated prospectively.",
            "Forecast quality should be judged from resolved predictions and calibration, not narrative confidence.",
            "Paper trades are simulated records and do not imply real-world profitability.",
        ],
    }
