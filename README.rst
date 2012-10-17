TileCloud Chain
===============

Just syntax check:

.. image:: https://secure.travis-ci.org/sbrunner/tilecloud-chain.png


The goal of TileCloud Chain is to have tools around tile generation on a chain like:

Source: WMS, Mapnik, and probably in future MapScript.

Optionaly use an SQS queue.

Destination in WMTS layout, on localhost or on S3.

Feature:

- Generate tiles.
- Drop empty tiles.
- Drop tiles outside a geometry or a bbox.
- Use MetaTiles
- Generate GetCapabilities.
- Generate OpenLayers example page.
- Obtain the hash of an empty tile
- In future, measure tile generation speed
- Calculate cost and generation time.
- In future, manage the AWG hosts that generate tiles.
- Delete empty tiles.

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
