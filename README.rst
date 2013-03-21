TileCloud Chain
===============

The goal of TileCloud Chain is to have tools around tile generation on a chain like:

Source: WMS, Mapnik, and probably in future MapScript.

Optionally use an SQS queue.

Destination in WMTS layout, on local filesystem or on S3.

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
- In future, manage the AWS hosts that generate tiles.
- Delete empty tiles.

Use it
------

Install::

    virtualenv .
    ./bin/pip install tilecloud-chain
    ./bin/pcreate -s tilecloud_chain .

Edit your layers configuration in ``./tilegeneration/config.yaml``.

Default self documented file: https://github.com/sbrunner/tilecloud-chain/blob/master/tilecloud_chain/scaffolds/create/tilegeneration/config.yaml.in.

Generate tiles::

    ./bin/generate_tiles

Generate WMTS capabilities::

    ./bin/generate_controller --generate_wmts_capabilities

Please use the ``--debug`` to report issue.


From source
-----------

Build it::

    python bootstrap.py --distribute -v 1.7.1
    ./buildout/bin/buildout

Changes
-------

Release 0.5
~~~~~~~~~~~

1. SQS config change:

.. code:: javascript

    layers:
        layer_name:
            sqs:
                # The region where the SQS queue is
                region: eu-west-1
                # The SQS queue name, it should already exists
                queue: the_name

2. Add debug option (--debug), please use it to report issue.
