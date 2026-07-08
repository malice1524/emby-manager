# File Organizer and DeepSeek Settings Design

Date: 2026-07-08
Project: Emby Manager
Status: approved design draft

## Purpose

Add a file organizer workflow to Emby Manager for 115 cloud-drive mounted content. The first implementation focuses on organizing real video files inside the CloudDrive2 115 mount, plus a separate metadata-copy tool that copies already prepared local metadata from the existing STRM library to the matching 115 location.

The feature must avoid destructive behavior: no video overwrite, no delete, no automatic rollback, and every real move/copy operation requires precheck and user confirmation.

## Scope

### In scope

- Add a sidebar entry named `文件整理`.
- Add a sidebar entry named `设置` at the bottom of all sidebar functions.
- Add DeepSeek configuration in the settings page.
- Save settings in `/app/data/settings.json`, with environment fallback for `DEEPSEEK_API_KEY`.
- Add DeepSeek test translation support.
- Add a 115-internal video organize workflow:
  - source folder under `/CloudDrive115`
  - target folder under `/CloudDrive115`
  - scan video files
  - translate non-Chinese titles with DeepSeek
  - confirm/edit final names in a table
  - precheck
  - move/rename files using the mounted filesystem
  - save operation logs
- Add a metadata copy workflow:
  - source folder under `/strm`
  - target folder under `/CloudDrive115`
  - copy only NFO/image metadata
  - preserve directory structure
  - overwrite same-name metadata files only after confirmation

### Out of scope

- Fly NAS local-to-115 file moving. This will be designed later as a separate function.
- STRM generation.
- Video deletion.
- Video overwrite.
- Automatic rollback after partial success.
- Full user authentication/authorization changes.

## Deployment Paths

The Docker container needs these mounts:

```yaml
volumes:
  - /vol1/1000/docker/CloudDrive115:/CloudDrive115
  - /vol1/1000/docker/strm/已整理:/strm
  - ./data:/app/data
```

Application roots:

```text
115 root: /CloudDrive115
metadata source root: /strm
settings/log data root: /app/data
```

All file operations must be constrained to these roots using resolved-path validation to prevent path traversal.

## Sidebar and Navigation

Add two frontend routes/views:

```text
文件整理
设置
```

`设置` must be rendered at the bottom of the sidebar after all existing feature entries.

The existing monitor/config page behavior should not be removed. This new settings page is for DeepSeek-related configuration only in this design.

## Settings Page

### Fields

The settings page contains:

```text
DeepSeek API Key
DeepSeek Base URL
DeepSeek model
translation batch size
```

Defaults:

```text
base URL: https://api.deepseek.com
model: deepseek-chat
translation batch size: 10
```

API key priority:

1. API key saved in `/app/data/settings.json`.
2. Environment variable `DEEPSEEK_API_KEY`.

The UI must never show the full saved key. It should show configured/unconfigured state and may show a masked value.

### Test Translation

The settings page provides a test translation tool:

- user enters one test title
- backend calls DeepSeek using the current settings
- backend returns a natural Chinese title
- errors show actionable messages without leaking API keys

## Settings Storage

Settings are stored in:

```text
/app/data/settings.json
```

Expected shape:

```json
{
  "deepseek": {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "batch_size": 10
  }
}
```

If the key is omitted or empty, backend uses `DEEPSEEK_API_KEY` from the environment. Secrets must not be printed to logs or returned by GET responses.

## File Organizer Page

The page uses a single-screen workflow with collapsible steps. Current step is expanded; completed steps can be reviewed; unavailable future steps are disabled.

Steps:

```text
1. 选择 115 源文件夹和目标文件夹
2. 扫描视频
3. DeepSeek 翻译标题
4. 表格确认最终文件名
5. 预检查
6. 执行移动
7. 元数据复制到 115
```

The metadata copy section is independent and can be used separately from the video move workflow.

## 115 Folder Selection

Both source and target selectors support:

- browsing folders one level at a time
- manual path paste

Video organize source and target paths must be under:

```text
/CloudDrive115
```

Metadata copy source must be under:

```text
/strm
```

Metadata copy target must be under:

```text
/CloudDrive115
```

