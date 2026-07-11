import json
import os
import re
import shutil
from datetime import datetime
from xml.sax.saxutils import escape
from pathlib import Path
from typing import Any

VIDEO_SUFFIXES = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".ts", ".m2ts", ".webm"}
METADATA_SUFFIXES = {".nfo", ".jpg", ".jpeg", ".png", ".webp"}
ORGANIZED_RE = re.compile(r"^.+\.S\d{2}E\d{2,}\..+\.[^.]+$", re.I)
EPISODE_RE = re.compile(r"\.S(?P<season>\d{2})E(?P<episode>\d{2,})\.", re.I)
PUBLISHED_DATE_DASH_RE = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(?:[_ .-]|$)")
PUBLISHED_DATE_COMPACT_RE = re.compile(r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?:[_ .-]|$)")
VIEWKEY_RE = re.compile(r"(?P<viewkey>[A-Za-z0-9]{11,16})(?=\.[^.]+$|$)")
INVALID_FILENAME_CHARS_RE = re.compile(r"[/\\:*?\"<>|]+")

def _first_existing_root(values: list[str | None]) -> Path:
    candidates = [Path(value).expanduser() for value in values if value]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return candidates[0]


ROOTS = {
    "cloud115": _first_existing_root([os.getenv("CLOUD115_ROOT"), "/CloudDrive115", "/vol1/1000/docker/CloudDrive115/CloudDrive"]),
    "strm": _first_existing_root([os.getenv("NFO_MEDIA_ROOT"), os.getenv("STRM_ROOT"), "/vol1/1000/docker/strm", "/strm"]),
}
DATA_ROOT = Path(os.getenv("MONITOR_DATA_DIR", "/data"))


def _natural_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def _parse_published_date_from_name(name: str) -> str | None:
    for pattern in (PUBLISHED_DATE_DASH_RE, PUBLISHED_DATE_COMPACT_RE):
        match = pattern.search(name)
        if not match:
            continue
        try:
            return datetime(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            ).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _extract_viewkey_from_name(name: str) -> str | None:
    match = VIEWKEY_RE.search(name)
    return match.group("viewkey") if match else None


def _find_artwork_for_video(video: Path, directory_files: list[Path]) -> Path | None:
    same_stem = [
        path for path in directory_files
        if path.is_file() and path.suffix.lower() in METADATA_SUFFIXES and path.stem == video.stem
    ]
    if same_stem:
        return sorted(same_stem, key=lambda path: _natural_key(path.name))[0]
    viewkey = _extract_viewkey_from_name(video.name)
    if not viewkey:
        return None
    matches = [
        path for path in directory_files
        if path.is_file()
        and path.suffix.lower() in METADATA_SUFFIXES
        and _extract_viewkey_from_name(path.name) == viewkey
    ]
    return sorted(matches, key=lambda path: _natural_key(path.name))[0] if matches else None


def _root(root_key: str) -> Path:
    if root_key not in ROOTS:
        raise ValueError("未知根目录")
    return ROOTS[root_key].resolve()


def safe_path(root_key: str, value: str | None) -> Path:
    root = _root(root_key)
    path = Path(value).expanduser().resolve() if value else root
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError(f"路径必须位于允许根目录内: {root}")
    return path


def browse_directory(root_key: str, path: str | None = None) -> dict[str, Any]:
    current = safe_path(root_key, path)
    if not current.exists() or not current.is_dir():
        raise FileNotFoundError("目录不存在")
    root = _root(root_key)
    directories = []
    for child in current.iterdir():
        if child.is_dir():
            directories.append({"name": child.name, "path": str(child)})
    directories.sort(key=lambda item: _natural_key(item["name"]))
    parent = str(current.parent) if current != root and current.parent.resolve().is_relative_to(root) else ""
    return {"root": str(root), "path": str(current), "parent": parent, "directories": directories}


def scan_videos(source_dir: str, recursive: bool = False, sort: str = "name") -> dict[str, Any]:
    source = safe_path("cloud115", source_dir)
    if not source.exists() or not source.is_dir():
        raise FileNotFoundError("源目录不存在")
    iterator = source.rglob("*") if recursive else source.iterdir()
    paths = [path for path in iterator]
    files_by_parent: dict[Path, list[Path]] = {}
    for path in paths:
        if path.is_file():
            files_by_parent.setdefault(path.parent, []).append(path)
    items = []
    for path in paths:
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES:
            stat = path.stat()
            suspected = bool(ORGANIZED_RE.match(path.name))
            title = path.stem
            published_date = _parse_published_date_from_name(path.name)
            artwork = _find_artwork_for_video(path, files_by_parent.get(path.parent, []))
            items.append({
                "id": str(len(items) + 1),
                "name": path.name,
                "path": str(path),
                "relative_path": str(path.relative_to(source)),
                "title": title,
                "suffix": path.suffix,
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "published_date": published_date,
                "published_date_source": "filename" if published_date else "",
                "artwork_path": str(artwork) if artwork else "",
                "artwork_name": artwork.name if artwork else "",
                "artwork_suffix": artwork.suffix if artwork else "",
                "suspected_organized": suspected,
                "selected": not suspected,
            })
    if sort == "mtime":
        items.sort(key=lambda item: (item["mtime"], _natural_key(item["name"]), _natural_key(item["relative_path"])))
    elif sort == "published_date":
        items.sort(key=lambda item: (
            0 if item.get("published_date") else 1,
            item.get("published_date") or item["mtime"],
            _natural_key(item["name"]),
            _natural_key(item["relative_path"]),
        ))
    else:
        items.sort(key=lambda item: (_natural_key(item["name"]), _natural_key(item["relative_path"])))
    for index, item in enumerate(items, start=1):
        item["id"] = str(index)
    return {"source_dir": str(source), "items": items}


