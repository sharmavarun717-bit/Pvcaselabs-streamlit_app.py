# PV Case Lab

An original Streamlit pharmacovigilance case-processing and training simulation. Educational demonstrations only; use synthetic data. This is not a validated production pharmacovigilance system.

## Run locally

Requires Python 3.11 or newer and `uv`.

```bash
uv sync
uv run streamlit run streamlit_app.py
```

## Keeping cases after logout

Case records are stored in SQLite, not in the browser's Streamlit session. The default database is `data/pv_caselab.sqlite3`; uploaded files are stored in `data/documents/`. Signing out, closing the browser, or starting a new Streamlit session will not clear these records. To keep them, do not delete the `data` directory and back it up regularly. You can set `PV_CASELAB_DATA_DIR` to a persistent folder before starting the app.

For example, on Linux/macOS:

```bash
export PV_CASELAB_DATA_DIR=/path/to/persistent/pv-caselab-data
uv run streamlit run streamlit_app.py
```

On Windows PowerShell:

```powershell
$env:PV_CASELAB_DATA_DIR = "D:\pv-caselab-data"
uv run streamlit run streamlit_app.py
```

**Hosting note:** local SQLite and files persist across logout/restart only if the host preserves the configured directory. Streamlit Community Cloud's local filesystem can be ephemeral across redeploys/restarts; use persistent mounted storage or a managed database/file store if you need durable hosted data. For five people, run one shared app against one persistent data directory; do not run separate copies with separate local databases if users need to see the same cases. Back up the entire data directory, including documents.

## Coding dictionaries

The `pages/1_Coding_Workspaces.py` page provides MedDRA event coding and WHODrug product coding workspaces. No official dictionary is bundled. Only import data you are authorized to use; uploaded CSV data are not independently verified. Manual entries are training-only and not dictionary-verified.

## Important limitations

- Synthetic training data only; never upload real patient or reporter identifiers.
- Demonstration role selection is not authentication or an authorization boundary.
- Audit records are persistent but not immutable or regulatory validated.
- The XML download is an educational sketch, not a valid E2B(R3) message or a regulatory submission.
- The app's SQLite database and document files are the persistent source of truth. Previous in-memory-only cases from older app versions cannot be recovered after their Streamlit session ended.
