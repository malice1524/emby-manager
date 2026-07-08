# File Organizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe Emby Manager file organizer for 115 CloudDrive2 video moves, DeepSeek title translation, and STRM metadata copying to 115.

**Architecture:** Add focused backend service modules for settings, DeepSeek translation, path-safe file planning, and execution. Expose them through two FastAPI routers, then wire a dense Vue/Element Plus management page and a bottom sidebar settings page into the existing single-file SPA.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, httpx, pathlib/shutil/os.replace-style filesystem operations, JSON files under `/app/data`, Vue 3 Options API, Vue Router, Element Plus.

## Global Constraints

- 115 root is `/CloudDrive115`.
- Metadata source root is `/strm`.
- Settings/log data root is `/app/data`.
- Docker mounts must include `/vol1/1000/docker/CloudDrive115:/CloudDrive115`, `/vol1/1000/docker/strm/已整理:/strm`, and `./data:/app/data`.
- Settings are saved to `/app/data/settings.json`.
- Saved DeepSeek key takes priority over `DEEPSEEK_API_KEY`; if no saved key exists, use `DEEPSEEK_API_KEY`.
- DeepSeek Base URL defaults to `https://api.deepseek.com`.
- DeepSeek model defaults to `deepseek-chat`.
- Translation batch size defaults to `10`.
- Supported video suffixes are `.mp4 .mkv .avi .mov .wmv .flv .ts .m2ts .webm`.
- Metadata copy suffixes are `.nfo .jpg .jpeg .png .webp`.
- Do not generate STRM files.
- Do not delete videos.
- Do not overwrite videos.
- Do not automatically roll back partial video moves.
- Metadata copy preserves directory structure and overwrites same-name metadata only after precheck and explicit confirmation.
- Every path operation must validate resolved paths stay under the allowed root.
- Frontend changes must be applied to both `frontend/index.html` and `static/index.html`.
- This is a code/feature change; before push, bump version from `1.36` to `1.37` in `VERSION`, `static/VERSION`, `frontend/index.html`, and `static/index.html`.
- Do not push without explicit user permission.

---

## File Structure

Create these backend modules:

- `backend/app/settings_store.py`: read/write `/app/data/settings.json`, mask DeepSeek status, merge env fallback.
- `backend/app/deepseek_client.py`: OpenAI-compatible DeepSeek chat-completions calls and batch title translation.
- `backend/app/file_organizer.py`: path validation, directory browsing, scan/sort, filename generation, video precheck, video execute, metadata precheck, metadata execute, operation logs.
- `backend/app/routers/settings.py`: `/api/settings/deepseek` routes.
- `backend/app/routers/file_organizer.py`: `/api/file-organizer/*` routes.

Modify these existing files:

- `backend/app/main.py`: include new routers.
- `frontend/index.html`: add sidebar links, `FileOrganizer` component, `Settings` component, routes.
- `static/index.html`: mirror frontend changes.
- `docker-compose.yml` and `docker-compose.hub.yml`: document/add mounts for `/CloudDrive115`, `/strm`, `/app/data` where appropriate.
- `VERSION`, `static/VERSION`: bump to `1.37` before final code commit/push.
- `README.md`, `AI_CONTEXT.md`, `PROJECT.md`, `API.md`, `DATABASE.md`: document new settings, APIs, JSON files, mounts, workflows.

Add tests:

- `test_settings_deepseek.py`
- `test_file_organizer_backend.py`
- `test_file_organizer_api.py`
- extend `test_monitor_frontend.py` or add `test_file_organizer_frontend.py`

---

### Task 1: DeepSeek Settings Storage

**Files:**
- Create: `backend/app/settings_store.py`
- Create: `test_settings_deepseek.py`

**Interfaces:**
- Produces: `load_deepseek_settings() -> dict`
- Produces: `save_deepseek_settings(payload: dict) -> dict`
- Produces: `public_deepseek_settings() -> dict`
- Produces: constants `SETTINGS_DATA_DIR`, `SETTINGS_PATH`

- [ ] **Step 1: Write failing settings tests**

Create `test_settings_deepseek.py` with tests that monkeypatch `MONITOR_DATA_DIR` to a temp directory and verify defaults, env fallback, saved-key priority, omitted-key preservation, empty-key clearing, and no key returned publicly.

Use assertions for this exact public shape:

```python
{
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "batch_size": 10,
    "api_key_configured": False,
    "api_key_source": "none",
}
```

- [ ] **Step 2: Run failing tests**

