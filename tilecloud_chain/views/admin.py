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
import subprocess  # nosec
from collections.abc import Callable
from typing import IO, Any
from urllib.parse import urljoin

import pyproj
import pyramid.httpexceptions
import pyramid.request
import pyramid.response
from c2cwsgiutils.auth import AuthenticationType, auth_type, auth_view
from pyramid.view import view_config

import tilecloud_chain.server
import tilecloud_chain.store.postgresql
from tilecloud_chain import configuration, controller, generate
from tilecloud_chain.controller import get_status

_LOG = logging.getLogger(__name__)


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Get the current event loop."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError as e:
        if "There is no current event loop in thread" in str(e):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            raise
    return loop


_LOOP = _get_event_loop()


class Admin:
    """The admin views."""

    def __init__(self, request: pyramid.request.Request) -> None:
        """Initialize."""
        self.request = request

        tilecloud_chain.server.init_tilegeneration(
            self.request.registry.settings["tilegeneration_configfile"],
        )
        self.gene = tilecloud_chain.server._TILEGENERATION  # noqa: SLF001
        assert self.gene is not None

        main_config = self.gene.get_main_config()
        queue_store = main_config.config.get("queue_store", configuration.QUEUE_STORE_DEFAULT)
        self.postgresql_queue_store = (
            _LOOP.run_until_complete(
                tilecloud_chain.store.postgresql.get_postgresql_queue_store(main_config),
            )
            if queue_store == "postgresql"
            else None
        )

    def _check_access(self, raise_on_no_access: bool = True) -> tuple[bool, tilecloud_chain.DatedConfig]:
        assert self.gene
        config = self.gene.get_host_config(self.request.host)
        has_access = self.request.has_permission("admin", config.config.get("authentication", {}))
        if not has_access and raise_on_no_access:
            raise pyramid.httpexceptions.HTTPForbidden
        return has_access, config

    @view_config(route_name="admin", renderer="tilecloud_chain:templates/admin_index.html")  # type: ignore[misc]
    @view_config(route_name="admin_slash", renderer="tilecloud_chain:templates/admin_index.html")  # type: ignore[misc]
    def index(self) -> dict[str, Any]:
        """Get the admin index page."""
        assert self.gene
        has_access, config = self._check_access(raise_on_no_access=False)
        server_config = config.config.get("server", {})
        main_config = self.gene.get_main_config()
        main_server_config = main_config.config.get("server", {})
        jobs_status = None
        queue_store = main_config.config.get("queue_store", configuration.QUEUE_STORE_DEFAULT)
        if queue_store == "postgresql" and has_access:
            assert self.postgresql_queue_store is not None
            config_filename = self.gene.get_host_config_file(self.request.host)
            assert config_filename is not None
            jobs_status = _LOOP.run_until_complete(self.postgresql_queue_store.get_status(config_filename))
        return {
            "auth_type": auth_type(self.request.registry.settings),
            "has_access": has_access,
            "commands": server_config.get("predefined_commands", []),
            "status": _LOOP.run_until_complete(get_status(self.gene))
            if queue_store != "postgresql"
            else None,
            "admin_path": main_server_config.get("admin_path", "admin"),
            "AuthenticationType": AuthenticationType,
            "jobs_status": jobs_status,
            "footer": main_server_config.get("admin_footer") if has_access else None,
            "footer_classes": main_server_config.get("admin_footer_classes", ""),
        }

    @view_config(route_name="admin_run", renderer="fast_json")  # type: ignore[misc]
    def run(self) -> pyramid.response.Response:
        """Run the command given by the user."""
        assert self.gene

        if "TEST_USER" not in os.environ:
            auth_view(self.request)
            self._check_access()

        if "command" not in self.request.POST:
            self.request.response.status_code = 400
            return {"error": "The POST argument 'command' is required"}

        commands = shlex.split(self.request.POST["command"])
        command = commands[0].replace("_", "-")

        allowed_commands = (
            self.gene.get_main_config()
            .config.get("server", {})
            .get("allowed_commands", configuration.ALLOWED_COMMANDS_DEFAULT)
        )
        if command not in allowed_commands:
            return {
                "error": f"The given command '{command}' is not allowed, allowed command are: "
                f"{', '.join(allowed_commands)}",
            }
        add_role = False
        arguments = {c.split("=")[0]: c.split("=")[1:] for c in commands[1:]}
        if command == "generate-tiles":
            add_role = "--get-hash" not in arguments and "--get-bbox" not in arguments

        allowed_arguments = (
            self.gene.get_main_config()
            .config.get("server", {})
            .get("allowed_arguments", configuration.ALLOWED_ARGUMENTS_DEFAULT)
        )
        for arg in arguments:
            if arg.startswith("-") and arg not in allowed_arguments:
                self.request.response.status_code = 400
                return {
                    "error": (
                        f"The argument {arg} is not allowed, allowed arguments are: "
                        f"{', '.join(allowed_arguments)}"
                    ),
                }

        final_command = [
            command,
            f"--host={self.request.host}",
            f"--config={self.gene.get_host_config_file(self.request.host)}",
        ]
        if add_role:
            final_command += ["--role=master"]
        final_command += commands[1:]

        display_command = shlex.join(final_command)
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
            return return_dict

        completed_process = subprocess.run(  # pylint: disable=subprocess-run-check # noqa: S603
            final_command,
            capture_output=True,
            env=env,
            check=False,
        )

        if completed_process.returncode != 0:
            _LOG.warning(
                "The command `%s` exited with an error code: %s\nstdout:\n%s\nstderr:\n%s",
                display_command,
                completed_process.returncode,
                completed_process.stdout.decode(),
                completed_process.stderr.decode(),
            )

        stdout_parsed = _parse_stdout(completed_process.stdout.decode())
        out = _format_output(
            "<br />".join(stdout_parsed),
            int(os.environ.get("TILECLOUD_CHAIN_MAX_OUTPUT_LENGTH", "1000")),
        )
        if completed_process.stderr:
            out += "<br />Error:<br />" + _format_output(
                completed_process.stderr.decode().replace("\n", "<br />"),
                int(os.environ.get("TILECLOUD_CHAIN_MAX_OUTPUT_LENGTH", "1000")),
            )
        return {
            "out": out,
            "error": completed_process.returncode != 0,
        }

    @view_config(route_name="admin_create_job", renderer="fast_json")  # type: ignore[misc]
    def create_job(self) -> dict[str, Any]:
        """Create a job."""
        if "TEST_USER" not in os.environ:
            auth_view(self.request)
            self._check_access()

        store = self.postgresql_queue_store
        assert store is not None

        if "command" not in self.request.POST:
            self.request.response.status_code = 400
            return {"success": False, "error": "The POST argument 'command' is required"}

        if "name" not in self.request.POST:
            self.request.response.status_code = 400
            return {"success": False, "error": "The POST argument 'name' is required"}

        try:
            assert self.gene is not None
            config_filename = self.gene.get_host_config_file(self.request.host)
            assert config_filename is not None
            _LOOP.run_until_complete(
                store.create_job(self.request.POST["name"], self.request.POST["command"], config_filename),
            )
        except tilecloud_chain.store.postgresql.PostgresqlTileStoreError as e:
            _LOG.exception("Error while creating the job")
            self.request.response.status_code = 400
            return {"success": False, "error": str(e)}
        else:
            return {
                "success": True,
            }

    @view_config(route_name="admin_cancel_job", renderer="fast_json")  # type: ignore[misc]
    def cancel_job(self) -> dict[str, Any]:
        """Cancel a job."""
        if "TEST_USER" not in os.environ:
            auth_view(self.request)
            self._check_access()

        store = self.postgresql_queue_store
        assert store is not None

        if "job_id" not in self.request.POST:
            self.request.response.status_code = 400
            return {"success": False, "error": "The POST argument 'job_id' is required"}

        assert self.gene is not None

        try:
            config_filename = self.gene.get_host_config_file(self.request.host)
            assert config_filename is not None
            _LOOP.run_until_complete(
                store.cancel(self.request.POST["job_id"], config_filename),
            )
        except tilecloud_chain.store.postgresql.PostgresqlTileStoreError as e:
            _LOG.exception("Exception while cancelling the job")
            self.request.response.status_code = 400
            return {"success": False, "error": str(e)}
        else:
            return {
                "success": True,
            }

    @view_config(route_name="admin_retry_job", renderer="fast_json")  # type: ignore[misc]
    def retry_job(self) -> dict[str, Any]:
        """Retry a job."""
        if "TEST_USER" not in os.environ:
            auth_view(self.request)
            self._check_access()

        store = self.postgresql_queue_store
        assert store is not None

        if "job_id" not in self.request.POST:
            self.request.response.status_code = 400
            return {"success": False, "error": "The POST argument 'job_id' is required"}

        assert self.gene is not None

        try:
            config_filename = self.gene.get_host_config_file(self.request.host)
            assert config_filename is not None
            _LOOP.run_until_complete(
                store.retry(self.request.POST["job_id"], config_filename),
            )
        except tilecloud_chain.store.postgresql.PostgresqlTileStoreError as e:
            _LOG.exception("Exception while retrying the job")
            self.request.response.status_code = 400
            return {"success": False, "error": str(e)}
        else:
            return {"success": True}

    @view_config(route_name="admin_test", renderer="tilecloud_chain:templates/openlayers.html")  # type: ignore[misc]
    def admin_test(self) -> dict[str, Any]:
        """Test the admin view."""
        assert self.gene
        config = self.gene.get_host_config(self.request.host)
        main_config = self.gene.get_main_config()
        srs = config.config["openlayers"].get("srs", configuration.SRS_DEFAULT)
        proj4js_def = config.config["openlayers"].get("proj4js_def")
        if proj4js_def is None:
            proj4js_def = pyproj.CRS.from_string(srs).to_proj4()
        return {
            "proj4js_def": proj4js_def,
            "srs": srs,
            "center_x": config.config["openlayers"].get("center_x", configuration.CENTER_X_DEFAULT),
            "center_y": config.config["openlayers"].get("center_y", configuration.CENTER_Y_DEFAULT),
            "zoom": config.config["openlayers"].get("zoom", configuration.MAP_INITIAL_ZOOM_DEFAULT),
            "http_url": urljoin(
                self.request.current_route_url(),
                (
                    "/" + main_config.config["server"].get("wmts_path", "wmts") + "/"
                    if "server" in config.config
                    else "/"
                ),
            ),
        }


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
