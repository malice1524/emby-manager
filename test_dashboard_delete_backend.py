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
    assert "当前 Emby API Key 无法执行删除" in SOURCE
    assert "EMBY_ADMIN_USER" in SOURCE
    assert "EMBY_ADMIN_PW" in SOURCE


def test_spa_response_disables_index_cache():
    main_source = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert '"Cache-Control": "no-cache, no-store, must-revalidate"' in main_source
