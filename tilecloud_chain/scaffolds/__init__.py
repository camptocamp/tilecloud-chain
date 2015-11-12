from pyramid.scaffolds.template import Template  # pragma: no cover


class Create(Template):  # pragma: no cover
    _template_dir = 'create'
    summary = 'Template used to create a standalone TileCloud-chain project'

    def post(self, *args, **kargs):
        super(Create, self).post(*args, **kargs)
        print("""
Welcome to TileCloud chain.
===========================

By default this scaffold use variable from Puppet facter.
""")


class Ec2(Template):  # pragma: no cover
    _template_dir = 'ec2'
    summary = 'Template used to complete TileCloud-chain project with ec2 support'
