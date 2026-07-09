# File Organizer Published-Date Artwork and NFO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add File Organizer support for published-date sorting, same-stem episode artwork renaming, and same-stem episode NFO generation.

**Architecture:** Keep the feature inside the existing File Organizer boundary. Backend scan enriches video rows with parsed filename dates and artwork matches; frontend uses those fields for preview and planning; backend precheck/execute validates and moves video, artwork, and NFO as one row-level operation.

**Tech Stack:** Python 3.12, FastAPI, pathlib/shutil/xml.etree, Vue 3 single-file HTML, pytest.

## Global Constraints

- Do not call PornHub during organization.
- Do not require `.info.json` metadata for the first implementation.
- Published date comes from filename prefixes `YYYY-MM-DD` or `YYYYMMDD`.
- Matching artwork suffixes: `.jpg`, `.jpeg`, `.png`, `.webp`.
- Existing File Organizer target filename pattern remains `Actor.S01E02.Chinese Title.ext`.
- Frontend source `frontend/index.html` and served file `static/index.html` must remain synchronized.
- Non-document code changes require version bump before push, but do not push unless the user explicitly says “推送”.

---

### Task 1: Scan Metadata Parsing and Sorting

**Files:**
- Modify: `backend/app/file_organizer.py`
- Test: `test_file_organizer_backend.py`

**Interfaces:**
- Produces: `_parse_published_date_from_name(name: str) -> str | None`
- Produces: `_extract_viewkey_from_name(name: str) -> str | None`
- Produces: `_find_artwork_for_video(video: Path, directory_files: list[Path]) -> Path | None`
- Extends: `scan_videos(source_dir: str, recursive: bool = False, sort: str = "name") -> dict[str, Any]`

- [ ] **Step 1: Write failing backend tests**

Add tests to `test_file_organizer_backend.py`:

```python
def test_scan_videos_parses_filename_published_date_and_artwork(tmp_path, monkeypatch):
    root = tmp_path / "cloud"
    source = root / "待整理"
    source.mkdir(parents=True)
    video = source / "2025-07-16_My_Title_68781106ba7d5.mp4"
    image = source / "2025-07-16_My_Title_68781106ba7d5.jpg"
    video.write_bytes(b"video")
    image.write_bytes(b"image")
    monkeypatch.setenv("CLOUD115_ROOT", str(root))
    import importlib
    import backend.app.file_organizer as fo
    importlib.reload(fo)

    result = fo.scan_videos(str(source), sort="published_date")

    item = result["items"][0]
    assert item["published_date"] == "2025-07-16"
    assert item["published_date_source"] == "filename"
    assert item["artwork_path"] == str(image)
    assert item["artwork_name"] == image.name
    assert item["artwork_suffix"] == ".jpg"


def test_scan_videos_sorts_by_published_date_then_undated_mtime(tmp_path, monkeypatch):
    root = tmp_path / "cloud"
    source = root / "待整理"
    source.mkdir(parents=True)
    newer = source / "2025-02-01_New_aaaa.mp4"
    older = source / "2024-01-01_Old_bbbb.mp4"
    undated = source / "No_Date_cccc.mp4"
    for path in (newer, older, undated):
        path.write_bytes(b"video")
    os.utime(undated, (100, 100))
    monkeypatch.setenv("CLOUD115_ROOT", str(root))
    import importlib
    import backend.app.file_organizer as fo
    importlib.reload(fo)

    result = fo.scan_videos(str(source), sort="published_date")

    assert [item["name"] for item in result["items"]] == [older.name, newer.name, undated.name]


def test_scan_videos_matches_artwork_by_viewkey_when_stem_differs(tmp_path, monkeypatch):
    root = tmp_path / "cloud"
    source = root / "待整理"
    source.mkdir(parents=True)
    video = source / "2025-07-16_Title_68781106ba7d5.mp4"
    image = source / "thumbnail_68781106ba7d5.webp"
    video.write_bytes(b"video")
    image.write_bytes(b"image")
    monkeypatch.setenv("CLOUD115_ROOT", str(root))
    import importlib
    import backend.app.file_organizer as fo
    importlib.reload(fo)

    result = fo.scan_videos(str(source), sort="published_date")

    assert result["items"][0]["artwork_path"] == str(image)
    assert result["items"][0]["artwork_suffix"] == ".webp"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest test_file_organizer_backend.py -q`

Expected: new tests fail because scan items do not expose `published_date` / artwork fields and `published_date` sort is not implemented.

- [ ] **Step 3: Implement scan helpers and sorting**

In `backend/app/file_organizer.py`:

