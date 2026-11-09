"""Manual training coding and authorized dictionary lookup for PV Case Lab.

Dictionary records must come from data the user is authorized to use. This module
never creates or asserts official MedDRA or WHODrug terms/codes.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

import pv_storage as storage

MEDDRA = "MedDRA"
WHODRUG = "WHODrug"

MEDDRA_COLUMNS = {
    "term": ("llt", "llt term", "term"),
    "code": ("llt_code", "llt code", "code"),
    "pt": ("pt", "pt term"),
    "pt_code": ("pt_code", "pt code"),
    "hlt": ("hlt",),
    "hlgt": ("hlgt",),
    "soc": ("soc",),
    "primary_soc": ("primary_soc", "primary soc"),
    "version": ("version", "dictionary version"),
}
WHODRUG_COLUMNS = {
    "term": ("preferred_name", "whodrug preferred name", "term"),
    "code": ("drug_code", "drug code", "code"),
    "active_ingredient": ("active_ingredient", "active ingredient", "ingredient"),
    "atc_code": ("atc_code", "atc code"),
    "drug_record_number": ("drug_record_number", "drug record number", "record number"),
    "strength": ("strength",),
    "pharmaceutical_form": ("pharmaceutical_form", "pharmaceutical form", "form"),
    "manufacturer": ("manufacturer",),
    "country": ("country",),
    "version": ("version", "dictionary version"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initialize() -> None:
    storage.init_db()
    with storage.connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS coding_dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dictionary_type TEXT NOT NULL,
            search_term TEXT NOT NULL,
            code TEXT NOT NULL,
            version TEXT NOT NULL DEFAULT '',
            record_json TEXT NOT NULL,
            source TEXT NOT NULL,
            imported_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_coding_dict_search
            ON coding_dictionary(dictionary_type, search_term);
        CREATE INDEX IF NOT EXISTS idx_coding_dict_code
            ON coding_dictionary(dictionary_type, code);
        CREATE TABLE IF NOT EXISTS case_codings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL REFERENCES cases(case_id),
            coding_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            reported_term TEXT NOT NULL DEFAULT '',
            coded_record_json TEXT NOT NULL,
            coding_status TEXT NOT NULL,
            coder TEXT NOT NULL,
            reviewer TEXT NOT NULL DEFAULT '',
            comments TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            UNIQUE(case_id, coding_type, target_id)
        );
        CREATE TABLE IF NOT EXISTS coding_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL REFERENCES cases(case_id),
            coding_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            action TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            user_name TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """)


def _normal_header(value: str) -> str:
    return " ".join(value.strip().lower().replace("-", " ").replace("_", " ").split())


def _row_value(row: dict[str, str], aliases: tuple[str, ...]) -> str:
    normalized = {_normal_header(key): (value or "").strip() for key, value in row.items()}
    for alias in aliases:
        value = normalized.get(_normal_header(alias), "")
        if value:
            return value
    return ""


def import_dictionary_csv(dictionary_type: str, content: bytes, user_name: str,
                          authorized_data_confirmed: bool) -> int:
    """Import user-authorized CSV rows; records are explicitly marked as imported.

    MedDRA requires LLT term and LLT code; WHODrug requires preferred name and
    drug code. Codes/terms are never synthesized by this importer.
    """
    if dictionary_type not in (MEDDRA, WHODRUG):
        raise ValueError("Dictionary type must be MedDRA or WHODrug")
    if not authorized_data_confirmed:
        raise ValueError("Confirm you are authorized to use this dictionary data")
    schema = MEDDRA_COLUMNS if dictionary_type == MEDDRA else WHODRUG_COLUMNS
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV must include a header row")
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError("Could not read the CSV; save it as UTF-8 CSV and try again") from exc
    if not rows:
        raise ValueError("CSV contains no dictionary records")
    records = []
    for line_number, row in enumerate(rows, start=2):
        term = _row_value(row, schema["term"])
        code = _row_value(row, schema["code"])
        if not term or not code:
            raise ValueError(f"Row {line_number} is missing the required term/name or code column value")
        normalized_record = {field: _row_value(row, aliases) for field, aliases in schema.items()}
        records.append((dictionary_type, term, code, normalized_record.get("version", ""),
                        json.dumps(normalized_record, ensure_ascii=False), "User-authorized CSV", user_name, _now()))
    initialize()
    with storage.connect() as db:
        db.executemany(
            "INSERT INTO coding_dictionary(dictionary_type, search_term, code, version, record_json, source, imported_by, created_at) VALUES(?,?,?,?,?,?,?,?)",
            records,
        )
    storage.audit("", f"{dictionary_type} training dictionary imported ({len(records)} records)", user_name)
    return len(records)


