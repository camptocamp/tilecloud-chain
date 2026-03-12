"""Application settings from environment variables."""

from __future__ import annotations

from typing import Annotated, Literal

from anyio import Path
from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _to_path(value: str | Path) -> Path:
    if isinstance(value, Path):
        return value
    return Path(str(value))


AnyioPath = Annotated[Path, BeforeValidator(_to_path)]


def _to_str_list(value: str | None | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


StrList = Annotated[list[str], BeforeValidator(_to_str_list)]


def _to_route_prefix(route_prefix: str) -> str:
    if route_prefix and not route_prefix.startswith("/"):
        route_prefix = f"/{route_prefix}"
    if route_prefix and not route_prefix.endswith("/"):
        route_prefix = f"{route_prefix}/"
    return route_prefix


RoutePrefix = Annotated[str, BeforeValidator(_to_route_prefix)]


def _to_wmts_path(wmts_path: str) -> str:
    if wmts_path and not wmts_path.endswith("/"):
        wmts_path = f"{wmts_path}/"
    return wmts_path


WMTSPath = Annotated[str, BeforeValidator(_to_wmts_path)]


class AzureSettings(BaseModel):
    """Azure storage settings."""

    model_config = ConfigDict(extra="ignore")

    storage_connection_string: str | None = None
    storage_blob_container_url: str | None = None
    storage_blob_validate_container_name: bool = True
    storage_account_url: str | None = None


_LOGGING_LEVELS = Literal["CRITICAL", "ERROR", "WARN", "WARNING", "INFO", "DEBUG", "NOTSET"]
_TCC_LOG_LEVELS = Literal["quiet", "verbose", "debug"]


class LoggingSettings(BaseModel):
    """Logging settings."""

    model_config = ConfigDict(extra="ignore")

    ci: bool = False
    log_type: str = "console"
    other_log_level: _LOGGING_LEVELS = "WARN"
    sql_log_level: _LOGGING_LEVELS = "WARN"
    c2casgiutils_log_level: _LOGGING_LEVELS = "WARN"
    tilecloud_log_level: _LOGGING_LEVELS = "INFO"
    tilecloud_chain_log_level: _LOGGING_LEVELS = "INFO"
    server_log_level: _TCC_LOG_LEVELS = "quiet"
    mapcache_log_level: _TCC_LOG_LEVELS = "verbose"


class RedisSettings(BaseModel):
    """Redis settings."""

    model_config = ConfigDict(extra="ignore")

    url: str | None = None
    db: str | None = None
    socket_timeout: str | None = None
    sentinels: str | None = None
    service_name: str | None = None
    options: str | None = None
    queue: str | None = None
    timeout: str | None = None
    sentinel_service_name: str | None = None


class PostgresqlSettings(BaseModel):
    """PostgreSQL settings."""

    model_config = ConfigDict(extra="ignore")

    schema_name: str = "tilecloud_chain"
    sqlalchemy_url: str | None = None
    objgraph_postgresql: bool = False
    objgraph_limit: int = 10


class SecuritySettings(BaseModel):
    """Security settings."""

    trusted_hosts: StrList = ["*"]
    cors_origins: StrList = ["*"]
    cors_methods: StrList = ["*"]
    cors_headers: StrList = ["*"]
    cors_credentials: bool = True


class Settings(BaseSettings):
    """The configuration settings."""

    max_output_length: int = 1000
    nb_tasks: int = 1
    slave: bool = False
    objgraph_limit: int = 10
    objgraph_gene: bool = False
    config_file: AnyioPath = Path("/etc/tilegeneration/config.yaml")
    main_config_file: AnyioPath | None = None
    hosts_file: AnyioPath = Path("/etc/tilegeneration/hosts.yaml")
    hosts_limit: AnyioPath = Path("/etc/tilegeneration/hosts_limit.yaml")
    ignore_config_error: bool = False
    max_generation_time: int = 60
    allowed_process_commands: StrList = ["optipng", "jpegoptim", "pngquant"]
    frontend: str | None = None
    development: bool = False
    route_prefix: RoutePrefix = "/tiles/"
    wmts_path: WMTSPath = ""

    azure: AzureSettings = AzureSettings()
    logging: LoggingSettings = LoggingSettings()
    postgresql: PostgresqlSettings = PostgresqlSettings()
    redis: RedisSettings = RedisSettings()
    tests: bool = False
    security: SecuritySettings = SecuritySettings()

    model_config = SettingsConfigDict(
        env_prefix="TILECLOUD_CHAIN__",
        env_nested_delimiter="__",
        extra="ignore",
    )


settings = Settings()
