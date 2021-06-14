from typing import Dict

from pyramid.scaffolds.template import Template


class Create(Template):  # type: ignore
    _template_dir = "create"
    summary = "Template used to create a standalone TileCloud-chain project"

    def post(
        self, command: str, output_dir: str, vars: Dict[str, str]  # pylint: disable=redefined-builtin
    ) -> None:
        super().post(command, output_dir, vars)
        print(
            """
Welcome to TileCloud chain.
===========================

By default this scaffold use variable from Puppet facter.
"""
        )
