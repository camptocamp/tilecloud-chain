"""The admin views."""

# Copyright (c) 2018-2025 by Camptocamp
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 3. Neither the name of Camptocamp nor the names of its contributors may
# be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import asyncio
import io
import json
import logging
import multiprocessing
import os
import shlex
import urllib.parse
from collections.abc import Callable
from typing import IO, Annotated, Any

import pyproj
from c2casgiutils import auth
from c2casgiutils import config as c2c_config
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import tilecloud_chain.server
import tilecloud_chain.store.postgresql
from tilecloud_chain import TileGeneration, configuration, controller, generate, server
from tilecloud_chain.controller import get_status

_LOG = logging.getLogger(__name__)
# Initialize templates
_templates = Jinja2Templates(directory="tilecloud_chain/templates")
_postgresql_store: tilecloud_chain.store.postgresql.PostgresqlTileStore | None = None
app = FastAPI(title="TileCloud-chain admin API")


def _get_tilegeneration() -> TileGeneration:
    """Get the tilegeneration instance."""
    if (
        not hasattr(tilecloud_chain.server, "_TILEGENERATION")
        or tilecloud_chain.server._TILEGENERATION is None  # pylint: disable=protected-access
    ):
        raise HTTPException(status_code=500, detail="Tilegeneration not initialized")
    return tilecloud_chain.server._TILEGENERATION  # pylint: disable=protected-access


async def startup(_main_app: FastAPI) -> None:
    """Create and configure the FastAPI admin application."""

    main_config = await _get_tilegeneration().get_main_config()
    queue_store = main_config.config.get("queue_store", configuration.QUEUE_STORE_DEFAULT)
    if queue_store == "postgresql":
        global _postgresql_store  # pylint: disable=global-statement
        _postgresql_store = await tilecloud_chain.store.postgresql.get_postgresql_queue_store(main_config)


def _get_postgresql_store() -> tilecloud_chain.store.postgresql.PostgresqlTileStore:
    """Get the PostgreSQL store."""
    if not _postgresql_store:
        raise HTTPException(status_code=400, detail="PostgreSQL queue store not configured")
    return _postgresql_store


async def _get_access(
    config: Annotated[tilecloud_chain.DatedConfig, Depends(server.get_host_config)],
    auth_info: Annotated[auth.AuthInfo, Depends(auth.get_auth)],
) -> bool:
    """Check if the user has access to admin functions."""

    if c2c_config.settings.auth.test.username:
        return True

    if await auth.check_admin_access(auth_info):
        return True

    auth_config = config.config.get("authentication", {})
    return await auth.check_access_config(
        auth_info,
        auth.AuthConfig(
            github_repository=auth_config.get("github_repository", ""),
            github_access_type=auth_config.get("github_access_type", ""),
        ),
    )


def _check_access(
    has_access: Annotated[dict[str, Any], Depends(_get_access)],
) -> None:
    """Check if the user has access to admin functions."""

    if not has_access:
        raise HTTPException(status_code=403, detail="Access forbidden")


# Pydantic models for request/response
class CommandRequest(BaseModel):
    """Model for command execution requests."""

    command: str


class JobRequest(BaseModel):
    """Model for job creation requests."""

    name: str
    command: str


class JobActionRequest(BaseModel):
    """Model for job action requests (cancel, retry)."""

    job_id: str


class CommandResponse(BaseModel):
    """Model for command execution responses."""

    out: str
    error: bool


class JobResponse(BaseModel):
    """Model for job operation responses."""

    success: bool
    error: str = ""


@app.get("/", response_class=HTMLResponse)
async def admin_index(
    request: Request,
    config: Annotated[tilecloud_chain.DatedConfig, Depends(server.get_host_config)],
    gene: Annotated[TileGeneration, Depends(_get_tilegeneration)],
    auth_info: Annotated[auth.AuthInfo, Depends(auth.get_auth)],
    has_access: Annotated[bool, Depends(_get_access)],
    auth_type: Annotated[auth.AuthenticationType, Depends(auth.auth_type)],
    secret: Annotated[str | None, Query(..., description="Secret key for authentication")] = None,
) -> HTMLResponse:
    """Get the admin index page."""
    server_config = config.config.get("server", {})
    main_config = await gene.get_main_config()
    main_server_config = main_config.config.get("server", {})
    jobs_status = None
    queue_store = main_config.config.get("queue_store", configuration.QUEUE_STORE_DEFAULT)

    if queue_store == "postgresql" and has_access and _postgresql_store and config.file:
        jobs_status = await _postgresql_store.get_status(config.file)

    assert auth_info, auth_info
    context = {
        "request": request,
        "has_access": has_access,
        "auth_info": auth_info,
        "auth_type": auth_type,
        "secret": secret,
        "current_url": str(request.url),
        "commands": server_config.get("predefined_commands", []),
        "status": await get_status(gene) if queue_store != "postgresql" else None,
        "admin_path": main_server_config.get("admin_path", "admin"),
        "AuthenticationType": auth.AuthenticationType,
        "jobs_status": jobs_status,
        "footer": main_server_config.get("admin_footer") if has_access else None,
        "footer_classes": main_server_config.get("admin_footer_classes", ""),
        "urlencode": urllib.parse.urlencode,
    }
    return _templates.TemplateResponse("admin_index.html", context)


