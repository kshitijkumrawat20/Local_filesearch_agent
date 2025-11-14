# Local File Search Agent Modernization Plan

_Last updated: 2025-11-14_

## 1. Pain point recap

| # | Symptom | Root cause (today) |
|---|---------|--------------------|
| 1 | **Slow cold start / load** | Streamlit spins up a websocket server, imports LangGraph + heavy ML stacks, downloads HF models on first run, and eagerly mounts every drive before rendering the UI. |
| 2 | **"Web-based" feel** | Streamlit requires a browser session and an HTTP server. Even if it runs on localhost, it still behaves like a web app and is awkward to distribute as a self-contained desktop experience. |
| 3 | **Full-disk indexing takes too long** | Indexer walks every directory synchronously, embeds every file into Chroma, and stores only file paths as page content, so you pay embedding cost even if you just need metadata. No persistent watcher means every rebuild is a full rescan. |

## 2. Local-first runtime strategy

| Layer | Recommendation | Why it helps |
|-------|----------------|--------------|
| UI shell | **Tauri** (Rust core + Svelte/React UI) or **Textual** (pure-Python TUI) | Both are lightweight, bundle everything locally, and start in <1s. Tauri lets you ship a polished desktop UI with auto-updates; Textual gives you an in-terminal UI with zero browser dependency. |
| Backend API | **FastAPI/uvicorn** embedded in the same binary, or Rust Axum service when using Tauri | Gives you structured async endpoints for search, indexing, telemetry, and isolates UI from long-running jobs. |
| Packaging | **PyInstaller** for Python-only builds or **Rye/uv + Briefcase** for multi-platform installers | Produce a single .exe/.msi without making the user manage Python or environment variables. |
| Local models | Swap `ChatOpenAI` for **Ollama** (e.g., `llama3.1:8b`) and **sentence-transformers/all-minilm-l6** via `gguf` + `text-embedding-inference` | Removes cloud dependency, eliminates API latency, and makes the app fully offline. |

### Fast cold start checklist

1. **Lazy-load heavy modules** (LangGraph, embedding models) after the UI renders; show a lightweight splash/progress indicator.
2. **Ship pre-downloaded HF models** inside `%APPDATA%/LocalFilesearchAgent/models` and point `cache_folder` there so first-run time is dominated by your installer, not runtime download.
3. **Use `uv` or `pdm`** to pin dependencies and produce lockfiles with pre-built wheels; this avoids long `pip` builds during installation.
4. **Split the agent runtime into a separate worker process** started on demand (e.g., via `multiprocessing` or `SubprocessRunner`). The UI can stay responsive even if the worker is warming models.

## 3. Desktop-local UX options

| Option | Stack | Notes |
|--------|-------|-------|
| **Tauri Desktop** | Rust backend + TypeScript front-end; call Python via `pyo3` or use Rust for indexing | Tiny footprint (~10 MB), GPU-friendly, automatic native menu bars, sandboxed FS access prompts for better security. |
| **Textual + Rich** | Pure Python; runs in terminal; supports docking layouts, mouse, keybindings | Fast, no browser; can still embed `Textual-Web` later if you need remote access. |
| **PySide6/Qt for Python** | Native widgets with QML styling | Good for drag/drop and file explorers; pair with `QtWebEngine` if you still want HTML components. |

All of these eliminate the “open browser tab” workflow while staying 100 % on-device.

## 4. Semantic indexing redesign

### 4.1 Tiered search pipeline

1. **Metadata layer (instant):** Keep the Everything SDK (or Windows Search API) running in the background. Answer filename/path queries directly from its index (<50 ms) and show results immediately.
2. **Full-text layer:** Use `tantivy` (Rust) or `Xapian` to index plain text extracted from files. This gives lightning-fast keyword search without embeddings.
3. **Semantic layer:** Only embed the top *N* candidates from layer 2, chunked by 1–2 KB, and store them in a local vector DB (see below). This reduces embedding volume by 90 %+ while preserving semantic ranking when users need it.

### 4.2 Storage choices

| Need | Recommended engine | Reason |
|------|--------------------|--------|
| On-disk vector store | **LanceDB** or **Qdrant (embedded)** | Both are optimized for local use, support ANN indexes (HNSW) for fast recall, and avoid SQLite locks you see with Chroma.
| Metadata/time-travel | **SQLite (FTS5) + USN journal offsets** | SQLite handles millions of rows with minimal overhead and gives you ACID transactions for metadata updates.

### 4.3 Real-time updates

- Subscribe to the **NTFS USN Journal** or use `watchdog` with `ReadDirectoryChangesW` so you only process changed files.
- Maintain a queue (`sqlite` table or `reddis-lite`) for files that need re-chunking.
- Run a **Rust or Go worker** for text extraction + embedding; Python can dispatch jobs but heavy lifting lives in a compiled binary for speed.

### 4.4 Embedding throughput

- Use `Instructor-xl` or `GTE-large` via **`text-embedding-inference` (TEI)** on GPU/CPU. TEI streams batches efficiently and exposes a REST API, so multiple app components can reuse it.
- Pre-chunk documents with `llama_index.core.node_parser.SentenceWindowNodeParser` to minimize redundant embeddings.
- Cache embeddings per file hash (`blake3`). If the hash hasn’t changed, skip re-embedding entirely.

## 5. Concrete action plan

| Phase | Goals | Key tasks |
|-------|-------|-----------|
| **P0 – Profiling & baselines (1 day)** | Measure actual cold start, crawl speed, and memory footprint | Instrument current `app.py` with `perf_counter`, run `py-spy` to capture import hotspots, log indexing throughput per file type. |
| **P1 – Local shell (3–5 days)** | Replace Streamlit with Textual prototype; keep existing agent backend | Reuse `FileSearchAgent` via an async API, add background worker process, implement key bindings for search/chat. |
| **P2 – Indexer refactor (1–2 weeks)** | Introduce tiered search + watchers | Integrate Everything SDK, add USN watcher, swap Chroma for LanceDB/Qdrant, write migration script for existing metadata. |
| **P3 – Offline LLM stack (ongoing)** | Remove Groq/OpenAI dependency | Set up Ollama server, adjust `config/settings.py` to select local models, update agent prompts to fit new context windows. |
| **P4 – Packaging & DX (2 days)** | Ship a single installer | Create `pyproject.toml` for uv/pdm, add `Makefile` targets, configure PyInstaller/Tauri bundler, add auto-update channel if using Tauri. |

## 6. Additional quality-of-life improvements

- **Fast resume:** Persist LangGraph state and chat history to disk (`sqlite`) so reopening the app restores context instantly.
- **Resource guardrails:** Limit concurrent embeddings to protect HDD/SSD wear; expose a “Pause indexing” toggle in the UI.
- **Observability:** Add `structlog` + rotating file handler to trace indexing batches, embedding speeds, and queue depth for easier troubleshooting.
- **Plugin surface:** Define a TOML-based tool registry so you can drop in new automation scripts without editing `file_tools.py`.

## 7. Immediate next steps

1. Decide between **Tauri** and **Textual** for the first local-only UX—spin up a quick spike to validate startup time.
2. Prototype a **metadata-only Everything integration** so users can search path strings instantly while the semantic layer warms up.
3. Swap Chroma for **LanceDB** in a feature branch and measure ingest speed + query latency on a realistic dataset.
4. Plan the **Ollama/TEI deployment** (port selection, model sizes, GPU requirements) so you can drop the cloud API key dependency.

Adopting this plan will give you sub-second startup, an installer that truly feels local-native, and an indexing pipeline that keeps up with real-time file changes without repeatedly walking the entire disk.
