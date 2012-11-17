from pyramid.scaffolds.template import Template


class Create(Template):
    _template_dir = 'create'
    summary = 'Template used to create a tilecloud chain project'

    def post(self, *args, **kargs):
        super(Create, self).post(*args, **kargs)
        print """
Welcome to TileCloud chain.
===========================

By default this scaffold use variable from Puppet facter,
to make it working you should have this in your buildout.cfg:

[buildout]
parts = ...
    template

[template]
recipe = z3c.recipe.filetemplate
source-directory = .
exclude-directories = buildout
extends = vars
    facts

[vars]
instanceid = main

[facts]
recipe = c2c.recipe.facts"""
