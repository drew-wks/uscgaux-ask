# Administrative Module of the USCG Auxiliary AI-Native Knowledge Management and Governance Platform

## Description  
This repository contains the administration system for the AI-Native Knowledge Management and Governance Platform. This platform combines AI retrieval-augmented generation (RAG) with enterprise-grade document lifecycle management, giving organizations a single, unified environment to store, govern, and retrieve their knowledge with precision and compliance. Platform details can be found [here](platform_overview.md).

This instance has been customized to support a specific RAG application: the U.S. Coast Guard Auxiliary RAG system, called "ASK". The runtime and RAG pipeline for ASK are located at [ASK](https://github.com/drew-wks/ASK/).


## Overall Repo Structure  
-  **Entrypoint** `uscgaux/frontends/streamlit/streamlit_app.py` is built on Streamlit.
-  **Lifecycle orchestration** The scripts in `lifecycle/` (`propose.py`, `verify.py`, `promote.py`, `archive.py`, `delete.py`, `lifecycle_manager.py`, and `lifecycle_service.py`) define and execute the document lifecycle and ETL loop.
-  **Backend Adapters** provide shared helpers and low-level clients for backend service providers such as Google authentication, Google Drive, Qdrant, SQLite
-  **Backend Connectors** "connect" core services (file storage, metadata catalog, event logging, vector database), to backend providers. They define abstract interfaces that enable the entrypoint and orchestration layer to interact with backend providers via a consistent API. 
-  A **config** dict contains configuration helpers and constants, loaded from `.env` or `st.secrets`, and from `constants.py`
- A **catalog schema** defines the catalog metadata fields
-  Automated tests provide test coverage.  


## Document Lifecycle
The ETL loop drives documents through the following lifecycle states:  

| **Proposed** → **Verified** → **Live** → **Archived** |
| --- |

The catalog's `status` field is the ground truth for determining an item's lifecycle state. The core `DocumentLifecycleManager` (`lifecycle/lifecycle_manager.py`) defines the allowed transitions. When a frontend requests a change, `lifecycle_service.update_backends_and_apply_transitions()` persists catalog edits and uses the connectors to move files and vectors in the backends.

| Status | Description | Catalog | Drive Folder of PDF | in the Vector DB | Allowed actions
| --- | --- | --- | --- | --- |--- |
| **Proposed** | A newly-uploaded PDF document enters a `proposed` state while the system verifies it is a valid PDF and not already present in the CATALOG | None | None | No | `verify()`
| **Verified** | An entry enters the `verified` state, indicating the document has been verified and awaits tagging of its metadata by a Content Admin | CATALOG | PDF_STAGED | No | Promote, Reject
| **Promote** | A transitional state indicating an entry with completed metadata that is ready for validation and promotion to `live` status | CATALOG | PDF_STAGED | No |`promote()`
| **Live** | An active entry in the RAG system. Its information is accessible to End Users in the runtime environment | CATALOG | PDF_LIVE | Yes | Archive
| **Archive** | A transitional state indicating a live entry has been tagged for archiving. Once archived, the PDF is moved to `PDF_ARCHIVED`, the row copied to `CATALOG_ARCHIVED` with status set to `archived`, and the associated records removed from the vector db | CATALOG | PDF_LIVE | Yes | `archive()`
| **Archived** | An entry has been moved from live to archived. The catalog row and file have been archived. The vector db record has been deleted. | CATALOG_ARCHIVED | PDF_ARCHIVED | No | Delete
| **Delete** | A transitional state indicating an archived entry that has been tagged for deletion. Once deleted, all associated entries in the catalog, file storage file, and vector db (if applicable) will be deleted. | CATALOG_ARCHIVED | PDF_ARCHIVED | No | `delete()`
| **Reject** | A transitional state indicating an entry will be removed. All associated entries in the catalog, file storage file, and vector db (if applicable) will be deleted. | CATALOG | PDF_STAGED | No | `delete()`

### Frontends
Frontends provide the User Interface. Currently, the project only supports Streamlit. ETL functions for interfacing between the Streamlit Frontend and **Core** are located in `uscgaux/frontends/streamlit/stu`

### Backends  
Each original PDF document has corresponding 'items' contained in three external storage backends that are accessed by this project:
1. A **file storage** system which stores the original PDF files. The PDFs are used to create a vector record, and also stored for End User reference at runtime. This project supports Google Drive or a local file system for the file storage.

| Folder | Purpose |
| --- | --- |
| `PDF_STAGED` | Holds PDFs before they go live. Duplicates are not allowed. |
| `PDF_LIVE` | Contains PDFs that are currently in the vector db. Duplicates are not allowed. |
| `PDF_ARCHIVED` | Stores previously live PDFs. Duplicates are allowed. |


For local development, default SQLite databases and file storage are placed under a
`uscgaux/backends/local/` directory:

```
uscgaux/backends/local/
  file_storage/
  catalog/
    catalog.db
    catalog_archive.db
  event_log/
    event_log.db
  vectordb/
```

Override the file storage location with the `LOCAL_FILE_STORAGE_PATH` configuration
key if you need to store files elsewhere.


2. A **vector database** which stores the pdf document as vectors. This project currently supports Qdrant for the vector database.
3. A **catalog** of supplemental information (metadata) about the PDF document. The metadata is used during generation and filtering of results. This project supports Google Sheets or SQLite for the catalog.
4. An **event log** of CRUD actions performed on PDF files within the file storage folders.  

### Catalog for PDF Metadata  
Document metadata can be stored to be later used for results filtering or to enrich the response. The ground truth for metadata is a registry called `CATALOG`, which can be either a Google Sheet or SQLite table. CATALOG includes several mandatory fields, including a `status` field for tracking entry status. Duplicates are not allowed in `CATALOG`. System-required metadata is automatically computed and stored in the payload of each vector db record. Metadata for archived entries is stored in `CATALOG_ARCHIVED`, where duplicates are allowed. The location for `CATALOG` and `CATALOG_ARCHIVED` is configured in the configuration files (`uscgaux/config/DEFAULT.toml` and optional `uscgaux/config/local.toml`).

## Catalog ETL and Status Processing Flow  
Between **Frontends** and **Backends** is a **Core** layer where business rules are applied. There is a normalization helper (NH) applied at each boundary:    

```text
+----------+            +----------+            +----------+
|          |  -- NH ->  |          |  -- NH ->  |          |
| Frontend |            |   Core   |            |  Backend |
|          |  <- NH --  |          |  <- NH --  |          |
+----------+            +----------+            +----------+
```
| ETL Direction | Normalization Helper |
|-----------|-------------|
| **Frontend** → **Core** | `normalize_catalog_df_for_core`  |
| **Core** → **Backend** | `normalize_core_catalog_df_to_gsheets` (Google),   `normalize_core_catalog_df_to_sqlite` ( SQLite)|
| **Backend** → **Core** |  `normalize_catalog_df_for_core` |
| **Core** → **Frontend** |  `normalize_core_catalog_df_to_streamlit` prepares data for editing and display in Streamlit. |


## Architecture Detail
### Configuration  
Configuration is defined in a `config` dict utilizing tools in the `uscgaux/config/` package. `uscgaux/config/loader.py` composes the config with the following precedence:

Configuration sources (lowest → highest precedence):

1. `DEFAULT.toml`  
2. `local.toml` (or `CONFIG_FILE`)  
3. `.env` → `os.environ`  
5. Project-level `.streamlit/.secrets.toml`  
6. User-level  `~/.streamlit/secrets.toml` or on Streamlit Community Cloud

Access settings directly from `config` dict using `config['<key>']`. Backend-specific keys are grouped under namespaced sections in `uscgaux/config/local.toml`. 

During installation, `install.sh` will copy `uscgaux/config/DEFAULT.toml` to `uscgaux/config/local.toml` if it does not exist. Edit `uscgaux/config/local.toml` or `.env` to customize your deployment. 

At initialization, `load_config_by_context()` selects the appropriate subsection for each service
based on the `BACKENDS` settings and merges its keys into the top-level
configuration mapping.


### Entrypoint  
The Entrypoint `uscgaux/frontends/streamlit/streamlit_app.py` calls `uscgaux.config.load_config_by_context()` to configure the environment and set up the Connector pattern.
1. Load all runtime configuration (IDs, flags, etc.)  
2. Initialize a connector for each service by calling `uscgaux.backends.init_connectors`, which wraps each raw provider client (e.g., Google Drive, Sheets, Qdrant, LangChain) in a connector (e.g., ``GoogleDriveConnector``, `GoogleSheetCatalogConnector`)  
3. Passes the resulting connectors and config to functions in the Orchestration layer (e.g., promote) as needed.  

Provider clients are created once and all lifecycle orchestration logic receives pre-configured, high-level interfaces and never directly depends on raw clients.

### Connectors  
Connectors (in `backends/connectors/`) define abstract interfaces used by the entrypoint file and lifecycle orchestration layer to interact with storage backends (such as Google Drive/Sheets, Qdrant, local file systems, SQLite). They encapsulate service provider-specific logic (authentication, API access) behind clean interfaces to the backends like `CatalogConnector` or `FileStorageConnector`. Internally, they use raw clients (e.g. gspread.Client) and adapters to handle shared logic. For example, `GoogleDriveConnector` wraps Drive operations like `list_files`, `upload_pdf`, and `move_file`. No in-memory business logic beyond minimal shaping required to serialize/deserialize (e.g., dropping _table_row) occurs in the Connectors.
 
### Lifecycle Orchestrators 
Scripts that define and execute document lifecycle and ETL operations by composing backend connectors and **Core** transformations to persist changes across frontends and backends.

  -  `lifecycle/lifecycle_manager.py` defines the `DocumentLifecycle` enum and the `DocumentLifecycleManager` to manage allowed transitions, exposing `apply_transition()` to invoke `promote`, `delete`, or `archive` actions when statuses change.

  -  `lifecycle/lifecycle_service.py` provides a `LifecycleContext` dataclass and `update_backends_and_apply_transitions` to persist catalog edits and execute lifecycle transitions using the configured connectors.

  -  `lifecycle/propose.py` – a reusable function for handling file uploads in platforms that do not natively provide upload mechanisms (unlike Streamlit’s st.file_uploader). The `propose()` function accepts file paths, raw file-like objects, or an iterable containing both and normalizes them into objects conforming to the `FileLike` protocol. Once complete, `propose()` sets state to `proposed` and returns the objects for downstream processing in `lifecycle/verify.py`.

  -  `lifecycle/verify.py` – verifies the proposed file object represents a valid PDF and not already present in the CATALOG by computing a PDF ID for each uploaded file object and checks against existing items in the backend storage systems. Once verified, it uploads the PDF to Drive, appends any default values defined in the schema to the catalog of metadata, and places it in `verified` status. When `INFER_PDF_TITLE` is enabled (default) in the configuration, the first page text is analyzed by an OpenAI model to suggest a title. Duplicate or failed uploads are rejected and logged.

  -  `lifecycle/promote.py` – validates catalog rows marked `promote`, uploads document chunks to the vector db, moves the PDF to the live file storage folder, updates the table status to live, and removes duplicates if necessary. A summary DataFrame of upload results is returned.

  -  `lifecycle/archive.py` – processes rows marked `archive`: moves PDFs to the archive file storage folder, deletes vector db records, appends the row to `CATALOG_ARCHIVED`, removes it from `CATALOG`.

  -  `lifecycle/delete.py` – removes all of an item's artefacts from the catalog, file storage, and vector database backend services.


### Utilities
-  `uscgaux/utils/app_logging.py`provides app logging and function trace decorators.

-  `uscgaux/utils/catalog_schema_utils.py` centralizes utilities to load, merge, and query the schema for use across the project. Uses include enforcing schema validation, building dynamic UI components (e.g., forms) based on schema rules, and quickly identifying which fields must be provided to Content Admins versus those that are set by the system.

-  `uscgaux/utils/event_logging.py` provides tools for writing structured entries into the event log sheet.

-  `uscgaux/utils/diagnostics.py` is a quality assurance tool that build a comprehensive diagnostic_map by comparing all entries across the live backends to identify and report issues such as missing IDs, duplicates, and orphaned files

-  `uscgaux/utils/infer_title.py` allows verify() to use OpenAI to infer a title from the first page of a PDF. Its flag, `INFER_PDF_TITLE`, is set in the configuration files. When disabled, titles remain blank and must be provided manually.

-  `uscgaux/utils/langchain.py` contains helpers for loading PDF content and storing embeddings in Qdrant.

-  `uscgaux/utils/presidio_scan.py` uploaded text and PDFs are scanned with [Microsoft Presidio](https://microsoft.github.io/presidio/) to detect sensitive entities such as PII, PHI and documents marked confidential. The scanner can also load custom recognizers for agency or company-specific classified terms. When entities are detected the system can **flag**, **redact**, or **block** the content based on policy. Presidio’s configuration main confitaion is located in `DEFAULT.toml` and its `local.toml` override. Custom recognizer definitions live in `uscgaux/config/scanning`. There you’ll find the main configuration file `scanner.config.json` and optional JSON files defining extra recognizers: `recognizers_pii_phi.json` (for PII/PHI) and `recognizers_classified.json` (for classified terms)

-  `uscgaux/utils/transform_catalog_df.py` contain pure, in-memory DataFrame transformation and validation utilities for Backend, Frontend, and Core operations. This includes PDF ID calculation, metadata validation helpers, and DataFrame manipulation helpers. Backends call these functions after fetching data in order to normalize it before returning it to callers. Frontends and orchestration scripts call them when they already have a DataFrame in memory and need to apply business rules or shape the data for further processing.

-  `uscgaux/utils/value_utils.py` centralizes pure, data value transformation utilities for use across the project.

### Provider Adapters  
Stateless provider-specific modules live in the `backends/providers/` package so they can be used by the connectors and other utilities:

-  `gcp_adapter.py` handles authentication and high‑level Google Drive operations, including listing files, downloading PDFs, etc.) using a native Google API client.  

- `gsheets_adapter.py` provides native utilities for managing a Google Sheet as the system’s master catalog, including functions to fetch, read, append, replace, and delete rows while maintaining catalog schema alignment and data consistency.  

-  `qdrant_adapter.py` handles access to the Qdrant vector db, e.g. creating the client, checking for existing records, and updating metadata using a native Qdrant API client.  

-  `sqlite_adapter.py` offers SQLite-specific catalog utilities for local operations.

### Testing
-  `tests/` defines a suite of tests. Run them by installing requirements-dev.txt and running `pytest` 


### Example Connector Pattern for uploading PDF metadata to the Catalog stored in a Google Sheet backend  
```
Entry point (`uscgaux/frontends/streamlit/streamlit_app.py`)
└── loads → configuration (config dict) from `uscgaux.config.loader.load_config_by_context`
└── initializes → connector and raw client via `uscgaux.backends.init_connectors` using config dict
└── calls → logic in the lifecycle orchestration layer (e.g., `verify.verify`)  
    └── uses → `GoogleSheetCatalogConnector` (a concrete implementation of `CatalogConnector`)  
         └── uses → `fetch_sheet_as_df()` from `backends/providers/gsheets_adapter`
            └── uses → `gspread` raw client to access the backend Google Sheet
```
Once the configuration is loaded and connectors (and their associated raw clients) are initialized at the entry point, the configuration is passed down through the call stack. At the frontend and lifecycle orchestration levels, configuration is passed as a single dictionary. At the backend helper level, relevant values are passed individually.

Once connector objects are initialized and data has been fetched from them (e.g., using `filter_df_rows_by_status(catalog.fetch_table_and_normalize_catalog_df_for_core())`), any subsequent transformations should be performed using utility functions (e.g., in `utils.transform_catalog_df`) rather than re-calling connector methods that would trigger redundant backend fetches.

## Catalog Schema  
The base catalog schema lives at `uscgaux/config/CATALOG_SCHEMA_BASE.json` and is loaded as a packaged resource. It defines the expected structure, required fields, data types, and validation rules for each row in the metadata catalog. The project includes explicit validation logic to ensure each catalog entry conforms to this base schema across ingestion, validation, and automation workflows.  

Each field in the schema may include optional keys that influence system behavior:  

- **`system_required`** – An optional key. When present and set to `true`, the field must be present for the application to operate correctly. If key is set to None or `false` (default), the field is not required by the system.  
- **`user_required`** – An optional key indicating the field must be populated by the Content Admin when set to `true`. If key is set to None or `false` (default), the field is not required.
- **`read_only`** – If `true`, the field cannot be modified by Content Admins. If key is set to None or `false` (default), the field is editable by Content Admins.

Validation utilities enforce `system_required` rules when checking core payloads and report missing `user_required` fields separately. Administrative UIs may use `read_only` to determine which columns are editable.

The key `_table_row` specifies a transient helper field that maps DataFrame rows to Google Sheet or SQLite row positions. The field isn't persisted, so the values are not system_required, but the key exists in the schema to allow the system to create the field when needed and still pass validation.  

The `status` key in the schema defines the allowed lifecycle states. These values must match the constants in `lifecycle.lifecycle_manager.DocumentLifecycle` to ensure consistency between validation and the `DocumentLifecycleManager`.  

System Admins may optionally extend the base schema by creating `uscgaux/config/catalog_schema_admin.json` and setting the `CATALOG_SCHEMA_ADMIN_PATH` environment variable (defaults to this path). Keys in the System Admin schema are merged with the base schema, but any attempt to override keys in the base schema is ignored.

Note for tests and local overrides: utilities first look for a colocated `CATALOG_SCHEMA_BASE.json` next to the module (supports tests that monkeypatch `__file__`). If none is found, they fall back to the packaged `uscgaux/config/CATALOG_SCHEMA_BASE.json`.

## Event Logging
The Administrative Module includes an **event logging mechanism** to maintain a permanent record of CRUD actions performed on PDF files within the file storage folders `PDF_STAGED`, `PDF_LIVE`, and `PDF_ARCHIVED`. This log allows developers and System Admins to trace and verify changes over time.

### What is an Event?
An **event** refers to any **modification** to a PDF file in the file storage system:

* PDF additions or moves between `PDF_STAGED`, `PDF_LIVE`, and `PDF_ARCHIVED`
* PDF deletions from these folders

Changes to the catalog or vector database are not logged.

*Note:* Read-only operations are **not** considered events and are therefore not logged.

Each event is recorded as a single **event record** (a row) in a centralized **administrative event log** maintained in a Google Sheet. These records provide detailed insight into what happened, when it happened, and what resource was affected.

### Where are Events Logged?  
Events are logged in a table identified by `EVENT_LOG_ID`. At runtime the full sheet link `EVENT_LOG` is derived from `EVENT_LOG_ID` using `SHEET_LINK_TEMPLATE`. This table contains one row per event and captures structured metadata about each change.

### What Gets Logged?  
Each event record includes:

* `timestamp` — When the event occurred
* `action` — The type of change (e.g., `add`, `update`, `delete`)
* `pdf_id` — Unique identifier of the PDF document involved
* `pdf_file_name` — Human-readable name of the file
* Optional `extra_columns` — A list of supplemental values to add contextual information (e.g., previous status, new status)

### Usage  
Event logging is handled via an `EventLoggingConnector` interface defined in `backends/connectors/event_log.py`. The default implementation is `GoogleSheetsEventLogger`, which appends rows to the configured Google Sheet and exposes `get_log_url()` to retrieve the sheet link.

## RAG Configuration
- Split across three tables in TOML:
  - `RAG.INGESTION` (e.g., `chunk_size`, `chunk_overlap`, `length_function`, `separators`)
  - `RAG.RETRIEVAL` (e.g., `k`, `fetch_k`, `search_type`)
  - `RAG.GENERATION` (e.g., `generation_model`, `temperature`)
- Access in code using the nested mapping assembled by the loader:
  - Ingestion: `config["RAG"]["INGESTION"]`
  - Retrieval: `config["RAG"]["RETRIEVAL"]`
  - Generation: `config["RAG"]["GENERATION"]`
- Combined view: `config["RAG_ALL"]` merges the above (later sections override earlier on conflicts).
- Notes:
  - The loader deep-merges `config/DEFAULT.toml` with `config/local.toml` and environment variables.
  - `RAG.INGESTION.length_function` accepts the string `"len"` in TOML and is coerced to the callable in Python.

Events may be logged from anywhere except within the connectors module (on which it relies). To log an event programmatically, use the helper in `event_logging.py`:

```python
from uscgaux.utils.event_logging import write_event

write_event(
    event_log=event_log,  # An instance of EventLoggingConnector
    action="update",
    pdf_id="abc123",
    pdf_file_name="Auxiliary_Policy.pdf",
    extra_columns=["live", "archived"]
)
```

You can also batch multiple events:

```python
from uscgaux.utils.event_logging import write_events

events = [
    {"action": "add", "pdf_id": "abc123", "pdf_file_name": "Intro.pdf"},
    {"action": "delete", "pdf_id": "xyz789", "pdf_file_name": "Old_Notice.pdf"}
]
write_events(event_log, events)
```

### Viewing Logs  
You can access the full log directly via the Google Sheets URL or by calling:

```python
event_log.get_log_url()
```

For filtering logs related to a specific PDF:

```python
event_log.fetch_events("abc123")
```

To retrieve the entire log as a DataFrame:

```python
event_log.fetch_log_df()
```


## User Roles  
- **End User** – uses the RAG system to search, ask questions, and get answers from documents. The RAG system is contained in a separate repo. End Users have no access to the Administrative Module.
- **Content Administrator** ("Content Admin") – uses the Administrative Module to add new content, update catalog entries, and manage day-to-day ingestion.
- **System Administrator** ("System Admin") – uses the Administrative Module to design the metadata schema, set governance and ingestion rules, and configure the system.

The Administrative Module is only available to Content Admins and System Admins.


## Getting Started
1. **Clone the repository** 

   ```bash
   git clone https://github.com/drew-wks/uscgaux.git
   cd your-repo  
   ```

2. **Run the installer script** from the project root. It will set up a virtual environment, install dependencies, configure default paths, and create `uscgaux/config/local.toml` from `uscgaux/config/DEFAULT.toml` if needed:

   ```bash
   chmod +x install.sh   # only needed once to make the script executable
   ./install.sh
   ```

3. Set your api keys either by saving as `.env` in project root or as streamlit secrets.

4. **Configure your Environment**  
`RUN_CONTEXT` and `FORCE_USER_AUTH` determine system configuration.  

### RUN_CONTEXT  
The application can operate in either of two run contexts. When launched via the Streamlit UI (`uscgaux/frontends/streamlit/streamlit_app.py`), configuration values come from **Streamlit secrets**. When running scripts or notebooks directly, values are loaded from a **local `.env` file**.

   - streamlit → Uses `st.secrets` and decorators (DEFAULT)  
   - cli → Uses `.env` and skips Streamlit features. Note: Streamlit will try to resolve missing keys by falling back to a user-level secrets file, if available. Therefore, be sure to remove that file `~/.streamlit/secrets.toml`  whe running in cli mode
  
### FORCE_USER_AUTH
   - true → Requires login (default when in Streamlit)
   - false → Bypasses login to facilitate local development and testing

✅ For local development, define `RUN_CONTEXT` and `FORCE_USER_AUTH` in your `.env` file, if it exists.    
🚫 For Streamlit Community Cloud, DO NOT include `RUN_CONTEXT` and `FORCE_USER_AUTH` in your Streamlit Community Cloud secrets — they are inferred there.  `uscgaux.config.loader.load_config_by_context()` reads these environment switches and configures the app accordingly.

### CATALOG_SCHEMA_ADMIN_PATH
Optional path to an additional JSON file containing catalog schema keys managed by the System Admin. Defaults to `uscgaux/config/catalog_schema_admin.json`.


### SCAN_UPLOADS  
Toggles scanning of uploaded PDFs via Presidio.
- Provide a `scanner.config.json` file (copy the template from `uscgaux/config/scanning/`) with:
  - `modes` that enable PII/PHI and/or classified scanning and optional paths to custom recognizer JSON files.
  - `action.on_detect` set to `flag`, `redact`, or `block`.
  - `action.redaction` settings when redaction is enabled (`strategy`, `masking_char`, or `replacement`).
  - `action.redaction.strategy` can be `mask` (uses `masking_char`) or `replace` (uses `replacement`).
- Ensure any referenced custom recognizer files are deployed alongside the config file.
- Install the required spaCy model (`en_core_web_sm`).


### BACKENDS
The `BACKENDS` configuration in selects which provider is used for each service.  

| Service | Default Provider | Currently-supported Options |
| --- | --- | --- |
| `file_storage` | `google_drive` | `google_drive`, `local_fs` |
| `catalog` | `google_sheets` | `google_sheets`, `sqlite` |
| `event_log` | `google_sheets` | `google_sheets` |
| `vectordb` | `qdrant` | `qdrant` |

Use the `qdrant_location` setting (`"cloud"` or `"local"`) to choose between a remote or local Qdrant instance. With
`qdrant_location = "cloud"`, the connector reads `QDRANT_URL` and `QDRANT_API_KEY` to reach Qdrant Cloud. Setting
`qdrant_location = "local"` instead uses `QDRANT_PATH` to access a local server.


## Adding New Backends  
Follow these steps to add support for a new backend provider for file storage, catalog, event logging, or vector database:

1. **Create a Adapter**  
   Add a new adapter module for that provider into the `backends/providers` directory (e.g., `your-backend-provider_adapater.py`) that implements provider-specific logic, such as authentication, file I/O and uses pd.DataFrame as the interchange type when moving tabular data across the boundary.

2. **Extend the Connector Class**  
   In `backends/connectors/`, implement a new connector class tha corresponds to the type of service the provider offers. by inheriting from the appropriate abstract base class (e.g., `FileStorageConnector`, `CatalogConnector`, `EventLoggingConnector` or `VectorDBConnector`). Ensure your class implements all required methods.

3. **Register the Connector in `backends/__init__.py`**
   Update the logic in `__init__.py` (such as `init_connectors()`) to recognize your new backend and return an instance of your connector based on the active configuration.

4. **Update the Configuration Files**
   In `uscgaux/config/local.toml`, set the backend identifiers in the `[BACKENDS]` section to select the implementation for each service. Add any required API keys to a `.env` file at the project root.

## Integration Testing of Connectors (Drive & Sheets)
To exercise the Drive/Sheets backends against real GCP resources instead of mocks:

1. **Prepare GCP credentials**: Create a service account in your Google Cloud project bucket:  
-  Add AllAuthenticatedUsers as a principal of the bucket and grant AllAuthenticatedUsers the role of Storage Object Admin and Storage Admin  
-  Give the account the necessary Drive API scopes (at minimum, Drive API Editor + Sheets API Editor)  
-  Share the target Drive folders/files with that service account’s email  
-  Create service-account key JSON  
-  Export the key JSON  
   ```bash
   export GCP_CREDENTIALS_FOR_STREAMLIT_USCGAUX_APP="/path/to/your/service-account.json"
   ```
2. **Configure folder and sheet IDs** in a `.env` at the project root:
   ```dotenv
   RUN_CONTEXT=cli
   FORCE_USER_AUTH=false

   CATALOG=<your-catalog-sheet-id>
   CATALOG_ARCHIVED_ID=<your-archive-sheet-id>
   EVENT_LOG_ID=<your-event-log-sheet-id>

   PDF_STAGED_ID=<your-staging-folder-id>
   PDF_LIVE_ID=<your-live-folder-id>
   PDF_ARCHIVED_ID=<your-archive-folder-id>

   FILE_LINK_TEMPLATE=https://drive.google.com/file/d/{file_id}/view
   FOLDER_LINK_TEMPLATE=https://drive.google.com/drive/folders/{folder_id}
   ```
3. **Reload environment**:
   ```bash
   source .env
   ```
4. **Run a quick integration script** (or use `python -m uscgaux.utils.integration`):
   ```python
   from uscgaux.config.loader import load_config_by_context
    from uscgaux.backends import init_connectors

   cfg = load_config_by_context()
   catalog, catalog_archive, file_storage, vectordb, event_log = init_connectors(cfg)

   # List existing files
   print('Staging files:', file_storage.list_files(cfg['PDF_STAGED_ID']))

   # Upload a test PDF
   with open('tests/lorem_ipsum.pdf','rb') as f:
       fid = file_storage.upload_pdf(f, 'test.pdf', cfg['PDF_STAGED_ID'])
   print('Uploaded ID:', fid)

   # Verify existence and move to live
   print('Exists?', file_storage.file_exists(fid))
   file_storage.move_file(fid, cfg['PDF_LIVE_ID'])
   print('Now in folder:', file_storage.get_folder_name(fid))

   # Cleanup
   file_storage.delete_file(fid)
   ```

Run it:
```bash
python -m uscgaux.utils.integration
```

You should see real API calls and be able to confirm listing, upload, movement, and deletion.


## Privacy and Security
The CI workflow includes the following security tools:
Static Code Analysis via `Bandit` (SAST) and Dependency vulnerability scanning via `pip-audit` which are run before committing changes.
The CI workflow fails if Bandit reports any high-severity findings or if pip-audit detects vulnerabilities.
GitHub’s built-in integration with GitGuardian is enabled to automatically scan commits and pull requests for leaked secrets.
A SBOM (Software Bill of Materials) is generated by pip-audit on every push and upload as a build artifact

Artifacts:
- `bandit.json` – Bandit findings.
- `sbom.cdx.json` – Software Bill of Materials (CycloneDX).


## Importing into another project 
You can use components of this project in your own RAG front end.  

```bash
pip install git+https://github.com/drew-wks/uscgaux.git@main
```

Example imports in another project:

```python
from uscgaux import (
    logging,
    load_schema_cached,
    stui,
    stu,
)
```

### Accessing the Catalog Schema from another repo
External projects can import the stable schema API and always get the current merged schema (base + admin) that ships with this package.

- Add dependency: `git+https://github.com/drew-wks/uscgaux.git@main#egg=uscgaux`
- Import the stable API: `from uscgaux import get_catalog_schema, get_allowed_values, get_editable_fields, get_read_only_fields, get_user_required_fields, get_system_required_fields`

Example usage:

```python
from uscgaux import (
    get_catalog_schema,
    get_allowed_values,
    get_editable_fields,
    get_read_only_fields,
    get_user_required_fields,
    get_system_required_fields,
)

# The merged schema (base + admin)
schema = get_catalog_schema()

# Populate UI choices
scopes = get_allowed_values("scope")
units = get_allowed_values("unit", {"scope": "District"})

# Field sets for validation / forms
editable = get_editable_fields()
read_only = get_read_only_fields()
user_required = get_user_required_fields()
system_required = get_system_required_fields()
```