## Video Scan

Supported video extensions:

```text
.mp4 .mkv .avi .mov .wmv .flv .ts .m2ts .webm
```

Scan options:

- scan current folder only or recursively scan subfolders
- sort by natural filename
- sort by modified time from oldest to newest
- allow manual up/down adjustment in the table

The final table order determines episode numbering.

Files that already look organized should still be shown but marked `疑似已整理` and default to unchecked.

## Translation Rules

Only the title portion is translated. The extension is never sent to DeepSeek.

Example:

```text
Beautiful Girl At Home 1080p.mp4
```

Translation input:

```text
Beautiful Girl At Home 1080p
```

If the title already contains Chinese, do not call DeepSeek. Use the original title as the proposed Chinese title and allow manual editing.

For non-Chinese titles, DeepSeek should return a natural Chinese media-library title rather than strict literal translation. It may remove obvious meaningless advertising words when producing the Chinese title.

Translation runs in batches. Batch size comes from DeepSeek settings and defaults to 10.

If translation fails for a file, mark that row in red. The user must manually fill the Chinese title before precheck/execution can pass.

## Naming Rules

Final filename format is fixed:

```text
演员名称.S01E01.中文标题.原扩展名
```

Rules:

- separator is always `.`
- actor name defaults from target folder name
- actor name can be manually edited
- season number is user-entered, e.g. `1` becomes `S01`
- episode number supports two modes:
  - start from `E01` according to current table order
  - user-entered start episode, e.g. `5` becomes `E05` then increments
- invalid filename characters are automatically removed or replaced with spaces:

```text
/ \ : * ? " < > |
```

If the `auto create actor folder` option is enabled, create or reuse a target child folder named after the actor field. If the folder already exists, use it directly.

## Confirmation Table

The table must show enough detail before moving files:

```text
selected
original filename
source path
translation input
Chinese title
actor name
season/episode
final filename
target path
status/conflict messages
```

The user can edit at least:

- Chinese title
- actor name
- season
- start episode mode/value
- final filename or fields that generate it
- row order
- selected rows

Target filename conflict must be marked in red. Conflict rows cannot be executed until manually fixed. Video files are never overwritten.

The user must explicitly confirm the table is correct before execution is enabled.

## Precheck

Provide a `预检查` button. Formal execution also runs precheck again.

Precheck validates:

- source files still exist
- source files are under `/CloudDrive115`
- target folder is under `/CloudDrive115`
- target folder can be written or created
- final filename is legal
- no target video conflict
- no duplicate target path inside the current task
- no failed or missing translation remains
- user confirmation is present

Precheck returns per-row status plus overall pass/fail.

## Execution

Execution uses filesystem move/rename so CloudDrive2 handles 115-internal movement:

```text
source path -> target path
```

Behavior:

- move selected rows only
- no delete operation beyond normal move semantics
- no video overwrite
- partial success is allowed
- successful rows stay successful
- failed rows remain in the table and can be edited/rechecked/retried
- no automatic rollback

## Logs

Save operation logs under:

```text
/app/data/file-organizer/logs/
```

Each execution should write a timestamped JSON log with:

```text
task type
execution time
source root/path
target root/path
actor name
season/start episode options
per-file source path
per-file target path
original filename
translated title
final filename
success/failure
error reason
```

The UI should show execution results immediately after execution.

## Metadata Copy Workflow

Add an independent section at the bottom of the file organizer page.

Inputs:

```text
metadata source folder: browse/paste under /strm
115 target folder: browse/paste under /CloudDrive115
```

Copied file types:

```text
.nfo .jpg .jpeg .png .webp
```

Do not copy:

```text
.strm
video files
other files
```

Preserve directory structure. If the source contains `Season 1`, the target should create or reuse `Season 1` and copy matching metadata files inside it.

Example source:

```text
/strm/PornHub/Sienna Moore/
  tvshow.nfo
  poster.jpg
  Season 1/
    Sienna Moore.S01E01.xxx.nfo
    Sienna Moore.S01E01.xxx.jpg
    Sienna Moore.S01E01.xxx.strm
```

Example target:

```text
/CloudDrive115/PornHub/Sienna Moore/
  tvshow.nfo
  poster.jpg
  Season 1/
    Sienna Moore.S01E01.xxx.nfo
    Sienna Moore.S01E01.xxx.jpg
```

Same-name metadata files are overwritten, but only after precheck and explicit user confirmation.

Metadata precheck shows:

- files to copy
- files that will overwrite existing files
- folders that will be created or reused
- skipped files, if any

## Backend API Design

Suggested new routers:

```text
backend/app/routers/settings.py
backend/app/routers/file_organizer.py
```

Register both in `backend/app/main.py`.

### Settings APIs

```http
GET /api/settings/deepseek
```

Returns non-secret settings and key status.

```http
PUT /api/settings/deepseek
Content-Type: application/json
```

Saves DeepSeek settings. If `api_key` is omitted, keep the existing saved key. If `api_key` is an empty string, clear the saved key so the backend falls back to `DEEPSEEK_API_KEY`. The response must not echo the key.

```http
POST /api/settings/deepseek/test-translation
Content-Type: application/json

{"title":"Beautiful Girl At Home 1080p"}
```

Returns translated Chinese title or an error.

### File Organizer APIs

```http
GET /api/file-organizer/browse?root=cloud115&path=/CloudDrive115/...
```

`root` is one of:

```text
cloud115
strm
```

Returns current path, parent path where allowed, and child directories.

```http
POST /api/file-organizer/scan
```

Scans video files under a 115 source folder with recursive/sort options.

```http
POST /api/file-organizer/translate
```

Translates selected non-Chinese titles in batches using DeepSeek.

```http
POST /api/file-organizer/precheck
```

Prechecks planned video moves.

```http
POST /api/file-organizer/execute
```

Runs planned video moves after precheck/confirmation.

```http
POST /api/file-organizer/metadata/precheck
```

Prechecks metadata copy.

```http
POST /api/file-organizer/metadata/execute
```

Copies metadata after confirmation.

Request/response schemas should include per-row IDs so the frontend can preserve row order and update only changed rows.

## DeepSeek Client

Add a small backend helper for DeepSeek chat-completions calls. It should:

- use OpenAI-compatible `/chat/completions` style endpoint under the configured base URL
- apply reasonable timeouts
- parse JSON responses defensively
- never log API keys
- produce stable per-title results for batch input
- return row-level failures where possible

The translation prompt should request natural Chinese titles suitable for media-library filenames and should return structured JSON so the backend can map translations back to rows.

## Error Handling

User-facing errors should identify the operation and next action, for example:

- DeepSeek not configured
- DeepSeek request failed
- source folder not found
- target folder not writable
- target filename already exists
- path is outside allowed root
- CloudDrive2 move failed

Errors must not include secrets.

## Frontend Implementation Notes

The current project uses a single Vue 3/Element Plus HTML SPA in both:

```text
frontend/index.html
static/index.html
```

Any frontend implementation must update both files consistently.

The file organizer should use dense management UI rather than marketing layout:

- compact path selectors
- tables for file confirmation
- tags/status labels for warning/conflict states
- primary actions disabled until precheck and confirmation pass
- destructive-looking actions avoided because the workflow does not delete files

## Tests

Recommended tests:

- settings storage reads/writes without returning secrets
- environment fallback for `DEEPSEEK_API_KEY`
- path validation blocks traversal and paths outside `/CloudDrive115` or `/strm`
- video scan filters supported extensions only
- natural filename and mtime sorting behavior
- Chinese-title detection skips DeepSeek
- filename generation for actor/season/episode/title/ext
- invalid filename character sanitization
- precheck detects source missing, duplicate target, existing target conflict, missing translation
- execute moves successful rows and preserves failed rows without rollback
- metadata precheck preserves directory structure and reports overwrites
- metadata execute copies only `.nfo/.jpg/.jpeg/.png/.webp` and does not copy `.strm`
- frontend static/source files remain synchronized for new sidebar/routes

## Documentation Updates During Implementation

When implementation begins, update these docs as part of the code change:

```text
AI_CONTEXT.md
PROJECT.md
API.md
DATABASE.md
README.md
```

Because this current change is only a design document, it does not require a version bump.