```python
PUBLISHED_DATE_DASH_RE = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(?:[_ .-]|$)")
PUBLISHED_DATE_COMPACT_RE = re.compile(r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?:[_ .-]|$)")
VIEWKEY_RE = re.compile(r"(?P<viewkey>[A-Za-z0-9]{11,16})(?=\.[^.]+$|$)")


def _parse_published_date_from_name(name: str) -> str | None:
    for pattern in (PUBLISHED_DATE_DASH_RE, PUBLISHED_DATE_COMPACT_RE):
        match = pattern.search(name)
        if not match:
            continue
        year = int(match.group("year"))
        month = int(match.group("month"))
        day = int(match.group("day"))
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _extract_viewkey_from_name(name: str) -> str | None:
    match = VIEWKEY_RE.search(name)
    return match.group("viewkey") if match else None


def _find_artwork_for_video(video: Path, directory_files: list[Path]) -> Path | None:
    same_stem = [p for p in directory_files if p.suffix.lower() in METADATA_SUFFIXES and p.stem == video.stem]
    if same_stem:
        return sorted(same_stem, key=lambda p: _natural_key(p.name))[0]
    viewkey = _extract_viewkey_from_name(video.name)
    if not viewkey:
        return None
    matches = [
        p for p in directory_files
        if p.suffix.lower() in METADATA_SUFFIXES and _extract_viewkey_from_name(p.name) == viewkey
    ]
    return sorted(matches, key=lambda p: _natural_key(p.name))[0] if matches else None
```

Update `scan_videos()` to collect source directory files, attach `published_date`, `published_date_source`, `artwork_path`, `artwork_name`, `artwork_suffix`, and sort when `sort == "published_date"`.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python3 -m pytest test_file_organizer_backend.py -q`

Expected: all file organizer backend tests pass.

- [ ] **Step 5: Commit Task 1**

Run:

```bash
git add backend/app/file_organizer.py test_file_organizer_backend.py
git commit -m "feat: detect file organizer published dates"
```

---

### Task 2: Precheck and Execute Artwork/NFO Side Effects

**Files:**
- Modify: `backend/app/file_organizer.py`
- Test: `test_file_organizer_backend.py`

**Interfaces:**
- Produces: `_episode_nfo_xml(title: str, season: int, episode: int, published_date: str | None) -> str`
- Extends: `_validate_video_item(item: dict[str, Any], seen_targets: dict[str, int]) -> dict[str, Any]`
- Extends: `execute_video_moves(payload: dict[str, Any]) -> dict[str, Any]`

- [ ] **Step 1: Write failing tests for precheck and execute**

Add tests to `test_file_organizer_backend.py`:

```python
def test_precheck_rejects_existing_artwork_and_nfo_targets(tmp_path, monkeypatch):
    root = tmp_path / "cloud"
    source_dir = root / "src"
    target_dir = root / "dst"
    source_dir.mkdir(parents=True)
    target_dir.mkdir()
    video = source_dir / "2025-07-16_Title_key.mp4"
    artwork = source_dir / "2025-07-16_Title_key.jpg"
    target_video = target_dir / "Actor.S01E01.标题.mp4"
    target_artwork = target_dir / "Actor.S01E01.标题.jpg"
    target_nfo = target_dir / "Actor.S01E01.标题.nfo"
    video.write_bytes(b"video")
    artwork.write_bytes(b"image")
    target_artwork.write_bytes(b"existing")
    target_nfo.write_text("existing", encoding="utf-8")
    monkeypatch.setenv("CLOUD115_ROOT", str(root))
    import importlib
    import backend.app.file_organizer as fo
    importlib.reload(fo)

    result = fo.precheck_video_moves({
        "confirmed": True,
        "items": [{
            "id": "1",
            "source_path": str(video),
            "target_path": str(target_video),
            "artwork_path": str(artwork),
            "target_artwork_path": str(target_artwork),
            "target_nfo_path": str(target_nfo),
            "nfo": {"title": "标题", "season": 1, "episode": 1, "published_date": "2025-07-16"},
        }],
    })

    assert not result["ok"]
    assert "目标图片已存在" in result["items"][0]["error"] or "目标 NFO 已存在" in result["items"][0]["error"]


