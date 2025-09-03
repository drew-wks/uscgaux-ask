# ASK (Auxiliary Source of Knowledge)

## Description
This repository contains the Streamlit user interface for ASK — the U.S. Coast Guard Auxiliary’s AI-powered question answering tool. ASK uses a Retrieval-Augmented Generation (RAG) pipeline to search authoritative, public USCG Auxiliary references and respond with sourced, natural‑language answers.

For a non‑technical overview of the project, see [ASK_overview.md](ASK_overview.md).

## Repo Structure
- Entrypoint: `ui.py` (Streamlit app)
- Pages: `pages/` (e.g., `pages/Library.py`)
- UI helpers: `sidebar.py`, `streamlit_ui_check.py`
- RAG pipeline: `utils/rag.py`, `utils/filter.py`, `utils/filter_spec.py`
- Backend bridge: `utils/backends_bridge.py`, `utils/protocols.py`
- Config data: `config/` (e.g., `acronyms.csv`, `terms.csv`)
- Tests: `tests/` (includes Streamlit app tests)

This UI relies on the backend connectors and configuration provided by the `uscgaux` package (imported as `uscgaux.*`). At runtime, configuration is loaded through `uscgaux.config.loader.load_config_by_context()` and used to initialize vector DB, catalog, and related services.

## Prerequisites
- Python 3.10+
- Streamlit
- Access and credentials for the configured backends (e.g., Qdrant, catalog provider) via the `uscgaux` package

## Installation
1) Create and activate a virtual environment.
2) Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r requirements-dev.txt` (for development and tests)

If working inside a workspace path, you may need absolute paths such as:
- `pip install -r /workspace/ASK/requirements.txt`
- `pip install -r /workspace/ASK/requirements-dev.txt`

## Configuration
ASK reads configuration and secrets from two places:
- `.env` (environment defaults)
- `.streamlit/secrets.toml` (secrets for local dev and Streamlit Cloud)

Do not commit secrets. Ensure both files are set up before running locally. At minimum, the UI expects:
- `OPENAI_API_KEY_ASK` (used by LangChain/OpenAI integrations)
- `LANGCHAIN_API_KEY` (for LangSmith tracing)

Additional configuration (catalog, vector DB, providers, etc.) is resolved by `uscgaux` via `load_config_by_context()`. Refer to your environment’s configuration for required keys.

## Run Locally
- `streamlit run ui.py`

Notes:
- Streamlit uses the repository root as the working directory. Use forward slashes in paths.
- On startup, the app validates filter specs and attempts to initialize catalog and vector DB connectors through `uscgaux`. If backends or config are unavailable, the UI will show an error banner.

## Testing
- Unit and integration tests live under `tests/`.
- Streamlit UI tests use `st.testing.v1.AppTest`.
- Run tests: `pytest`

## Developer Workflow
- Use `logging` (not `print`).
- Follow Google‑style docstrings.
- Avoid `from module import *`.
- Run `pyright` after editing a function, before submitting a PR, and before running tests.

## Network Access
This UI communicates with configured backends (e.g., vector DB, catalog) at runtime. If working in a restricted environment where outbound requests are blocked, capture attempted requests and include them in a report file named `requests` alongside your PR for review.

## Troubleshooting
- "Backend init/fetch failed" or missing catalog data: verify `uscgaux` configuration and credentials are available through `.env`/`st.secrets`.
- OpenAI or LangSmith errors: confirm `OPENAI_API_KEY_ASK` and `LANGCHAIN_API_KEY` are set in `secrets.toml`.
- Filter spec warnings: see `utils/filter_spec.py` and the upstream spec referenced there.

## Usage License
See `LICENSE.txt`.

## Compliance
### Dependencies Licenses
Proejct dependencies are scanned and verified free from strong copyleft (aka "viral") licenses listed in `liccheck.ini` using `licensecheck`. To renew scan, 

```bash
pip install requirements-dev.txt
licensecheck > logs/license_scan_results_updated.txt
```
