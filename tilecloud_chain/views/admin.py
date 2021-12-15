# Copyright (c) 2018 by Camptocamp
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


import logging
import os
import shlex
import subprocess  # nosec
from typing import Any, Dict

from c2cwsgiutils.auth import auth_view, is_auth
import pyramid.httpexceptions
import pyramid.request
import pyramid.response
from pyramid.view import view_config

from tilecloud_chain.controller import get_status
import tilecloud_chain.server

LOG = logging.getLogger(__name__)


class Admin:
    """The admin views."""

    def __init__(self, request: pyramid.request.Request):
        """Initialize."""
        self.request = request

        tilecloud_chain.server.init_tilegeneration(
            self.request.registry.settings["tilegeneration_configfile"]
        )
        self.gene = tilecloud_chain.server.tilegeneration

    @view_config(route_name="admin", renderer="tilecloud_chain:templates/admin_index.html")  # type: ignore
    def index(self) -> Dict[str, Any]:
        """Get the admin index page."""
        assert self.gene
        config = self.gene.get_host_config(self.request.host)
        server_config = config.config.get("server", {})
        return {
            "secret": self.request.params.get("secret"),
            "auth": is_auth(self.request),
            "commands": server_config.get("predefined_commands", []),
            "status": get_status(self.gene),
            "run_url": self.request.route_url("admin_run"),
            "static_path": server_config.get("static_path", "static"),
        }

    @view_config(route_name="admin_run", renderer="fast_json")  # type: ignore
    def run(self) -> pyramid.response.Response:
        """Run the command given by the user."""
        assert self.gene
        auth_view(self.request)

        if "command" not in self.request.POST:
            self.request.response.status_code = 400
            return {"error": "The POST argument 'command' is required"}

        commands = shlex.split(self.request.POST["command"])
        command = commands[0].replace("_", "-")

        allowed_commands = (
            self.gene.get_main_config()
            .config.get("server", {})
            .get("allowed_commands", ["generate-tiles", "generate-controller", "generate-cost"])
        )
        if command not in allowed_commands:
            return {
                "error": f"The given command '{command}' is not allowed, allowed command are: "
                f"{', '.join(allowed_commands)}"
            }
        add_role = False
        arguments = {c.split("=")[0]: c.split("=")[1:] for c in commands[1:]}
        if command == "generate-tiles":
            add_role = "--get-hash" not in arguments and "--get-bbox" not in arguments

        allowed_arguments = (
            self.gene.get_main_config()
            .config.get("server", {})
            .get(
                "allowed_arguments",
                [
                    "--layer",
                    "--get-hash",
                    "--openlayers",
                    "--generate-legend-images",
                    "--dump-config",
                    "--get-bbox",
                ],
            )
        )
        for arg in arguments.keys():
            if arg.startswith("-") and arg not in allowed_arguments:
                self.request.response.status_code = 400
                return {
                    "error": (
                        f"The argument {arg} is not allowed, allowed arguments are: "
                        f"{', '.join(allowed_arguments)}"
                    )
                }

        final_command = [command, f"--config={self.gene.get_host_config_file(self.request.host)}"]
        if add_role:
            final_command += ["--role=master"]
        final_command += commands[1:]

        display_command = " ".join([shlex.quote(arg) for arg in final_command])
        LOG.info("Run the command `%s`", display_command)
        env: Dict[str, str] = {}
        env.update(os.environ)
        env["FRONTEND"] = "noninteractive"

        completed_process = subprocess.run(  # nosec # pylint: disable=subprocess-run-check
            final_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        if completed_process.returncode != 0:
            LOG.warning(
                "The command `%s` exited with an error code: %s\nstdout:\n%s\nstderr:\n%s",
                display_command,
                completed_process.returncode,
                completed_process.stdout.decode(),
                completed_process.stderr.decode(),
            )

        return {
            "stdout": completed_process.stdout.decode(),
            "stderr": completed_process.stderr.decode(),
            "returncode": completed_process.returncode,
        }
