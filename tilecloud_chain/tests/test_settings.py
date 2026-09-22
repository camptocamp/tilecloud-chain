# Copyright (c) 2026 by Camptocamp
"""Tests for the settings loaded from environment variables."""

import pytest

from tilecloud_chain.settings import SecuritySettings, Settings


def test_admin_test_img_src_default():
    assert SecuritySettings().admin_test_img_src == []


def test_admin_test_img_src_comma_separated():
    security = SecuritySettings(admin_test_img_src="https://example.com/img/, https://tiles.example.org/")
    assert security.admin_test_img_src == ["https://example.com/img/", "https://tiles.example.org/"]


def test_admin_test_img_src_list():
    security = SecuritySettings(admin_test_img_src=["https://example.com/img/"])
    assert security.admin_test_img_src == ["https://example.com/img/"]


def test_admin_test_img_src_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "TILECLOUD_CHAIN__SECURITY__ADMIN_TEST_IMG_SRC",
        "https://example.com/img/,https://tiles.example.org/",
    )
    settings = Settings()
    assert settings.security.admin_test_img_src == ["https://example.com/img/", "https://tiles.example.org/"]


def test_str_list_env_not_json(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TILECLOUD_CHAIN__ALLOWED_PROCESS_COMMANDS", "optipng,pngquant")
    monkeypatch.setenv("TILECLOUD_CHAIN__SECURITY__TRUSTED_HOSTS", "example.com")
    settings = Settings()
    assert settings.allowed_process_commands == ["optipng", "pngquant"]
    assert settings.security.trusted_hosts == ["example.com"]
