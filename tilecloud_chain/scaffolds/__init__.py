from pyramid.scaffolds.template import Template  # pragma: no cover


class Create(Template):  # pragma: no cover
    _template_dir = "create"
    summary = "Template used to create a standalone TileCloud-chain project"

    def post(self, command, output_dir, vars):  # pylint: disable=redefined-builtin
        super().post(command, output_dir, vars)
        print(
            """
Welcome to TileCloud chain.
===========================

By default this scaffold use variable from Puppet facter.
"""
        )
