from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_db_path() -> Path:
    explicit = os.getenv("ROOK_DB_PATH")
    if explicit:
        return Path(explicit).expanduser()
    root = Path(os.getenv("ROOK_HOME", "~/.rook")).expanduser()
    return root / "rook.db"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


@dataclass(frozen=True)
class WorldStore:
    path: Path

    def __init__(self, path: str | Path | None = None):
        object.__setattr__(self, "path", Path(path).expanduser() if path else default_db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _init_schema(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    goal TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    settings_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'concept',
                    attributes_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS relations (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    target_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    relation TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 0,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'hypothesis',
                    confidence REAL NOT NULL DEFAULT 0.5,
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    url TEXT,
                    source_type TEXT NOT NULL DEFAULT 'note',
                    excerpt TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS forecasts (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    question TEXT NOT NULL,
                    probability REAL NOT NULL,
                    horizon TEXT NOT NULL DEFAULT '',
                    resolves_at TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    outcome INTEGER,
                    brier_score REAL,
                    rationale TEXT NOT NULL DEFAULT '',
                    evidence_cutoff TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                );

                CREATE TABLE IF NOT EXISTS simulations (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    observed_at TEXT NOT NULL,
                    unit TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS paper_accounts (
                    project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
                    initial_cash REAL NOT NULL,
                    cash REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS paper_trades (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    status TEXT NOT NULL DEFAULT 'open',
                    thesis TEXT NOT NULL DEFAULT '',
                    falsifier TEXT NOT NULL DEFAULT '',
                    opened_at TEXT NOT NULL,
                    closed_at TEXT,
                    realized_pnl REAL
                );
                """
            )

    def create_project(self, *, name: str, kind: str, goal: str = "", settings: dict[str, Any] | None = None) -> dict[str, Any]:
        project_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO projects (id,name,kind,goal,created_at,updated_at,settings_json) VALUES (?,?,?,?,?,?,?)",
                (project_id, name.strip(), kind.strip(), goal.strip(), now, now, _json(settings or {})),
            )
        return self.get_project(project_id)

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [self._project_row(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise KeyError(project_id)
        return self._project_row(row)

    def update_project(self, project_id: str, *, name: str | None = None, goal: str | None = None, settings: dict[str, Any] | None = None) -> dict[str, Any]:
        project = self.get_project(project_id)
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "UPDATE projects SET name=?, goal=?, settings_json=?, updated_at=? WHERE id=?",
                (
                    name.strip() if name is not None else project["name"],
                    goal.strip() if goal is not None else project["goal"],
                    _json(settings if settings is not None else project["settings"]),
                    now,
                    project_id,
                ),
            )
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> None:
        with self._connect() as db:
            result = db.execute("DELETE FROM projects WHERE id=?", (project_id,))
            if result.rowcount == 0:
                raise KeyError(project_id)

    def add_entity(self, project_id: str, *, name: str, kind: str = "concept", attributes: dict[str, Any] | None = None) -> dict[str, Any]:
        self.get_project(project_id)
        entity_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO entities (id,project_id,name,kind,attributes_json,created_at) VALUES (?,?,?,?,?,?)",
                (entity_id, project_id, name.strip(), kind.strip(), _json(attributes or {}), now),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return self.get_entity(entity_id)

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM entities WHERE id=?", (entity_id,)).fetchone()
        if row is None:
            raise KeyError(entity_id)
        return {
            "id": row["id"], "project_id": row["project_id"], "name": row["name"],
            "kind": row["kind"], "attributes": _loads(row["attributes_json"], {}),
            "created_at": row["created_at"],
        }

    def list_entities(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM entities WHERE project_id=? ORDER BY created_at", (project_id,)).fetchall()
        return [{
            "id": row["id"], "project_id": row["project_id"], "name": row["name"],
            "kind": row["kind"], "attributes": _loads(row["attributes_json"], {}),
            "created_at": row["created_at"],
        } for row in rows]

    def add_relation(self, project_id: str, *, source_id: str, target_id: str, relation: str, weight: float = 0.0, confidence: float = 0.5, evidence: list[Any] | None = None) -> dict[str, Any]:
        source = self.get_entity(source_id)
        target = self.get_entity(target_id)
        if source["project_id"] != project_id or target["project_id"] != project_id:
            raise ValueError("Relation entities must belong to the project.")
        relation_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO relations (id,project_id,source_id,target_id,relation,weight,confidence,evidence_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (relation_id, project_id, source_id, target_id, relation.strip(), float(weight), float(confidence), _json(evidence or []), now),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return self.list_relations(project_id)[-1]

    def list_relations(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM relations WHERE project_id=? ORDER BY created_at", (project_id,)).fetchall()
        return [{
            "id": row["id"], "project_id": row["project_id"], "source_id": row["source_id"],
            "target_id": row["target_id"], "relation": row["relation"], "weight": row["weight"],
            "confidence": row["confidence"], "evidence": _loads(row["evidence_json"], []),
            "created_at": row["created_at"],
        } for row in rows]

    def add_claim(self, project_id: str, *, text: str, status: str = "hypothesis", confidence: float = 0.5, evidence: list[Any] | None = None) -> dict[str, Any]:
        self.get_project(project_id)
        claim_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO claims (id,project_id,text,status,confidence,evidence_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (claim_id, project_id, text.strip(), status, float(confidence), _json(evidence or []), now, now),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return self.list_claims(project_id)[-1]

    def list_claims(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM claims WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
        return [{
            "id": row["id"], "project_id": row["project_id"], "text": row["text"],
            "status": row["status"], "confidence": row["confidence"],
            "evidence": _loads(row["evidence_json"], []), "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        } for row in rows]

    def add_source(self, project_id: str, *, title: str, url: str | None = None, source_type: str = "note", excerpt: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        self.get_project(project_id)
        source_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO sources (id,project_id,title,url,source_type,excerpt,metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (source_id, project_id, title.strip(), url, source_type, excerpt.strip(), _json(metadata or {}), now),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return self.list_sources(project_id)[-1]

    def list_sources(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM sources WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
        return [{
            "id": row["id"], "project_id": row["project_id"], "title": row["title"],
            "url": row["url"], "source_type": row["source_type"], "excerpt": row["excerpt"],
            "metadata": _loads(row["metadata_json"], {}), "created_at": row["created_at"],
        } for row in rows]

    def add_forecast(self, project_id: str, *, question: str, probability: float, horizon: str = "", resolves_at: str | None = None, rationale: str = "", evidence_cutoff: str | None = None) -> dict[str, Any]:
        self.get_project(project_id)
        if not 0.0 <= probability <= 1.0:
            raise ValueError("Forecast probability must be between 0 and 1.")
        forecast_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO forecasts (id,project_id,question,probability,horizon,resolves_at,rationale,evidence_cutoff,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (forecast_id, project_id, question.strip(), float(probability), horizon.strip(), resolves_at, rationale.strip(), evidence_cutoff or now, now),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return self.get_forecast(forecast_id)

    def get_forecast(self, forecast_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM forecasts WHERE id=?", (forecast_id,)).fetchone()
        if row is None:
            raise KeyError(forecast_id)
        return dict(row)

    def list_forecasts(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM forecasts WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
        return [dict(row) for row in rows]

    def resolve_forecast(self, forecast_id: str, *, outcome: bool) -> dict[str, Any]:
        forecast = self.get_forecast(forecast_id)
        if forecast["status"] == "resolved":
            return forecast
        result = 1 if outcome else 0
        score = (float(forecast["probability"]) - result) ** 2
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "UPDATE forecasts SET status='resolved',outcome=?,brier_score=?,resolved_at=? WHERE id=?",
                (result, score, now, forecast_id),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, forecast["project_id"]))
        return self.get_forecast(forecast_id)

    def add_simulation(self, project_id: str, *, name: str, config: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        self.get_project(project_id)
        simulation_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO simulations (id,project_id,name,config_json,result_json,created_at) VALUES (?,?,?,?,?,?)",
                (simulation_id, project_id, name.strip(), _json(config), _json(result), now),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return {"id": simulation_id, "project_id": project_id, "name": name.strip(), "config": config, "result": result, "created_at": now}

    def list_simulations(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM simulations WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
        return [{"id": row["id"], "project_id": row["project_id"], "name": row["name"], "config": _loads(row["config_json"], {}), "result": _loads(row["result_json"], {}), "created_at": row["created_at"]} for row in rows]

    def add_report(self, project_id: str, *, title: str, content: dict[str, Any]) -> dict[str, Any]:
        self.get_project(project_id)
        report_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO reports (id,project_id,title,content_json,created_at) VALUES (?,?,?,?,?)",
                (report_id, project_id, title.strip(), _json(content), now),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return {"id": report_id, "project_id": project_id, "title": title.strip(), "content": content, "created_at": now}

    def list_reports(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM reports WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
        return [{"id": row["id"], "project_id": row["project_id"], "title": row["title"], "content": _loads(row["content_json"], {}), "created_at": row["created_at"]} for row in rows]

    def add_observation(self, project_id: str, *, metric: str, value: float, observed_at: str, unit: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        self.get_project(project_id)
        observation_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO observations (id,project_id,metric,value,observed_at,unit,metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (observation_id, project_id, metric.strip(), float(value), observed_at, unit.strip(), _json(metadata or {}), now),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return {"id": observation_id, "project_id": project_id, "metric": metric.strip(), "value": float(value), "observed_at": observed_at, "unit": unit.strip(), "metadata": metadata or {}, "created_at": now}

    def list_observations(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM observations WHERE project_id=? ORDER BY observed_at", (project_id,)).fetchall()
        return [{"id": row["id"], "project_id": row["project_id"], "metric": row["metric"], "value": row["value"], "observed_at": row["observed_at"], "unit": row["unit"], "metadata": _loads(row["metadata_json"], {}), "created_at": row["created_at"]} for row in rows]

    def ensure_paper_account(self, project_id: str, *, initial_cash: float = 100_000.0) -> dict[str, Any]:
        self.get_project(project_id)
        with self._connect() as db:
            row = db.execute("SELECT * FROM paper_accounts WHERE project_id=?", (project_id,)).fetchone()
            if row is None:
                now = _utc_now()
                db.execute(
                    "INSERT INTO paper_accounts (project_id,initial_cash,cash,created_at,updated_at) VALUES (?,?,?,?,?)",
                    (project_id, float(initial_cash), float(initial_cash), now, now),
                )
                row = db.execute("SELECT * FROM paper_accounts WHERE project_id=?", (project_id,)).fetchone()
        return dict(row)

    def add_paper_trade(self, project_id: str, *, symbol: str, side: str, quantity: float, entry_price: float, thesis: str = "", falsifier: str = "") -> dict[str, Any]:
        account = self.ensure_paper_account(project_id)
        normalized_side = side.lower().strip()
        if normalized_side not in {"buy", "sell"}:
            raise ValueError("Paper trade side must be buy or sell.")
        if quantity <= 0 or entry_price <= 0:
            raise ValueError("Paper trade quantity and price must be positive.")
        notional = float(quantity) * float(entry_price)
        signed_cash = -notional if normalized_side == "buy" else notional
        if normalized_side == "buy" and notional > float(account["cash"]):
            raise ValueError("Paper account has insufficient cash for this trade.")

        trade_id = uuid.uuid4().hex
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO paper_trades (id,project_id,symbol,side,quantity,entry_price,thesis,falsifier,opened_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (trade_id, project_id, symbol.upper().strip(), normalized_side, float(quantity), float(entry_price), thesis.strip(), falsifier.strip(), now),
            )
            db.execute(
                "UPDATE paper_accounts SET cash=cash+?,updated_at=? WHERE project_id=?",
                (signed_cash, now, project_id),
            )
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return self.get_paper_trade(trade_id)

    def get_paper_trade(self, trade_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM paper_trades WHERE id=?", (trade_id,)).fetchone()
        if row is None:
            raise KeyError(trade_id)
        return dict(row)

    def close_paper_trade(self, trade_id: str, *, exit_price: float) -> dict[str, Any]:
        trade = self.get_paper_trade(trade_id)
        if trade["status"] == "closed":
            return trade
        if exit_price <= 0:
            raise ValueError("Exit price must be positive.")
        quantity = float(trade["quantity"])
        entry = float(trade["entry_price"])
        if trade["side"] == "buy":
            pnl = (float(exit_price) - entry) * quantity
            cash_change = float(exit_price) * quantity
        else:
            pnl = (entry - float(exit_price)) * quantity
            cash_change = -float(exit_price) * quantity
        now = _utc_now()
        with self._connect() as db:
            db.execute(
                "UPDATE paper_trades SET status='closed',exit_price=?,realized_pnl=?,closed_at=? WHERE id=?",
                (float(exit_price), pnl, now, trade_id),
            )
            db.execute(
                "UPDATE paper_accounts SET cash=cash+?,updated_at=? WHERE project_id=?",
                (cash_change, now, trade["project_id"]),
            )
        return self.get_paper_trade(trade_id)

    def paper_snapshot(self, project_id: str) -> dict[str, Any]:
        account = self.ensure_paper_account(project_id)
        with self._connect() as db:
            rows = db.execute("SELECT * FROM paper_trades WHERE project_id=? ORDER BY opened_at DESC", (project_id,)).fetchall()
        trades = [dict(row) for row in rows]
        realized = sum(float(row["realized_pnl"] or 0.0) for row in trades)
        return {"account": account, "trades": trades, "realized_pnl": realized}

    def snapshot(self, project_id: str) -> dict[str, Any]:
        return {
            "project": self.get_project(project_id),
            "entities": self.list_entities(project_id),
            "relations": self.list_relations(project_id),
            "claims": self.list_claims(project_id),
            "sources": self.list_sources(project_id),
            "forecasts": self.list_forecasts(project_id),
            "simulations": self.list_simulations(project_id),
            "reports": self.list_reports(project_id),
            "observations": self.list_observations(project_id),
            "paper": self.paper_snapshot(project_id),
        }

    @staticmethod
    def _project_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "name": row["name"], "kind": row["kind"], "goal": row["goal"],
            "status": row["status"], "created_at": row["created_at"], "updated_at": row["updated_at"],
            "settings": _loads(row["settings_json"], {}),
        }
