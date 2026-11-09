# PV Case Lab

An original Streamlit pharmacovigilance case-processing and training simulation. Educational demonstrations only; use synthetic data. This is not a validated production pharmacovigilance system.

## Single-person local testing

The current setup is intended for **one person running the app on their own computer**. Start it locally:

```bash
uv sync
uv run streamlit run streamlit_app.py
```

The Streamlit server is configured to bind to `127.0.0.1`, so it is intended to be available only on the computer running it. Do not deploy this single-user setup publicly or expose the port to a network. The demo role selector is only a way for the one tester to inspect role-specific training screens; it is not login, authentication, or access control.

## Current local storage

For this test phase the app uses local SQLite and local file storage:

- Database: `data/pv_caselab.sqlite3`
- Uploaded documents: `data/documents/`

Case edits and documents are persisted across browser logout/restart as long as these files remain on the same computer. Back up the entire `data` directory. The storage choice can be revisited before any shared or hosted deployment. Do not run multiple app instances against the same SQLite database while testing.

## Coding dictionaries

The `pages/1_Coding_Workspaces.py` page provides MedDRA event coding and WHODrug product coding workspaces. No official dictionary is bundled. Only import data you are authorized to use; uploaded CSV data are not independently verified. Manual entries are training-only and not dictionary-verified.

## Important limitations

- Synthetic training data only; never upload real patient or reporter identifiers.
- Single-person local test setup; no production authentication or multi-user access control.
- Audit records are persistent but not immutable or regulatory validated.
- The XML download is an educational sketch, not a valid E2B(R3) message or a regulatory submission.
- This local storage configuration should not be treated as a shared database or production backup solution. Decide on hosted/shared storage only after testing and planning backups.
