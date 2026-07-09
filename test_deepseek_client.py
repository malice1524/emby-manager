import asyncio

from backend.app import deepseek_client


def test_contains_chinese_detects_cjk_text():
    assert deepseek_client.contains_chinese("中文标题") is True
    assert deepseek_client.contains_chinese("Beautiful Girl") is False


def test_sanitize_filename_part_removes_invalid_characters():
    value = deepseek_client.sanitize_filename_part('A/B\\C:D*E?F"G<H>I|J')
    assert "/" not in value
    assert "\\" not in value
    assert ":" not in value
    assert "*" not in value
    assert "?" not in value
    assert '"' not in value
    assert "<" not in value
    assert ">" not in value
    assert "|" not in value
    assert "A" in value and "J" in value


def test_translate_titles_skips_existing_chinese_titles():
    rows = [{"id": "row-1", "title": "已经是中文"}]

    result = asyncio.run(deepseek_client.translate_titles(rows, {"api_key": "secret"}))

    assert result == [{"id": "row-1", "ok": True, "title": "已经是中文", "error": "", "skipped": True}]


def test_translate_titles_returns_row_errors_without_api_key():
    rows = [{"id": "row-1", "title": "Beautiful Girl"}]

    result = asyncio.run(deepseek_client.translate_titles(rows, {"api_key": ""}))

    assert result == [{"id": "row-1", "ok": False, "title": "", "error": "DeepSeek API Key 未配置", "skipped": False}]


def test_translate_titles_prompt_requests_natural_adult_media_titles(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"items":[{"id":"row-1","title":"继妹的秘密邀约"}]}'}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(deepseek_client.httpx, "AsyncClient", FakeClient)

    asyncio.run(deepseek_client.translate_titles(
        [{"id": "row-1", "title": "Step sister wants me to cum inside her while parents are not at home"}],
        {"api_key": "secret", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    ))

    prompt = captured["body"]["messages"][1]["content"]
    assert "完整翻译" in prompt
    assert "不要逐词直译" in prompt
    assert "自然中文" in prompt
    assert "不要有 AI 味" in prompt
    assert "保留人物关系、动作、场景" in prompt



def test_translate_titles_parses_mocked_success(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"items":[{"id":"row-1","title":"美丽女孩在家中"}]}'
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            assert url == "https://api.deepseek.com/chat/completions"
            assert headers["Authorization"] == "Bearer secret"
            assert json["model"] == "deepseek-chat"
            return FakeResponse()

    monkeypatch.setattr(deepseek_client.httpx, "AsyncClient", FakeClient)

    result = asyncio.run(deepseek_client.translate_titles(
        [{"id": "row-1", "title": "Beautiful Girl At Home"}],
        {"api_key": "secret", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    ))

    assert result == [{"id": "row-1", "ok": True, "title": "美丽女孩在家中", "error": "", "skipped": False}]


def test_translate_titles_reports_malformed_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "not json"}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            return FakeResponse()

    monkeypatch.setattr(deepseek_client.httpx, "AsyncClient", FakeClient)

    result = asyncio.run(deepseek_client.translate_titles(
        [{"id": "row-1", "title": "Beautiful Girl"}],
        {"api_key": "secret", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    ))

    assert result[0]["id"] == "row-1"
    assert result[0]["ok"] is False
    assert "解析失败" in result[0]["error"]