Run: `python3 -m pytest test_settings_deepseek.py -q`
Expected: FAIL because `backend.app.settings_store` does not exist.

- [ ] **Step 3: Implement settings store**

Implement `backend/app/settings_store.py` using `Path(os.getenv("MONITOR_DATA_DIR", "/data")) / "settings.json"`. Use atomic write via temp file and replace. Return full key only from `load_deepseek_settings()` for backend use; never from `public_deepseek_settings()`.

Rules:

```text
base_url default: https://api.deepseek.com
model default: deepseek-chat
batch_size default: 10, coerced to int >= 1
api_key omitted in save: keep existing saved key
api_key == "": clear saved key
api_key non-empty: save it
load effective key: saved key first, then DEEPSEEK_API_KEY, then empty
```

- [ ] **Step 4: Verify settings tests pass**

Run: `python3 -m pytest test_settings_deepseek.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/app/settings_store.py test_settings_deepseek.py
git commit -m "feat: add DeepSeek settings storage"
```

---

### Task 2: DeepSeek Translation Client

**Files:**
- Create: `backend/app/deepseek_client.py`
- Modify: `test_settings_deepseek.py` or create `test_deepseek_client.py`

**Interfaces:**
- Consumes: `load_deepseek_settings() -> dict`
- Produces: `contains_chinese(text: str) -> bool`
- Produces: `sanitize_filename_part(text: str) -> str`
- Produces: `async translate_titles(titles: list[dict], settings: dict | None = None) -> list[dict]`

- [ ] **Step 1: Write failing client tests**

Create tests for:

```text
contains_chinese("中文标题") is True
contains_chinese("Beautiful Girl") is False
sanitize_filename_part removes or spaces / \ : * ? " < > |
translate_titles skips rows whose title contains Chinese
translate_titles returns row-level errors when API key is missing
```

Mock `httpx.AsyncClient.post` for success and malformed response cases. Expected translation row shape:

```python
{"id": "row-1", "ok": True, "title": "美丽女孩在家中", "error": ""}
```

- [ ] **Step 2: Run failing tests**

Run: `python3 -m pytest test_deepseek_client.py -q`
Expected: FAIL because the client does not exist.

- [ ] **Step 3: Implement DeepSeek client**

Implement an OpenAI-compatible POST to `{base_url.rstrip('/')}/chat/completions` with model, messages, and JSON-only instruction. The prompt must ask for natural Chinese media-library titles and structured JSON mapping IDs to titles. Never log or return the key.

For missing API key, return per-row failures instead of raising for the whole request.

- [ ] **Step 4: Verify tests pass**

Run: `python3 -m pytest test_deepseek_client.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/app/deepseek_client.py test_deepseek_client.py
git commit -m "feat: add DeepSeek title translator"
```

---

### Task 3: File Organizer Core Logic

**Files:**
- Create: `backend/app/file_organizer.py`
- Create: `test_file_organizer_backend.py`

**Interfaces:**
- Produces: `safe_path(root_key: str, value: str | None) -> Path`
- Produces: `browse_directory(root_key: str, path: str | None) -> dict`
- Produces: `scan_videos(source_dir: str, recursive: bool, sort: str) -> dict`
- Produces: `build_final_filename(actor: str, season: int, episode: int, title: str, suffix: str) -> str`
- Produces: `precheck_video_moves(payload: dict) -> dict`
- Produces: `execute_video_moves(payload: dict) -> dict`
- Produces: `precheck_metadata_copy(payload: dict) -> dict`
- Produces: `execute_metadata_copy(payload: dict) -> dict`

- [ ] **Step 1: Write failing core tests**

Use temp directories and monkeypatch root constants to test:

```text
path traversal is blocked
browse returns child directories only
scan filters supported video suffixes
recursive scan includes nested videos
natural sort puts 2 before 10
mtime sort orders oldest first
organized names are marked suspected_organized and selected false
filename generation creates Actor.S01E05.Title.mp4
invalid filename chars are sanitized
precheck blocks existing target video
precheck blocks duplicate target path in task
execute moves successful rows and keeps failed rows failed without rollback
metadata precheck preserves Season 1 structure and detects overwrite
metadata execute copies .nfo/.jpg/.jpeg/.png/.webp only and skips .strm/videos
```

- [ ] **Step 2: Run failing core tests**

Run: `python3 -m pytest test_file_organizer_backend.py -q`
Expected: FAIL because `backend.app.file_organizer` does not exist.

- [ ] **Step 3: Implement core logic**

