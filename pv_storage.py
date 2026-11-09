"""SQLite persistence helpers for the PV Case Lab training simulator.

This is a demonstration data layer, not a validated safety database.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("PV_CASELAB_DATA_DIR", APP_ROOT / "data")).expanduser()
DB_PATH = DATA_DIR / "pv_caselab.sqlite3"
DOCUMENT_DIR = DATA_DIR / "documents"

STAGES = [
    "Case Intake",
    "Triage",
    "Data Entry",
    "Quality Control Review",
    "Medical Review",
    "Submission",
    "Completed",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db() -> None:
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            wwuid TEXT UNIQUE,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            assigned_user TEXT NOT NULL DEFAULT '',
            due_date TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            data_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_cases_stage ON cases(stage);
        CREATE INDEX IF NOT EXISTS idx_cases_updated ON cases(updated_at);

        CREATE TABLE IF NOT EXISTS workflow_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL REFERENCES cases(case_id),
            from_stage TEXT NOT NULL,
            to_stage TEXT NOT NULL,
            action TEXT NOT NULL,
            comments TEXT NOT NULL DEFAULT '',
            user_name TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL,
            user_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            previous_value TEXT NOT NULL DEFAULT '',
            new_value TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_logs(case_id);

        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(case_id),
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            content_type TEXT NOT NULL,
            current_version INTEGER NOT NULL,
            review_status TEXT NOT NULL DEFAULT 'Pending review',
            description TEXT NOT NULL DEFAULT '',
            date_received TEXT NOT NULL DEFAULT '',
            document_date TEXT NOT NULL DEFAULT '',
            uploaded_by TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS document_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL REFERENCES documents(document_id),
            version INTEGER NOT NULL,
            stored_path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            uploaded_by TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            UNIQUE(document_id, version)
        );
        CREATE TABLE IF NOT EXISTS review_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL REFERENCES cases(case_id),
            review_type TEXT NOT NULL,
            decision TEXT NOT NULL,
            comments TEXT NOT NULL,
            reviewer TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """)


def audit(case_id: str, action: str, user_name: str,
          previous_value: str = "", new_value: str = "") -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO audit_logs(case_id, action, user_name, timestamp, previous_value, new_value) VALUES(?,?,?,?,?,?)",
            (case_id, action, user_name, utc_now(), previous_value, new_value),
        )


def create_case(data: dict[str, Any], user_name: str) -> str:
    now = utc_now()
    case_id = f"PV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    wwuid = str(data.get("WWUID", "")).strip() or None
    with connect() as db:
        db.execute(
            "INSERT INTO cases(case_id, wwuid, stage, status, assigned_user, due_date, created_at, updated_at, data_json) VALUES(?,?,?,?,?,?,?,?,?)",
            (case_id, wwuid, STAGES[0], "In Progress", str(data.get("Assigned User", "")),
             str(data.get("Due Date", "")), now, now, json.dumps(data, ensure_ascii=False)),
        )
        db.execute(
            "INSERT INTO workflow_history(case_id, from_stage, to_stage, action, comments, user_name, timestamp) VALUES(?,?,?,?,?,?,?)",
            (case_id, "", STAGES[0], "Case created", str(data.get("Intake Comments", "")), user_name, now),
        )
        db.execute(
            "INSERT INTO audit_logs(case_id, action, user_name, timestamp, new_value) VALUES(?,?,?,?,?)",
            (case_id, "Case created", user_name, now, json.dumps(data, ensure_ascii=False)),
        )
    return case_id


