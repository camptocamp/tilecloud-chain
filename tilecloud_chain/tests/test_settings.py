# Copyright (c) 2026 by Camptocamp
"""Tests for the application settings."""

import datetime

import pytest
from pydantic import ValidationError

from tilecloud_chain.settings import PostgresqlSettings, RedisSettings, Settings


class TestDurationSettings:
    """Tests for the duration typed settings."""

    def test_defaults(self) -> None:
        """Test the default duration values."""
        assert Settings.model_fields["max_generation_time"].default == datetime.timedelta(seconds=60)
        assert PostgresqlSettings.model_fields["init_timeout"].default == datetime.timedelta(seconds=30)

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("60", datetime.timedelta(seconds=60)),
            ("2m", datetime.timedelta(minutes=2)),
            ("2m30", datetime.timedelta(minutes=2, seconds=30)),
            ("1h", datetime.timedelta(hours=1)),
            ("PT1M30S", datetime.timedelta(minutes=1, seconds=30)),
            (datetime.timedelta(minutes=5), datetime.timedelta(minutes=5)),
        ],
    )
    def test_max_generation_time_parsing(self, value: object, expected: datetime.timedelta) -> None:
        """Test that max_generation_time accepts durations in the supported formats."""
        assert Settings(max_generation_time=value).max_generation_time == expected

    def test_max_generation_time_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that max_generation_time is parsed from the environment variable."""
        monkeypatch.setenv("TILECLOUD_CHAIN__MAX_GENERATION_TIME", "2m")
        assert Settings().max_generation_time == datetime.timedelta(minutes=2)

    def test_invalid_duration(self) -> None:
        """Test that an invalid duration is rejected."""
        with pytest.raises(ValidationError):
            Settings(max_generation_time="not-a-duration")

    def test_init_timeout_parsing(self) -> None:
        """Test that init_timeout accepts durations in the supported formats."""
        assert PostgresqlSettings(init_timeout="1m30").init_timeout == datetime.timedelta(
            minutes=1,
            seconds=30,
        )

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, None),
            ("", None),
            ("30", datetime.timedelta(seconds=30)),
            ("2m30", datetime.timedelta(minutes=2, seconds=30)),
        ],
    )
    def test_redis_socket_timeout_parsing(self, value: object, expected: datetime.timedelta | None) -> None:
        """Test that an unset or empty redis socket_timeout is treated as not set."""
        assert RedisSettings(socket_timeout=value).socket_timeout == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, None),
            ("", None),
            ("5", datetime.timedelta(seconds=5)),
            ("PT10S", datetime.timedelta(seconds=10)),
        ],
    )
    def test_redis_timeout_parsing(self, value: object, expected: datetime.timedelta | None) -> None:
        """Test that an unset or empty redis timeout is treated as not set."""
        assert RedisSettings(timeout=value).timeout == expected
