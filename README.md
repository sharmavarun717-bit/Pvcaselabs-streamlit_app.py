# PV Case Lab

An original Streamlit pharmacovigilance case-processing and training simulation. It is intended for educational demonstrations using synthetic data only. It is not a validated production pharmacovigilance system and does not perform real regulatory submissions.

## Run locally

Requires Python 3.11 or newer and `uv` (or install Streamlit and pandas in your environment).

```bash
uv sync
uv run streamlit run streamlit_app.py
```

The app initializes a SQLite database at `data/pv_caselab.sqlite3` and persists uploaded files under `data/documents/`. Set `PV_CASELAB_DATA_DIR` to choose another data directory. Back up this directory regularly. Streamlit Community Cloud's local filesystem may be ephemeral; use persistent external storage for durable multi-user use.

## Current implementation

The first implementation phase adds persistent case, workflow, review, document-version, and training audit records; intake with WWUID uniqueness and possible-duplicate prompting; searchable case queue; ICSR fields and repeatable product/event/laboratory training records; explicit workflow handovers; QC and medical review recording; versioned document upload/download and review; narrative drafts and versions; manual coding workspaces; training-only XML export; CSV reporting; basic training question; and SQLite backup.

## Limitations and safety

- Synthetic training data only; never upload real patient or reporter identifiers.
- Demonstration role selection is not authentication or an authorization boundary.
- Audit records are not immutable or regulatory validated.
- MedDRA and WHODrug dictionaries are not included. Do not invent codes or claim official coding. Use authorized/licensed data only.
- The XML download is an educational sketch, not a valid E2B(R3) message and not a submission.
- Local database/files need external persistent storage and a real identity provider before multi-user/production-like deployment.
- PDF preview, robust dictionary import, faculty grading, full analytics, schema validation and additional deployment hardening remain future work.
