import importlib


def reload_settings_store(monkeypatch, tmp_path, env_key=None):
    monkeypatch.setenv("MONITOR_DATA_DIR", str(tmp_path))
    if env_key is None:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    else:
        monkeypatch.setenv("DEEPSEEK_API_KEY", env_key)
    import backend.app.settings_store as settings_store
    return importlib.reload(settings_store)


def test_public_deepseek_settings_defaults_without_secret(monkeypatch, tmp_path):
    store = reload_settings_store(monkeypatch, tmp_path)

    assert store.public_deepseek_settings() == {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "batch_size": 10,
        "api_key_configured": False,
        "api_key_source": "none",
    }


def test_env_key_is_used_as_fallback_but_not_returned(monkeypatch, tmp_path):
    store = reload_settings_store(monkeypatch, tmp_path, env_key="env-secret")

    effective = store.load_deepseek_settings()
    public = store.public_deepseek_settings()

    assert effective["api_key"] == "env-secret"
    assert public["api_key_configured"] is True
    assert public["api_key_source"] == "environment"
    assert "api_key" not in public
    assert "env-secret" not in str(public)


def test_saved_key_takes_priority_over_environment(monkeypatch, tmp_path):
    store = reload_settings_store(monkeypatch, tmp_path, env_key="env-secret")

    store.save_deepseek_settings({"api_key": "saved-secret"})

    effective = store.load_deepseek_settings()
    public = store.public_deepseek_settings()
    assert effective["api_key"] == "saved-secret"
    assert public["api_key_source"] == "saved"
    assert "saved-secret" not in str(public)


def test_omitted_key_preserves_existing_saved_key(monkeypatch, tmp_path):
    store = reload_settings_store(monkeypatch, tmp_path)
    store.save_deepseek_settings({"api_key": "saved-secret"})

    store.save_deepseek_settings({"model": "custom-model", "batch_size": 5})

    effective = store.load_deepseek_settings()
    assert effective["api_key"] == "saved-secret"
    assert effective["model"] == "custom-model"
    assert effective["batch_size"] == 5


def test_empty_key_clears_saved_key_and_falls_back_to_environment(monkeypatch, tmp_path):
    store = reload_settings_store(monkeypatch, tmp_path, env_key="env-secret")
    store.save_deepseek_settings({"api_key": "saved-secret"})

    store.save_deepseek_settings({"api_key": ""})

    effective = store.load_deepseek_settings()
    public = store.public_deepseek_settings()
    assert effective["api_key"] == "env-secret"
    assert public["api_key_source"] == "environment"


def test_batch_size_is_coerced_to_positive_int(monkeypatch, tmp_path):
    store = reload_settings_store(monkeypatch, tmp_path)

    store.save_deepseek_settings({"batch_size": "0", "base_url": "", "model": ""})

    effective = store.load_deepseek_settings()
    assert effective["batch_size"] == 10
    assert effective["base_url"] == "https://api.deepseek.com"
    assert effective["model"] == "deepseek-chat"