def sanitize_filename_part(text: str) -> str:
    cleaned = INVALID_FILENAME_CHARS_RE.sub(" ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned


def build_final_filename(actor: str, season: int, episode: int, title: str, suffix: str) -> str:
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return f"{sanitize_filename_part(actor)}.S{int(season):02d}E{int(episode):02d}.{sanitize_filename_part(title)}{suffix}"


def _episode_nfo_xml(title: str, season: int, episode: int, published_date: str | None = None, plot: str | None = None) -> str:
    lines = [
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>',
        "<episodedetails>",
        f"  <title>{escape(title or '')}</title>",
        f"  <season>{int(season)}</season>",
        f"  <episode>{int(episode)}</episode>",
    ]
    if published_date:
        lines.append(f"  <aired>{escape(published_date)}</aired>")
        lines.append(f"  <premiered>{escape(published_date)}</premiered>")
    if plot:
        lines.append(f"  <plot>{escape(plot)}</plot>")
    lines.append("</episodedetails>")
    return "\n".join(lines) + "\n"


def suggest_next_episode(target_dir: str, season: int) -> dict[str, Any]:
    target = safe_path("cloud115", target_dir)
    if not target.exists() or not target.is_dir():
        raise FileNotFoundError("目标目录不存在")
    season_num = int(season or 1)
    episodes = []
    for path in target.iterdir():
        if not path.is_file() or path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        match = EPISODE_RE.search(path.name)
        if not match:
            continue
        if int(match.group("season")) == season_num:
            episodes.append(int(match.group("episode")))
    max_episode = max(episodes) if episodes else 0
    return {
        "target_dir": str(target),
        "season": season_num,
        "max_episode": max_episode,
        "next_episode": max_episode + 1,
        "matched_count": len(episodes),
    }


def _validate_video_item(item: dict[str, Any], seen_targets: dict[str, int]) -> dict[str, Any]:
    row_id = str(item.get("id") or "")
    try:
        source = safe_path("cloud115", str(item.get("source_path") or ""))
        target = safe_path("cloud115", str(item.get("target_path") or ""))
        artwork_source = safe_path("cloud115", str(item.get("artwork_path") or "")) if item.get("artwork_path") else None
        artwork_target = safe_path("cloud115", str(item.get("target_artwork_path") or "")) if item.get("target_artwork_path") else None
        nfo_target = safe_path("cloud115", str(item.get("target_nfo_path") or "")) if item.get("target_nfo_path") else None
    except ValueError as exc:
        return {"id": row_id, "ok": False, "error": str(exc)}
    for candidate in (target, artwork_target, nfo_target):
        if candidate is None:
            continue
        target_key = str(candidate)
        seen_targets[target_key] = seen_targets.get(target_key, 0) + 1
    if not source.exists() or not source.is_file():
        return {"id": row_id, "ok": False, "error": "源文件不存在"}
    if source.suffix.lower() not in VIDEO_SUFFIXES:
        return {"id": row_id, "ok": False, "error": "不是支持的视频文件"}
    if target.exists():
        return {"id": row_id, "ok": False, "error": "目标文件已存在"}
    if INVALID_FILENAME_CHARS_RE.search(target.name):
        return {"id": row_id, "ok": False, "error": "目标文件名包含非法字符"}
    row = {"id": row_id, "ok": True, "error": "", "source_path": str(source), "target_path": str(target)}
    if artwork_source or artwork_target:
        if not artwork_source or not artwork_target:
            return {"id": row_id, "ok": False, "error": "图片源和目标必须同时提供"}
        if not artwork_source.exists() or not artwork_source.is_file():
            return {"id": row_id, "ok": False, "error": "图片源文件不存在"}
        if artwork_source.suffix.lower() not in METADATA_SUFFIXES:
            return {"id": row_id, "ok": False, "error": "不是支持的图片文件"}
        if artwork_target.exists():
            return {"id": row_id, "ok": False, "error": "目标图片已存在"}
        if INVALID_FILENAME_CHARS_RE.search(artwork_target.name):
            return {"id": row_id, "ok": False, "error": "目标图片名包含非法字符"}
        row["artwork_path"] = str(artwork_source)
        row["target_artwork_path"] = str(artwork_target)
    if nfo_target:
        if nfo_target.exists():
            return {"id": row_id, "ok": False, "error": "目标 NFO 已存在"}
        if nfo_target.suffix.lower() != ".nfo":
            return {"id": row_id, "ok": False, "error": "目标 NFO 必须使用 .nfo 后缀"}
        if INVALID_FILENAME_CHARS_RE.search(nfo_target.name):
            return {"id": row_id, "ok": False, "error": "目标 NFO 文件名包含非法字符"}
        row["target_nfo_path"] = str(nfo_target)
        row["nfo"] = item.get("nfo") or {}
    return row


def precheck_video_moves(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("confirmed"):
        return {"ok": False, "items": [], "error": "请先确认无误"}
    seen: dict[str, int] = {}
    rows = [_validate_video_item(item, seen) for item in payload.get("items", [])]
    duplicates = {path for path, count in seen.items() if count > 1}
    for row in rows:
        for key in ("target_path", "target_artwork_path", "target_nfo_path"):
            if row.get(key) in duplicates:
                row["ok"] = False
                row["error"] = "目标路径在当前任务中重复"
                break
    return {"ok": bool(rows) and all(row.get("ok") for row in rows), "items": rows, "error": ""}


def _write_log(task_type: str, payload: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    log_dir = DATA_ROOT / "file-organizer" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{task_type}.json"
    path.write_text(json.dumps({"task_type": task_type, "payload": payload, "items": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def execute_video_moves(payload: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for item in payload.get("items", []):
        pre = precheck_video_moves({"confirmed": payload.get("confirmed"), "items": [item]})["items"]
        if not pre or not pre[0].get("ok"):
            rows.append(pre[0] if pre else {"id": str(item.get("id") or ""), "ok": False, "error": "预检查失败"})
            continue
        row = pre[0]
        source = Path(row["source_path"])
        target = Path(row["target_path"])
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
            if row.get("artwork_path") and row.get("target_artwork_path"):
                artwork_source = Path(row["artwork_path"])
                artwork_target = Path(row["target_artwork_path"])
                artwork_target.parent.mkdir(parents=True, exist_ok=True)
                artwork_source.rename(artwork_target)
            if row.get("target_nfo_path"):
                nfo = row.get("nfo") or {}
                nfo_path = Path(row["target_nfo_path"])
                nfo_path.parent.mkdir(parents=True, exist_ok=True)
                nfo_path.write_text(
                    _episode_nfo_xml(
                        str(nfo.get("title") or target.stem),
                        int(nfo.get("season") or 1),
                        int(nfo.get("episode") or 1),
                        str(nfo.get("published_date") or "") or None,
                        str(nfo.get("plot") or "") or None,
                    ),
                    encoding="utf-8",
                )
            rows.append({**row, "ok": True, "error": ""})
        except OSError as exc:
            rows.append({**row, "ok": False, "error": f"移动失败: {exc}"})
    log_path = _write_log("video-move", payload, rows)
    return {"ok": bool(rows) and all(row.get("ok") for row in rows), "items": rows, "log_path": log_path}


def _metadata_items(source: Path, target: Path) -> list[dict[str, Any]]:
    items = []
    for path in source.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in METADATA_SUFFIXES:
            continue
        relative = path.relative_to(source)
        target_path = target / relative
        items.append({
            "relative_path": relative.as_posix(),
            "source_path": str(path),
            "target_path": str(target_path),
            "will_overwrite": target_path.exists(),
            "ok": True,
            "error": "",
        })
    items.sort(key=lambda item: _natural_key(item["relative_path"]))
    return items


def precheck_metadata_copy(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        source = safe_path("strm", str(payload.get("source_dir") or ""))
        target = safe_path("cloud115", str(payload.get("target_dir") or ""))
    except ValueError as exc:
        return {"ok": False, "items": [], "error": str(exc)}
    if not source.exists() or not source.is_dir():
        return {"ok": False, "items": [], "error": "元数据源目录不存在"}
    items = _metadata_items(source, target)
    folders = sorted({str((target / Path(item["relative_path"]).parent)) for item in items if Path(item["relative_path"]).parent != Path(".")})
    return {"ok": bool(items), "items": items, "folders": folders, "error": ""}


def execute_metadata_copy(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("confirmed"):
        return {"ok": False, "items": [], "error": "请先确认无误"}
    pre = precheck_metadata_copy(payload)
    if not pre.get("ok"):
        return pre
    rows = []
    for item in pre["items"]:
        source = Path(item["source_path"])
        target = Path(item["target_path"])
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            rows.append({**item, "ok": True, "error": ""})
        except OSError as exc:
            rows.append({**item, "ok": False, "error": f"复制失败: {exc}"})
    log_path = _write_log("metadata-copy", payload, rows)
    return {"ok": bool(rows) and all(row.get("ok") for row in rows), "items": rows, "log_path": log_path, "error": ""}
