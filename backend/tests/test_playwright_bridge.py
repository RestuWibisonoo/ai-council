from app.services.playwright_bridge import PROVIDERS


def test_bridge_only_targets_known_official_provider_hosts():
    assert set(PROVIDERS) == {"chatgpt", "gemini", "claude", "notebooklm"}
    assert PROVIDERS["chatgpt"]["url"].startswith("https://chatgpt.com/")
    assert PROVIDERS["gemini"]["url"].startswith("https://gemini.google.com/")
    assert PROVIDERS["claude"]["url"].startswith("https://claude.ai/")
    assert PROVIDERS["notebooklm"]["url"].startswith("https://notebooklm.google.com/")


def test_bridge_has_editors_for_supported_providers():
    for provider in PROVIDERS.values():
        assert provider["selectors"]
        assert all(isinstance(selector, str) and selector for selector in provider["selectors"])