def test_execute_moves_video_artwork_and_writes_episode_nfo(tmp_path, monkeypatch):
    root = tmp_path / "cloud"
    source_dir = root / "src"
    target_dir = root / "dst"
    source_dir.mkdir(parents=True)
    target_dir.mkdir()
    video = source_dir / "2025-07-16_Title_68781106ba7d5.mp4"
    artwork = source_dir / "2025-07-16_Title_68781106ba7d5.jpg"
    target_video = target_dir / "Actor.S01E01.中文标题.mp4"
    target_artwork = target_dir / "Actor.S01E01.中文标题.jpg"
    target_nfo = target_dir / "Actor.S01E01.中文标题.nfo"
    video.write_bytes(b"video")
    artwork.write_bytes(b"image")
    monkeypatch.setenv("CLOUD115_ROOT", str(root))
    monkeypatch.setenv("MONITOR_DATA_DIR", str(tmp_path / "data"))
    import importlib
    import backend.app.file_organizer as fo
    importlib.reload(fo)

    result = fo.execute_video_moves({
        "confirmed": True,
        "items": [{
            "id": "1",
            "source_path": str(video),
            "target_path": str(target_video),
            "artwork_path": str(artwork),
            "target_artwork_path": str(target_artwork),
            "target_nfo_path": str(target_nfo),
            "nfo": {"title": "中文标题", "season": 1, "episode": 1, "published_date": "2025-07-16"},
        }],
    })

    assert result["ok"]
    assert target_video.read_bytes() == b"video"
    assert target_artwork.read_bytes() == b"image"
    xml = target_nfo.read_text(encoding="utf-8")
    assert "<title>中文标题</title>" in xml
    assert "<season>1</season>" in xml
    assert "<episode>1</episode>" in xml
    assert "<aired>2025-07-16</aired>" in xml
    assert "<premiered>2025-07-16</premiered>" in xml
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest test_file_organizer_backend.py -q`

Expected: new tests fail because precheck ignores artwork/NFO and execute does not move/write them.

- [ ] **Step 3: Implement validation and execution**

In `backend/app/file_organizer.py`:

- Validate optional `artwork_path` and `target_artwork_path` with `safe_path("cloud115", ...)`.
- Reject existing target artwork with error `目标图片已存在`.
- Reject existing target NFO with error `目标 NFO 已存在`.
- Generate NFO with `xml.etree.ElementTree` or escaped string.
- Move video first, then artwork, then write NFO.
- Only write NFO when `target_nfo_path` and `nfo` are present.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python3 -m pytest test_file_organizer_backend.py -q`

Expected: all backend file organizer tests pass.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add backend/app/file_organizer.py test_file_organizer_backend.py
git commit -m "feat: organize episode artwork and nfo"
```

---

### Task 3: Frontend Controls and Planning Payload

**Files:**
- Modify: `frontend/index.html`
- Modify: `static/index.html`
- Test: `test_file_organizer_frontend.py`

**Interfaces:**
- Consumes scan fields: `published_date`, `artwork_path`, `artwork_name`, `artwork_suffix`.
- Produces planned item fields: `artwork_path`, `target_artwork_path`, `target_nfo_path`, `nfo`.

- [ ] **Step 1: Write failing frontend tests**

Add assertions to `test_file_organizer_frontend.py`:

```python
def test_file_organizer_has_published_date_sort_and_nfo_controls():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert 'label="按发布时间从早到晚" value="published_date"' in html
    assert 'prop="published_date" label="发布时间"' in html
    assert 'label="图片"' in html
    assert '生成每集 NFO' in html
    static = Path("static/index.html").read_text(encoding="utf-8")
    assert 'label="按发布时间从早到晚" value="published_date"' in static
    assert 'prop="published_date" label="发布时间"' in static
    assert '生成每集 NFO' in static


def test_file_organizer_planned_items_include_artwork_and_nfo_payload():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    assert "target_artwork_path" in html
    assert "target_nfo_path" in html
    assert "generateNfo" in html
    assert "published_date" in html
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest test_file_organizer_frontend.py -q`

Expected: tests fail because controls and payload fields are missing.

- [ ] **Step 3: Update frontend and static HTML**

In both `frontend/index.html` and `static/index.html`:

- Add sort option `按发布时间从早到晚` with value `published_date`.
- Add table columns:
  - `prop="published_date" label="发布时间" width="120"`
  - image column showing `artwork_name || '无同名图片'`.
- Add data field `generateNfo:true`.
- Add checkbox in confirm section: `<el-checkbox v-model="generateNfo">生成每集 NFO</el-checkbox>`.
- Update `plannedItems()` to compute `basePath`, target artwork path when `i.artwork_path` exists, and target NFO path when `this.generateNfo` is true.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python3 -m pytest test_file_organizer_frontend.py -q`

Expected: frontend tests pass.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add frontend/index.html static/index.html test_file_organizer_frontend.py
git commit -m "feat: plan file organizer artwork and nfo"
```

---

### Task 4: Full Verification and Version Bump

**Files:**
- Modify: `VERSION`
- Modify: `static/VERSION`
- Modify: `frontend/index.html`
- Modify: `static/index.html`

**Interfaces:**
- Consumes all previous tasks.
- Produces verified local branch ready for user review or push.

- [ ] **Step 1: Bump version**

Read current `VERSION`. Increment minor patch by `0.01`. If current is `1.43`, write `1.44` to `VERSION` and `static/VERSION`, and replace sidebar `v1.43` with `v1.44` in both HTML files.

- [ ] **Step 2: Run full validation**

Run:

```bash
git diff --check
python3 -m py_compile backend/app/file_organizer.py backend/app/routers/file_organizer.py backend/app/main.py
python3 -m pytest -q
```

Expected: no diff whitespace errors, py_compile succeeds, pytest passes.

- [ ] **Step 3: Commit final version/doc updates**

Run:

```bash
git add VERSION static/VERSION frontend/index.html static/index.html
git commit -m "chore: bump version for file organizer automation"
```

If version edits were included in previous task commits, skip this commit and record that version was already committed.

- [ ] **Step 4: Final status**

Run:

```bash
git status --short
git log --oneline -5
```

Expected: clean worktree except intentional untracked local files. Do not push unless the user explicitly says `推送`.
