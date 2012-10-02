TileCloud Chain
===============

Use it
------

Install::

    virtualenv .
    ./bin/pip install tilecloud-chain
    ./bin/pcreate -s tilecloud_chain .

Edit your layers configuration in ``./tilegeneration/config.yaml``.

Generate tiles::

    ./bin/generate_tiles

Generate WMTS capabilities::

    ./bin/generate_controller --generate_wmts_capabilities


From source
-----------

Build it::

    python bootstrap.py --version 1.5.2 --distribute --download-base \
            http://pypi.camptocamp.net/distribute-0.6.22_fix-issue-227/ --setup-source \
            http://pypi.camptocamp.net/distribute-0.6.22_fix-issue-227/distribute_setup.py
    ./buildout/bin/buildout
