from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / "backend" / "app" / "routers" / "dashboard.py").read_text(encoding="utf-8")


def test_delete_item_uses_user_context_with_api_key():
    assert "admin_user_id = await _get_admin_user_id(client)" in SOURCE
    assert '"UserId": admin_user_id' in SOURCE
    assert "_emby_auth_headers" in SOURCE
    assert 'UserId="{user_id}"' in SOURCE


def test_delete_item_keeps_admin_token_fallback():
    assert "token = await _get_user_token(client)" in SOURCE
    assert "admin token" in SOURCE
