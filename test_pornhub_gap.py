from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app.routers import pornhub_gap as gap


def site_items():
    return [
        {"viewkey": "abc1234567890", "key": "abc1234567890", "title": "Hello World", "url": "https://example/1"},
        {"viewkey": "phdef1234567890", "key": "def1234567890", "title": "Second Movie Title", "url": "https://example/2"},
    ]


def test_scan_complete_pair_and_unkeyed_high_confidence_match(tmp_path: Path):
    (tmp_path / "2025-01-01_Hello_World_abc1234567890.mp4").write_bytes(b"x")
    (tmp_path / "2025-01-01_Hello_World_abc1234567890.jpg").write_bytes(b"x")
    (tmp_path / "Second_Movie_Title.mp4").write_bytes(b"x")

    result = gap._scan(tmp_path, site_items())

    assert result["site_total"] == 2
    assert result["missing_videos"] == []
    assert len(result["missing_images"]) == 1
    issue = next(row for row in result["name_issues"] if row["file"] == "Second_Movie_Title.mp4")
    assert set(issue["issues"]) == {"missing_viewkey", "missing_date"}
    assert issue["auto_match"] is True
    assert issue["key"] == "def1234567890"
    assert issue["viewkey"] == "phdef1234567890"


def test_scan_reports_missing_title_and_date(tmp_path: Path):
    (tmp_path / "___abc1234567890.mp4").write_bytes(b"x")

    result = gap._scan(tmp_path, site_items()[:1])

    assert result["missing_videos"] == []
    assert result["name_issues"][0]["issues"] == ["missing_date", "missing_title"]


def test_scan_does_not_auto_match_ambiguous_unkeyed_file(tmp_path: Path):
    site = [
        {"viewkey": "abc1234567890", "key": "abc1234567890", "title": "Same Movie One", "url": "https://example/1"},
        {"viewkey": "def1234567890", "key": "def1234567890", "title": "Same Movie Two", "url": "https://example/2"},
    ]
    (tmp_path / "Same_Movie.mp4").write_bytes(b"x")

    result = gap._scan(tmp_path, site)

    assert len(result["missing_videos"]) == 2
    assert result["name_issues"][0]["auto_match"] is False


def test_safe_dir_rejects_outside_cloud_root(monkeypatch, tmp_path: Path):
    cloud = tmp_path / "cloud"
    cloud.mkdir()
    monkeypatch.setattr(gap, "CLOUD_ROOT", cloud.resolve())

    with pytest.raises(HTTPException) as exc:
        gap._safe_dir(str(tmp_path / "outside"))

    assert exc.value.status_code == 400


def test_profile_url_rejects_fake_pornhub_domain():
    with pytest.raises(HTTPException) as exc:
        gap._profile_url("https://pornhub.com.evil.example/model/foo")
    assert exc.value.status_code == 400


def test_profile_url_accepts_real_subdomain_and_adds_videos():
    assert gap._profile_url("https://www.pornhub.com/model/foo") == "https://www.pornhub.com/model/foo/videos"
