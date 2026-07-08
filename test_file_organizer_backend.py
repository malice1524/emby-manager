import os
from pathlib import Path

import pytest

from backend.app import file_organizer


def setup_roots(monkeypatch, tmp_path):
    cloud = tmp_path / "CloudDrive115"
    strm = tmp_path / "strm"
    data = tmp_path / "data"
    cloud.mkdir()
    strm.mkdir()
    data.mkdir()
    monkeypatch.setattr(file_organizer, "ROOTS", {"cloud115": cloud, "strm": strm})
    monkeypatch.setattr(file_organizer, "DATA_ROOT", data)
    return cloud, strm, data


def touch(path: Path, text="x", mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_safe_path_blocks_traversal(monkeypatch, tmp_path):
    cloud, _, _ = setup_roots(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        file_organizer.safe_path("cloud115", str(cloud / ".."))


def test_browse_directory_returns_child_directories(monkeypatch, tmp_path):
    cloud, _, _ = setup_roots(monkeypatch, tmp_path)
    (cloud / "A").mkdir()
    touch(cloud / "file.mp4")
    result = file_organizer.browse_directory("cloud115", str(cloud))
    assert [item["name"] for item in result["directories"]] == ["A"]


def test_scan_filters_and_sorts_videos(monkeypatch, tmp_path):
    cloud, _, _ = setup_roots(monkeypatch, tmp_path)
    src = cloud / "src"
    touch(src / "10.mp4", mtime=30)
    touch(src / "2.mkv", mtime=20)
    touch(src / "nested" / "1.avi", mtime=10)
    touch(src / "note.txt")
    name_sorted = file_organizer.scan_videos(str(src), recursive=True, sort="name")
    assert [Path(i["path"]).name for i in name_sorted["items"]] == ["1.avi", "2.mkv", "10.mp4"]
    time_sorted = file_organizer.scan_videos(str(src), recursive=True, sort="mtime")
    assert [Path(i["path"]).name for i in time_sorted["items"]] == ["1.avi", "2.mkv", "10.mp4"]
    current_only = file_organizer.scan_videos(str(src), recursive=False, sort="name")
    assert [Path(i["path"]).name for i in current_only["items"]] == ["2.mkv", "10.mp4"]


def test_scan_marks_suspected_organized_unselected(monkeypatch, tmp_path):
    cloud, _, _ = setup_roots(monkeypatch, tmp_path)
    src = cloud / "src"
    touch(src / "Actor.S01E01.中文标题.mp4")
    result = file_organizer.scan_videos(str(src), recursive=False, sort="name")
    assert result["items"][0]["suspected_organized"] is True
    assert result["items"][0]["selected"] is False


def test_build_final_filename_sanitizes_invalid_chars():
    assert file_organizer.build_final_filename("Actor", 1, 5, 'A/B:C*D?', ".mp4") == "Actor.S01E05.A B C D.mp4"


def test_suggest_next_episode_from_target_dir(monkeypatch, tmp_path):
    cloud, _, _ = setup_roots(monkeypatch, tmp_path)
    target = cloud / "PornHub" / "Actor"
    touch(target / "Actor.S01E01.中文标题.mp4")
    touch(target / "Actor.S01E02.另一个标题.mkv")
    touch(target / "Actor.S02E09.第二季.mp4")
    touch(target / "random.mp4")

    s1 = file_organizer.suggest_next_episode(str(target), 1)
    s2 = file_organizer.suggest_next_episode(str(target), 2)
    s3 = file_organizer.suggest_next_episode(str(target), 3)

    assert s1["max_episode"] == 2
    assert s1["next_episode"] == 3
    assert s1["matched_count"] == 2
    assert s2["next_episode"] == 10
    assert s3["next_episode"] == 1


def test_precheck_blocks_conflicts_and_duplicates(monkeypatch, tmp_path):
    cloud, _, _ = setup_roots(monkeypatch, tmp_path)
    src = touch(cloud / "src" / "a.mp4")
    target_dir = cloud / "target"
    target_dir.mkdir()
    touch(target_dir / "Actor.S01E01.Title.mp4")
    payload = {"confirmed": True, "items": [
        {"id":"1", "source_path": str(src), "target_path": str(target_dir / "Actor.S01E01.Title.mp4")},
        {"id":"2", "source_path": str(src), "target_path": str(target_dir / "Actor.S01E01.Title2.mp4")},
        {"id":"3", "source_path": str(src), "target_path": str(target_dir / "Actor.S01E01.Title2.mp4")},
    ]}
    result = file_organizer.precheck_video_moves(payload)
    statuses = {row["id"]: row for row in result["items"]}
    assert statuses["1"]["ok"] is False and "已存在" in statuses["1"]["error"]
    assert statuses["2"]["ok"] is False and "重复" in statuses["2"]["error"]
    assert statuses["3"]["ok"] is False and "重复" in statuses["3"]["error"]
    assert result["ok"] is False


def test_execute_moves_success_and_keeps_failed_rows(monkeypatch, tmp_path):
    cloud, _, _ = setup_roots(monkeypatch, tmp_path)
    src = touch(cloud / "src" / "a.mp4")
    missing = cloud / "src" / "missing.mp4"
    target = cloud / "target" / "Actor.S01E01.Title.mp4"
    payload = {"confirmed": True, "items": [
        {"id":"1", "source_path": str(src), "target_path": str(target)},
        {"id":"2", "source_path": str(missing), "target_path": str(cloud / "target" / "missing.mp4")},
    ]}
    result = file_organizer.execute_video_moves(payload)
    rows = {row["id"]: row for row in result["items"]}
    assert rows["1"]["ok"] is True
    assert target.exists() and not src.exists()
    assert rows["2"]["ok"] is False


def test_metadata_copy_preserves_structure_and_overwrites(monkeypatch, tmp_path):
    cloud, strm, _ = setup_roots(monkeypatch, tmp_path)
    source = strm / "PornHub" / "Actor"
    target = cloud / "PornHub" / "Actor"
    touch(source / "tvshow.nfo", "new")
    touch(source / "poster.jpg", "poster")
    touch(source / "Season 1" / "a.nfo", "nfo")
    touch(source / "Season 1" / "a.jpg", "jpg")
    touch(source / "Season 1" / "a.strm", "strm")
    touch(source / "Season 1" / "a.mp4", "video")
    touch(target / "tvshow.nfo", "old")
    pre = file_organizer.precheck_metadata_copy({"source_dir": str(source), "target_dir": str(target), "confirmed": True})
    assert any(item["will_overwrite"] for item in pre["items"] if item["relative_path"] == "tvshow.nfo")
    result = file_organizer.execute_metadata_copy({"source_dir": str(source), "target_dir": str(target), "confirmed": True})
    copied = sorted(item["relative_path"] for item in result["items"] if item["ok"])
    assert copied == ["Season 1/a.jpg", "Season 1/a.nfo", "poster.jpg", "tvshow.nfo"]
    assert (target / "Season 1" / "a.nfo").read_text(encoding="utf-8") == "nfo"
    assert not (target / "Season 1" / "a.strm").exists()
    assert not (target / "Season 1" / "a.mp4").exists()