def get_cases(search: str = "") -> list[dict[str, Any]]:
    with connect() as db:
        if search.strip():
            pattern = f"%{search.strip()}%"
            rows = db.execute(
                "SELECT * FROM cases WHERE case_id LIKE ? OR COALESCE(wwuid,'') LIKE ? OR data_json LIKE ? ORDER BY created_at DESC",
                (pattern, pattern, pattern),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["data"] = json.loads(item.pop("data_json"))
        except (json.JSONDecodeError, TypeError):
            item["data"] = {}
        result.append(item)
    return result


def get_case(case_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["data"] = json.loads(item.pop("data_json") or "{}")
    return item


def update_case(case_id: str, data: dict[str, Any], user_name: str, action: str = "Case information updated") -> None:
    previous = get_case(case_id)
    if previous is None:
        raise ValueError("Case does not exist")
    wwuid = str(data.get("WWUID", "")).strip() or None
    with connect() as db:
        db.execute(
            "UPDATE cases SET wwuid=?, assigned_user=?, due_date=?, data_json=?, updated_at=? WHERE case_id=?",
            (wwuid, str(data.get("Assigned User", "")), str(data.get("Due Date", "")),
             json.dumps(data, ensure_ascii=False), utc_now(), case_id),
        )
        db.execute(
            "INSERT INTO audit_logs(case_id, action, user_name, timestamp, previous_value, new_value) VALUES(?,?,?,?,?,?)",
            (case_id, action, user_name, utc_now(), json.dumps(previous["data"], ensure_ascii=False), json.dumps(data, ensure_ascii=False)),
        )


def transition_case(case_id: str, to_stage: str, action: str, comments: str, user_name: str) -> None:
    case = get_case(case_id)
    if case is None:
        raise ValueError("Case does not exist")
    current = case["stage"]
    if to_stage == "Data Entry" and current in ("Quality Control Review", "Medical Review") and action == "Return for Rework":
        pass
    elif current not in STAGES or STAGES.index(to_stage) != STAGES.index(current) + 1:
        raise ValueError(f"Invalid transition from {current} to {to_stage}")
    if current in ("Quality Control Review", "Medical Review") and action not in ("Pass", "Return for Rework"):
        raise ValueError("Review stages must explicitly Pass or Return for Rework")
    if action == "Return for Rework" and not comments.strip():
        raise ValueError("Rework comments are required")
    now = utc_now()
    status = "Completed" if to_stage == "Completed" else ("Returned for Rework" if action == "Return for Rework" else "In Progress")
    with connect() as db:
        db.execute("UPDATE cases SET stage=?, status=?, updated_at=? WHERE case_id=?", (to_stage, status, now, case_id))
        db.execute(
            "INSERT INTO workflow_history(case_id, from_stage, to_stage, action, comments, user_name, timestamp) VALUES(?,?,?,?,?,?,?)",
            (case_id, current, to_stage, action, comments.strip(), user_name, now),
        )
        db.execute(
            "INSERT INTO audit_logs(case_id, action, user_name, timestamp, previous_value, new_value) VALUES(?,?,?,?,?,?)",
            (case_id, f"Workflow: {action}", user_name, now, current, f"{to_stage}; {comments.strip()}"),
        )


def save_review(case_id: str, review_type: str, decision: str, comments: str, reviewer: str) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO review_records(case_id, review_type, decision, comments, reviewer, timestamp) VALUES(?,?,?,?,?,?)",
            (case_id, review_type, decision, comments.strip(), reviewer, utc_now()),
        )
        db.execute(
            "INSERT INTO audit_logs(case_id, action, user_name, timestamp, new_value) VALUES(?,?,?,?,?)",
            (case_id, f"{review_type} review: {decision}", reviewer, utc_now(), comments.strip()),
        )


def add_document(case_id: str, name: str, category: str, content_type: str,
                 content: bytes, description: str, date_received: str,
                 document_date: str, user_name: str) -> str:
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("Each document must be 10 MB or smaller")
    document_id = str(uuid.uuid4())
    safe_suffix = Path(name).suffix.lower()
    stored = DOCUMENT_DIR / f"{document_id}_v1{safe_suffix}"
    stored.write_bytes(content)
    now = utc_now()
    try:
        with connect() as db:
            db.execute(
                "INSERT INTO documents(document_id, case_id, name, category, content_type, current_version, description, date_received, document_date, uploaded_by, uploaded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (document_id, case_id, Path(name).name, category, content_type, 1, description, date_received, document_date, user_name, now),
            )
            db.execute(
                "INSERT INTO document_versions(document_id, version, stored_path, size_bytes, uploaded_by, uploaded_at) VALUES(?,?,?,?,?,?)",
                (document_id, 1, str(stored), len(content), user_name, now),
            )
            db.execute(
                "INSERT INTO audit_logs(case_id, action, user_name, timestamp, new_value) VALUES(?,?,?,?,?)",
                (case_id, "Document uploaded", user_name, now, f"{Path(name).name} (v1)"),
            )
    except Exception:
        stored.unlink(missing_ok=True)
        raise
    return document_id


def list_documents(case_id: str = "") -> list[dict[str, Any]]:
    query = """SELECT d.*, v.stored_path, v.size_bytes FROM documents d
               JOIN document_versions v ON v.document_id=d.document_id AND v.version=d.current_version"""
    with connect() as db:
        rows = db.execute(query + (" WHERE d.case_id=?" if case_id else "") + " ORDER BY d.uploaded_at DESC", (case_id,) if case_id else ()).fetchall()
    return [dict(row) for row in rows]


def document_versions(document_id: str) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM document_versions WHERE document_id=? ORDER BY version DESC", (document_id,)).fetchall()
    return [dict(row) for row in rows]


def replace_document(document_id: str, name: str, content: bytes, content_type: str, user_name: str) -> int:
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("Each document must be 10 MB or smaller")
    with connect() as db:
        doc = db.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if doc is None:
        raise ValueError("Document does not exist")
    version = doc["current_version"] + 1
    suffix = Path(name).suffix.lower()
    stored = DOCUMENT_DIR / f"{document_id}_v{version}{suffix}"
    stored.write_bytes(content)
    now = utc_now()
    with connect() as db:
        db.execute("INSERT INTO document_versions(document_id, version, stored_path, size_bytes, uploaded_by, uploaded_at) VALUES(?,?,?,?,?,?)", (document_id, version, str(stored), len(content), user_name, now))
        db.execute("UPDATE documents SET current_version=?, name=?, content_type=?, uploaded_by=?, uploaded_at=?, review_status='Pending review' WHERE document_id=?", (version, Path(name).name, content_type, user_name, now, document_id))
        db.execute("INSERT INTO audit_logs(case_id, action, user_name, timestamp, previous_value, new_value) VALUES(?,?,?,?,?,?)", (doc["case_id"], "Document version replaced", user_name, now, str(doc["current_version"]), str(version)))
    return version


def set_document_review(document_id: str, status: str, comments: str, user_name: str) -> None:
    with connect() as db:
        doc = db.execute("SELECT case_id, review_status FROM documents WHERE document_id=?", (document_id,)).fetchone()
        if doc is None:
            raise ValueError("Document does not exist")
        db.execute("UPDATE documents SET review_status=? WHERE document_id=?", (status, document_id))
        db.execute("INSERT INTO audit_logs(case_id, action, user_name, timestamp, previous_value, new_value) VALUES(?,?,?,?,?,?)", (doc["case_id"], "Document review updated", user_name, utc_now(), doc["review_status"], f"{status}: {comments}"))


def get_workflow(case_id: str = "") -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM workflow_history" + (" WHERE case_id=?" if case_id else "") + " ORDER BY id DESC", (case_id,) if case_id else ()).fetchall()
    return [dict(row) for row in rows]


def get_audit(case_id: str = "") -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM audit_logs" + (" WHERE case_id=?" if case_id else "") + " ORDER BY id DESC", (case_id,) if case_id else ()).fetchall()
    return [dict(row) for row in rows]


def get_reviews(case_id: str) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM review_records WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()
    return [dict(row) for row in rows]


def backup_database(destination: Path) -> None:
    with connect() as source, sqlite3.connect(destination) as target:
        source.backup(target)
