# -*- coding: utf-8 -*-

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
import subprocess
import threading
from typing import List

from c2cwsgiutils.auth import auth_view, is_auth
import pyramid.httpexceptions
import pyramid.request
from pyramid.view import view_config

from tilecloud_chain.controller import get_status
import tilecloud_chain.server

LOG = logging.getLogger(__name__)


class LogThread(threading.Thread):
    def __init__(self, command: List[str]):
        super().__init__()
        self.command = command

    def run(self):
        try:
            display_command = " ".join([shlex.quote(arg) for arg in self.command])
            LOG.info("Run the command `%s`", display_command)
            env = {}
            env.update(os.environ)
            env["FRONTEND"] = "noninteractive"
            with subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            ) as process:
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    LOG.error(
                        "The command `%s` exited with an error code: %s\nstdout:\n%s\nstderr:\n%s",
                        display_command,
                        process.returncode,
                        stdout.decode(),
                        stderr.decode(),
                    )
                else:
                    LOG.info(
                        "The command `%s` succeeded with stdout:\n%s\nstderr:\n%s",
                        display_command,
                        stdout.decode(),
                        stderr.decode(),
                    )
        except Exception as exception:
            LOG.error(str(exception))
            raise exception


class Admin:
    def __init__(self, request: pyramid.request.Request):
        self.request = request

        tilecloud_chain.server.init_tilegeneration(
            self.request.registry.settings["tilegeneration_configfile"]
        )
        self.gene = tilecloud_chain.server.tilegeneration

    @view_config(route_name="admin", renderer="tilecloud_chain:templates/admin_index.html")
    def index(self):
        return {
            "secret": self.request.params.get("secret"),
            "auth": is_auth(self.request),
            "commands": self.gene.config.get("server", {}).get("predefined_commands", []),
            "status": get_status(self.gene),
            "run_url": self.request.route_url("admin_run"),
            "static_path": self.gene.config.get("server", {}).get("static_path", "static"),
        }

    @view_config(route_name="admin_run")
    def run(self):
        auth_view(self.request)

        if "command" not in self.request.POST:
            raise pyramid.httpexceptions.HTTPBadRequest("The POST argument 'command' is required")

        command = shlex.split(self.request.POST["command"])

        if command[0] not in self.gene.config.get("server", {}).get(
            "allowed_commands", ["generate_tiles", "generate_controller"]
        ):
            raise pyramid.httpexceptions.HTTPBadRequest(
                "The given executable '{}' is not allowed".format(command[0])
            )
        log_thread = LogThread(command)
        log_thread.start()
        return pyramid.httpexceptions.HTTPFound(self.request.route_url("admin"))