@app.post("/run")
async def admin_run(
    request: Request,
    command: Annotated[str, Form(...)],
    gene: Annotated[TileGeneration, Depends(_get_tilegeneration)],
    _: Annotated[None, Depends(_check_access)],
) -> CommandResponse:
    """Run the command given by the user."""
    commands = shlex.split(command)
    for part in commands:
        if ";" in part or "&&" in part or "|" in part or "\n" in part or "\r" in part:
            raise HTTPException(
                status_code=400,
                detail="The command contains malicious characters",
            )
    command_name = commands[0].replace("_", "-")

    main_config = await gene.get_main_config()
    allowed_commands = main_config.config.get("server", {}).get(
        "allowed_commands",
        configuration.ALLOWED_COMMANDS_DEFAULT,
    )
    if command_name not in allowed_commands:
        raise HTTPException(
            status_code=400,
            detail=f"The given command '{command_name}' is not allowed, allowed command are: {', '.join(allowed_commands)}",
        )

    add_role = False
    arguments = {c.split("=")[0]: c.split("=")[1:] for c in commands[1:]}
    if command_name == "generate-tiles":
        add_role = "--get-hash" not in arguments and "--get-bbox" not in arguments

    allowed_arguments = main_config.config.get("server", {}).get(
        "allowed_arguments",
        configuration.ALLOWED_ARGUMENTS_DEFAULT,
    )
    for arg in arguments:
        if arg.startswith("-") and arg not in allowed_arguments:
            raise HTTPException(
                status_code=400,
                detail=f"The argument {arg} is not allowed, allowed arguments are: {', '.join(allowed_arguments)}",
            )

    host = request.headers.get("host", "localhost")
    final_command = [
        command_name,
        f"--host={host}",
        f"--config={await gene.get_host_config_file(host)}",
    ]
    if add_role:
        final_command += ["--role=master"]
    final_command += commands[1:]

    display_command = shlex.join(final_command).replace("\n", " ").replace("\r", " ")
    _LOG.info("Run the command `%s`", display_command)
    env: dict[str, str] = {}
    env.update(os.environ)
    env["FRONTEND"] = "noninteractive"

    main = None
    if final_command[0] in ["generate-tiles", "generate_tiles"]:
        main = generate.main
    elif final_command[0] in ["generate-controller", "generate_controller"]:
        main = controller.main

    if main is not None:
        return_dict: dict[str, Any] = {}
        proc = multiprocessing.Process(
            target=_run_in_process,
            args=(final_command, env, main, return_dict),
        )
        proc.start()
        proc.join()
        return CommandResponse(out=return_dict.get("out", ""), error=return_dict.get("error", False))

    process = await asyncio.create_subprocess_exec(
        *final_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        _LOG.warning(
            "The command `%s` exited with an error code: %s\nstdout:\n%s\nstderr:\n%s",
            display_command,
            process.returncode,
            stdout.decode(),
            stderr.decode(),
        )

    stdout_parsed = _parse_stdout(stdout.decode())
    out = _format_output(
        "<br />".join(stdout_parsed),
        int(os.environ.get("TILECLOUD_CHAIN_MAX_OUTPUT_LENGTH", "1000")),
    )
    if stderr:
        out += "<br />Error:<br />" + _format_output(
            stderr.decode().replace("\n", "<br />"),
            int(os.environ.get("TILECLOUD_CHAIN_MAX_OUTPUT_LENGTH", "1000")),
        )

    return CommandResponse(out=out, error=process.returncode != 0)


@app.post("/create_job")
async def admin_create_job(
    request: Request,
    name: Annotated[str, Form(...)],
    command: Annotated[str, Form(...)],
    gene: Annotated[TileGeneration, Depends(_get_tilegeneration)],
    postgresql_store: Annotated[
        tilecloud_chain.store.postgresql.PostgresqlTileStore,
        Depends(_get_postgresql_store),
    ],
    _: Annotated[None, Depends(_check_access)],
) -> JobResponse:
    """Create a job."""
    try:
        host = request.headers.get("host", "localhost")
        config_filename = await gene.get_host_config_file(host)
        if not config_filename:
            raise HTTPException(status_code=400, detail="Config filename not found")

        await postgresql_store.create_job(name, command, config_filename)
        return JobResponse(success=True)
    except tilecloud_chain.store.postgresql.PostgresqlTileStoreError as e:
        _LOG.exception("Error while creating the job")
        raise HTTPException(status_code=400, detail=str(e))  # noqa: B904 # pylint: disable=raise-missing-from


@app.post("/cancel_job")
async def admin_cancel_job(
    request: Request,
    job_id: Annotated[int, Form(...)],
    gene: Annotated[TileGeneration, Depends(_get_tilegeneration)],
    postgresql_store: Annotated[
        tilecloud_chain.store.postgresql.PostgresqlTileStore,
        Depends(_get_postgresql_store),
    ],
    _: Annotated[None, Depends(_check_access)],
) -> JobResponse:
    """Cancel a job."""
    try:
        host = request.headers.get("host", "localhost")
        config_filename = await gene.get_host_config_file(host)
        if not config_filename:
            raise HTTPException(status_code=400, detail="Config filename not found")

        await postgresql_store.cancel(job_id, config_filename)
        return JobResponse(success=True)
    except tilecloud_chain.store.postgresql.PostgresqlTileStoreError as e:
        _LOG.exception("Exception while cancelling the job")
        raise HTTPException(status_code=400, detail=str(e))  # noqa: B904 # pylint: disable=raise-missing-from


@app.post("/retry_job")
async def admin_retry_job(
    request: Request,
    job_id: Annotated[int, Form(...)],
    gene: Annotated[TileGeneration, Depends(_get_tilegeneration)],
    postgresql_store: Annotated[
        tilecloud_chain.store.postgresql.PostgresqlTileStore,
        Depends(_get_postgresql_store),
    ],
    _: Annotated[None, Depends(_check_access)],
) -> JobResponse:
    """Retry a job."""
    try:
        host = request.headers.get("host", "localhost")
        config_filename = await gene.get_host_config_file(host)
        if not config_filename:
            raise HTTPException(status_code=400, detail="Config filename not found")

        await postgresql_store.retry(job_id, config_filename)
        return JobResponse(success=True)
    except tilecloud_chain.store.postgresql.PostgresqlTileStoreError as e:
        _LOG.exception("Exception while retrying the job")
        raise HTTPException(status_code=400, detail=str(e))  # noqa: B904 # pylint: disable=raise-missing-from


@app.get("/test", response_class=HTMLResponse)
async def admin_test(
    request: Request,
    gene: Annotated[TileGeneration, Depends(_get_tilegeneration)],
) -> HTMLResponse:
    """Test the admin view."""
    host = request.headers.get("host", "localhost")
    config = await gene.get_host_config(host)
    srs = config.config["openlayers"].get("srs", configuration.SRS_DEFAULT)
    proj4js_def = config.config["openlayers"].get("proj4js_def")
    if proj4js_def is None:
        proj4js_def = pyproj.CRS.from_string(srs).to_proj4()

    context = {
        "request": request,
        "proj4js_def": proj4js_def,
        "srs": srs,
        "center_x": config.config["openlayers"].get("center_x", configuration.CENTER_X_DEFAULT),
        "center_y": config.config["openlayers"].get("center_y", configuration.CENTER_Y_DEFAULT),
        "zoom": config.config["openlayers"].get("zoom", configuration.MAP_INITIAL_ZOOM_DEFAULT),
    }
    return _templates.TemplateResponse("openlayers.html", context)


def _parse_stdout(stdout: str) -> list[str]:
    stdout_parsed = []
    for line in stdout.splitlines():
        try:
            json_message = json.loads(line)
            msg = json_message["msg"]
            if json_message.get("logger_name", "").startswith("tilecloud"):
                if "full_message" in json_message:
                    full_message = json_message["full_message"].replace("\n", "<br />")
                    msg += f"<br />{full_message}"
                stdout_parsed.append(msg)
        except:  # pylint: disable=bare-except # noqa: E722
            stdout_parsed.append(line)
    return stdout_parsed


def _format_output(string: str, max_length: int = 1000) -> str:
    result = ""
    for line in string.splitlines():
        if len(string) > max_length:
            break
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
                if "source_facility" in parsed and not parsed.startswith("tilecloud"):
                    continue

                if result:
                    result += "\n"

                if (
                    "level_name" in parsed
                    and "source_facility" in parsed
                    and "line" in parsed
                    and "msg" in parsed
                ):
                    if parsed.startswith("tilecloud"):
                        result += (
                            f"[{parsed['level_name']}] {parsed['source_facility']}:{parsed['line']} "
                            f"{parsed['msg']}"
                        )
                elif "msg" in parsed:
                    result += parsed["msg"]
                else:
                    result += line
            except json.decoder.JSONDecodeError:
                if result:
                    result += "\n"
                result += line
        else:
            if result:
                result += "\n"
            result += line

    if len(string) > max_length:
        return string[: max_length - 3] + "\n..."
    return string


def _run_in_process(
    final_command: list[str],
    env: dict[str, str],
    main: Callable[[list[str], IO[str]], Any],
    return_dict: dict[str, Any],
) -> None:
    display_command = shlex.join(final_command)
    error = False
    out = io.StringIO()
    try:
        for key, value in env.items():
            os.environ[key] = value
        _LOG.debug("Running the command `%s` using the function directly", display_command)
        main(final_command, out)
    except Exception:  # pylint: disable=broad-exception-caught
        _LOG.exception("Error while running the command `%s`", display_command)
        error = True
    return_dict["out"] = _format_output(
        "<br />".join(_parse_stdout(out.getvalue())),
        int(os.environ.get("TILECLOUD_CHAIN_MAX_OUTPUT_LENGTH", "1000")),
    )
    return_dict["error"] = error