Implement with `pathlib.Path.resolve()`, root-key mapping `cloud115 -> /CloudDrive115`, `strm -> /strm`, and logs under `Path(os.getenv("MONITOR_DATA_DIR", "/data")) / "file-organizer" / "logs"`.

Use `Path.rename()` or `shutil.move()` for video moves. Do not overwrite videos: if target exists, mark row failed.

Use `shutil.copy2()` for metadata files. Preserve relative path from metadata source to target. Overwrite matching metadata files only in metadata execute after confirm flag is present.

- [ ] **Step 4: Verify core tests pass**

Run: `python3 -m pytest test_file_organizer_backend.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/app/file_organizer.py test_file_organizer_backend.py
git commit -m "feat: add file organizer core logic"
```

---

### Task 4: Settings and File Organizer APIs

**Files:**
- Create: `backend/app/routers/settings.py`
- Create: `backend/app/routers/file_organizer.py`
- Modify: `backend/app/main.py`
- Create: `test_file_organizer_api.py`

**Interfaces:**
- Consumes all functions from Tasks 1-3.
- Produces routes:
  - `GET /api/settings/deepseek`
  - `PUT /api/settings/deepseek`
  - `POST /api/settings/deepseek/test-translation`
  - `GET /api/file-organizer/browse`
  - `POST /api/file-organizer/scan`
  - `POST /api/file-organizer/translate`
  - `POST /api/file-organizer/precheck`
  - `POST /api/file-organizer/execute`
  - `POST /api/file-organizer/metadata/precheck`
  - `POST /api/file-organizer/metadata/execute`

- [ ] **Step 1: Write failing API tests**

Use `fastapi.testclient.TestClient` and monkeypatch temp roots. Test:

```text
GET settings does not return api_key
PUT settings accepts api_key omission and empty clearing
browse rejects paths outside root
scan returns video rows
precheck returns conflict rows
metadata precheck returns overwrite rows
```

Mock DeepSeek translation route to avoid network.

- [ ] **Step 2: Run failing API tests**

Run: `python3 -m pytest test_file_organizer_api.py -q`
Expected: FAIL because routes do not exist.

- [ ] **Step 3: Implement routers and include them**

Add `from .routers import settings, file_organizer` in `backend/app/main.py` and include both routers.

Use Pydantic models for request bodies. Translate `HTTPException` details into concise Chinese messages. Do not return secrets.

- [ ] **Step 4: Verify API tests pass**

Run: `python3 -m pytest test_file_organizer_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add backend/app/main.py backend/app/routers/settings.py backend/app/routers/file_organizer.py test_file_organizer_api.py
git commit -m "feat: expose file organizer APIs"
```

---

### Task 5: Frontend Settings Page

**Files:**
- Modify: `frontend/index.html`
- Modify: `static/index.html`
- Modify or create: `test_file_organizer_frontend.py`

**Interfaces:**
- Consumes settings APIs from Task 4.
- Produces frontend route `#/settings`.

- [ ] **Step 1: Write failing frontend assertions**

Add tests that read both HTML files and assert:

```text
#/settings link exists
设置 appears after 文件整理 or at sidebar bottom
DeepSeek API Key appears
测试翻译 appears
/api/settings/deepseek appears
source and static HTML contain the same settings route markers
```

- [ ] **Step 2: Run failing frontend tests**

Run: `python3 -m pytest test_file_organizer_frontend.py -q`
Expected: FAIL because settings UI does not exist.

- [ ] **Step 3: Implement Settings component**

Add a `Settings` Vue component with fields for API Key, Base URL, model, batch size, save button, and test translation input/result. Load settings on mount. Mask key status; do not display full saved key. Add sidebar bottom link and route.

- [ ] **Step 4: Mirror to static HTML**

Copy equivalent changes from `frontend/index.html` to `static/index.html`.

- [ ] **Step 5: Verify frontend tests pass**

Run: `python3 -m pytest test_file_organizer_frontend.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add frontend/index.html static/index.html test_file_organizer_frontend.py
git commit -m "feat: add DeepSeek settings page"
```

---

### Task 6: Frontend File Organizer Page

**Files:**
- Modify: `frontend/index.html`
- Modify: `static/index.html`
- Modify: `test_file_organizer_frontend.py`

**Interfaces:**
- Consumes file organizer APIs from Task 4.
- Produces frontend route `#/file-organizer`.

- [ ] **Step 1: Extend failing frontend assertions**

Assert both HTML files contain:

```text
#/file-organizer
文件整理
选择 115 源文件夹
扫描视频
DeepSeek 翻译标题
预检查
执行移动
元数据复制到 115
/api/file-organizer/scan
/api/file-organizer/metadata/precheck
```

- [ ] **Step 2: Run failing frontend tests**

Run: `python3 -m pytest test_file_organizer_frontend.py -q`
Expected: FAIL for missing file organizer UI.

- [ ] **Step 3: Implement FileOrganizer component**

Add one dense management page with collapsible sections:

```text
1. source/target path browse or paste
2. scan options and results table
3. translation action and row-level translation status
4. editable final filename table, row order controls, confirmed checkbox
5. precheck result table
6. execute result table and retry failed rows
7. metadata source/target selection, precheck list, execute copy
```

Actions must stay disabled until required previous state exists. Keep warnings visible for conflicts, failed translation, unconfirmed execution, and overwrite metadata.

- [ ] **Step 4: Mirror to static HTML**

Copy equivalent changes from `frontend/index.html` to `static/index.html`.

- [ ] **Step 5: Verify frontend tests pass**

Run: `python3 -m pytest test_file_organizer_frontend.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add frontend/index.html static/index.html test_file_organizer_frontend.py
git commit -m "feat: add file organizer interface"
```

---

### Task 7: Documentation, Compose, Version, and Full Verification

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docker-compose.hub.yml`
- Modify: `README.md`
- Modify: `AI_CONTEXT.md`
- Modify: `PROJECT.md`
- Modify: `API.md`
- Modify: `DATABASE.md`
- Modify: `VERSION`
- Modify: `static/VERSION`
- Modify: `frontend/index.html`
- Modify: `static/index.html`

**Interfaces:**
- Consumes all implemented routes and workflows.
- Produces documented deployment and usage guidance.

- [ ] **Step 1: Update deployment docs and compose**

Document and add/example these mounts:

```yaml
- /vol1/1000/docker/CloudDrive115:/CloudDrive115
- /vol1/1000/docker/strm/已整理:/strm
- ./data:/app/data
```

Document `DEEPSEEK_API_KEY` env fallback.

- [ ] **Step 2: Update API and data docs**

Add `/api/settings/deepseek` and `/api/file-organizer/*` sections to `API.md`. Add `/app/data/settings.json` and `/app/data/file-organizer/logs/*.json` to `DATABASE.md`. Update `PROJECT.md` and `AI_CONTEXT.md` with the new feature overview and safety rules.

- [ ] **Step 3: Bump version to 1.37**

Change:

```text
VERSION
static/VERSION
frontend/index.html sidebar v1.36 -> v1.37
static/index.html sidebar v1.36 -> v1.37
```

- [ ] **Step 4: Run full verification**

Run:

```bash
git diff --check
python3 -m py_compile backend/app/config.py backend/app/main.py backend/app/settings_store.py backend/app/deepseek_client.py backend/app/file_organizer.py backend/app/routers/settings.py backend/app/routers/file_organizer.py
python3 -m pytest test_settings_deepseek.py test_deepseek_client.py test_file_organizer_backend.py test_file_organizer_api.py test_file_organizer_frontend.py test_monitor_frontend.py test_api_smoke.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit final integration**

Run:

```bash
git add docker-compose.yml docker-compose.hub.yml README.md AI_CONTEXT.md PROJECT.md API.md DATABASE.md VERSION static/VERSION frontend/index.html static/index.html
git commit -m "docs: document file organizer deployment"
```

- [ ] **Step 6: Stop before push**

Do not push. Ask the user for explicit push permission after summarizing commits and verification output.

---

## Self-Review

Spec coverage:

- Sidebar `文件整理` and bottom `设置`: Tasks 5-6.
- DeepSeek settings and test translation: Tasks 1, 2, 4, 5.
- `/app/data/settings.json` and env fallback: Tasks 1 and 7.
- 115 internal video scan/translate/confirm/precheck/move/logs: Tasks 2, 3, 4, 6.
- `/strm` metadata copy to `/CloudDrive115`, preserve `Season 1`, overwrite metadata after confirmation: Tasks 3, 4, 6.
- Path root safety: Task 3 and API tests in Task 4.
- No video overwrite/delete/rollback: Task 3 tests and execution rules.
- Documentation and compose mounts: Task 7.

Placeholder scan: no TBD/TODO placeholders remain; each task has concrete file paths, interfaces, commands, and expected outcomes.

Type consistency: settings functions, DeepSeek functions, file organizer functions, and routes are named consistently across tasks.