def search_dictionary(dictionary_type: str, query: str, limit: int = 50) -> list[dict[str, Any]]:
    initialize()
    if dictionary_type not in (MEDDRA, WHODRUG):
        raise ValueError("Unknown dictionary type")
    term = query.strip()
    if len(term) < 2:
        return []
    pattern = f"%{term}%"
    with storage.connect() as db:
        rows = db.execute(
            "SELECT id, search_term, code, version, record_json, source FROM coding_dictionary WHERE dictionary_type=? AND (search_term LIKE ? OR code LIKE ?) ORDER BY search_term LIMIT ?",
            (dictionary_type, pattern, pattern, max(1, min(limit, 200))),
        ).fetchall()
    return [{**dict(row), "record": json.loads(row["record_json"])} for row in rows]


def save_coding(case_id: str, coding_type: str, target_id: str,
                reported_term: str, coded_record: dict[str, Any], status: str,
                coder: str, reviewer: str = "", comments: str = "") -> None:
    if coding_type not in (MEDDRA, WHODRUG):
        raise ValueError("Unknown coding type")
    if status not in ("Pending", "Training entry - not dictionary verified", "Dictionary selection - training only", "Reviewed"):
        raise ValueError("Invalid coding status")
    if status == "Reviewed" and not reviewer.strip():
        raise ValueError("A reviewer is required to mark coding as reviewed")
    initialize()
    now = _now()
    snapshot = {
        "reported_term": reported_term.strip(), "coded_record": coded_record,
        "coding_status": status, "coder": coder.strip(), "reviewer": reviewer.strip(),
        "comments": comments.strip(), "updated_at": now,
    }
    with storage.connect() as db:
        existing = db.execute(
            "SELECT id FROM case_codings WHERE case_id=? AND coding_type=? AND target_id=?",
            (case_id, coding_type, target_id),
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE case_codings SET reported_term=?, coded_record_json=?, coding_status=?, coder=?, reviewer=?, comments=?, updated_at=? WHERE id=?",
                (reported_term.strip(), json.dumps(coded_record, ensure_ascii=False), status, coder.strip(), reviewer.strip(), comments.strip(), now, existing["id"]),
            )
            action = "Coding updated"
        else:
            db.execute(
                "INSERT INTO case_codings(case_id, coding_type, target_id, reported_term, coded_record_json, coding_status, coder, reviewer, comments, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (case_id, coding_type, target_id, reported_term.strip(), json.dumps(coded_record, ensure_ascii=False), status, coder.strip(), reviewer.strip(), comments.strip(), now),
            )
            action = "Coding created"
        db.execute(
            "INSERT INTO coding_history(case_id, coding_type, target_id, action, snapshot_json, user_name, timestamp) VALUES(?,?,?,?,?,?,?)",
            (case_id, coding_type, target_id, action, json.dumps(snapshot, ensure_ascii=False), coder.strip(), now),
        )
    storage.audit(case_id, f"{coding_type} {action.lower()}", coder, new_value=json.dumps(snapshot, ensure_ascii=False))


def get_coding(case_id: str, coding_type: str, target_id: str) -> dict[str, Any] | None:
    initialize()
    with storage.connect() as db:
        row = db.execute("SELECT * FROM case_codings WHERE case_id=? AND coding_type=? AND target_id=?", (case_id, coding_type, target_id)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["coded_record"] = json.loads(result.pop("coded_record_json"))
    return result


def get_history(case_id: str, coding_type: str, target_id: str) -> list[dict[str, Any]]:
    initialize()
    with storage.connect() as db:
        rows = db.execute("SELECT * FROM coding_history WHERE case_id=? AND coding_type=? AND target_id=? ORDER BY id DESC", (case_id, coding_type, target_id)).fetchall()
    results = []
    for row in rows:
        item = dict(row)
        item["snapshot"] = json.loads(item.pop("snapshot_json"))
        results.append(item)
    return results
