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


import pyramid.request
import pyramid.httpexceptions
import subprocess
from c2cwsgiutils._auth import is_auth
from c2cwsgiutils.debug import DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY
from pyramid.view import view_config
from tilecloud_chain import TileGeneration
from tilecloud_chain.controller import get_status

class Admin:
    def __init__(self, request: pyramid.request.Request):
        self.request = request

    @view_config(route_name='admin', renderer='admin_index.html')
    def index(self):
        gene = TileGeneration(self.request.registry.settings['tilegeneration_configfile'])

        return {
            'secret': self.request.params.get('secret'),
            'auth': is_auth(self.request, DEPRECATED_ENV_KEY, DEPRECATED_CONFIG_KEY),
            'commands': gene.config.get('server', {}).get('predefined_run', []),
            'status': get_status(gene),
            'run_url': self.request.route_url('run')
        }

    @view_config(route_name='run')
    def run(self):
        if 'command' not in self.request.POST:
            raise pyramid.httpexceptions.HTTPBadRequest("The POST argument 'command' is required")
        subprocess.Popen(self.request.POST['command'], shell=True)
        return pyramid.httpexceptions.HTTPFound(self.request.route_url('admin'))
