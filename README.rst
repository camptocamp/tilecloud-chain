TileCloud Chain
===============

The goal of TileCloud Chain is to have tools around tile generation on a chain like:

Source: WMS, Mapnik.

Optionally use an SQS queue, AWS host, SNS topic.

Destination in WMTS layout, directly on local filesystem, on S3 or MBTiles on local filesystem.

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


.. contents:: Table of contents


Get it
------

Install::

    virtualenv buildout
    ./buildout/bin/pip install tilecloud-chain
    ./buildout/bin/pcreate -s tilecloud_chain .

Edit your layers configuration in ``./tilegeneration/config.yaml``.

`Default configuration file <https://github.com/sbrunner/tilecloud-chain/blob/master/tilecloud_chain/scaffolds/create/tilegeneration/config.yaml.in_tmpl>`_.


Configure hash
--------------

We can filter tiles and metatiles by using an hash.

The configuration of this hash is in the layer like this:

.. code:: yaml

    empty_metatile_detection:
        size: 740
        hash: 3237839c217b51b8a9644d596982f342f8041546
    empty_tile_detection:
        size: 921
        hash: 1e3da153be87a493c4c71198366485f290cad43c

To eaysly generate this configuration we can use the following command::

    ./buildout/bin/generate_tiles --get-hash <z/x/y> -l <layer_name>

Where ``<z/x/y>`` should refers en empty tile/metatile. Generally it's a good
idea to use z as the maximum zoom, x and y as 0.


Configure geom/sql
------------------

We can generate the tiles only on some geometries stored in PostGis.

The configuration is in the layer like this:

.. code:: yaml

    connection: user=www-data password=www-data dbname=<db> host=localhost
    sql: <column> AS geom FROM <table>

It's preferable to use simple geometries, too complex geometries can slow down the generation.


Configure MapCache
------------------

For the last zoom levels we can use MapCache.

To select the levels we generate the tiles an witch one we serve them using MapCache
we have an option 'min_resolution_seed' in the layer configuration.

The MapCache configuration look like this (default values):

.. code:: yaml

    mapcache:
        # The generated file
        config_file: apache/mapcache.xml
        # The memcache host
        memcache_host: localhost
        # the memcache port
        memcache_port: 11211

To generate the MapCache configuration we use the command::

    ./buildout/bin/generate_controller --mapcache

We can also use a buildout task to automatise it::

    [buildout]
    parts: += mapcache

    [mapcache]
    recipe = collective.recipe.cmd
    on_install = true
    on_update = true
    cmds =
      ./buildout/bin/generate_controller --mapcache
    uninstall_cmds =
      rm apache/mapcache.xml

And finally we can use the following Apache configuration to serve the
tiles, configure MapCache and redirect on MapCache for the last zoom levels
(11-19 in this example)::

    <Location /${vars:instanceid}/tiles>
        ExpiresActive on
        ExpiresDefault "now plus 8 hours"
        Header add Access-Control-Allow-Origin "*"
    </Location>
    Alias /${vars:instanceid}/tiles /var/sig/tilecache/<project>
    RewriteRule ^/${vars:instanceid}/tiles/1.0.0/([a-z0-9_]+)/([a-z0-9_]+)/([a-z0-9_]+)/([a-z0-9_]+)/1([1-9])/(.*)$ /${vars:instanceid}/mapcache/wmts/1.0.0/$1/$2/$3/$4/1$5/$6 [PT]
    MapCacheAlias /${vars:instanceid}/mapcache "${buildout:directory}/apache/mapcache.xml"


Configure S3
------------

The cache configuration is like this:

.. code:: yaml

    s3:
        type: s3
        # the s3 bucket name
        bucket: tiles
        # the used folder in the bucket [default to '']
        folder: ''
        # for GetCapabilities
        http_url: https://%(host)s/%(bucket)s/%(folder)s
        hosts:
        - wmts0.<host>

The bucket should already exists.

Before running an operation on S3 don't miss to set the following variable::

    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...


Configure SQS
-------------

The configuration in layer is like this:

.. code:: yaml

    sqs:
        # The region where the SQS queue is
        region: eu-west-1
        # The SQS queue name, it should already exists
        queue: the_name

The queue should be used only by one layer.

Before running the generation miss to set the following variable::

    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...

To use the SQS queue we should first fille the queue::

    ./buildout/bin/generate_controller --role master --layer <a_layer>

And then generate the tiles present in the SQS queue::

    ./buildout/bin/generate_controller --role slave --layer <a_layer>


Use MBTile
----------

The cache configuration is like this:

.. code:: yaml

    mbtiles:
        type: mbtiles
        http_url: http://taurus/tiles
        folder: /tmp/tiles/mbtiles

The advantage is to store all the tiles of a layer in one file.

To serve them there is a view named `serve_tiles`.


Generate tiles
--------------

Generate all the tiles::

    ./buildout/bin/generate_tiles

Generate a specific layer::

    ./buildout/bin/generate_tiles --layer=<a_layer>

Generate a specific zoom::

    ./buildout/bin/generate_tiles --zoom=5

Generate a specific zoom range::

    ./buildout/bin/generate_tiles --zoom=2-8

Generate a specific some zoom levels::

    ./buildout/bin/generate_tiles --zoom=2,4,7

Generate tiles on a bbox::

    ./buildout/bin/generate_tiles --bbox=<minx,miny,maxx,maxy>

Generate a tiles near a tile coordinate (useful for test)::

    ./buildout/bin/generate_tiles --near=z/x/y

Generate a tiles in a deferent cache than the default one::

    ./buildout/bin/generate_tiles --cache=<a_cache>

And don't forget to generate the WMTS Capabilities::

    ./buildout/bin/generate_controller --capabilities

Explain cost
-------------

Configuration (default values):

.. code:: yaml

    cost:
        # [nb/month]
        request_per_layers: 10000000
        # GeoData size [Go]
        esb_size: 100
        cloudfront:
            download: 0.12,
            get: 0.009
        ec2:
            usage: 0.17
        esb:
            io: 260.0,
            storage: 0.11
        esb_size: 100
        request_per_layers: 10000000
        s3:
            download: 0.12,
            get: 0.01,
            put: 0.01,
            storage: 0.125
        sqs:
            request: 0.01


Layer configuration (default values):

.. code:: yaml

    cost:
        metatile_generation_time: 30.0,
        tile_generation_time: 30.0,
        tile_size: 20.0,
        tileonly_generation_time: 60.0

The following commands can be used to know the time and cost to do generation::

    ./buildout/bin/generate_controller --cost

This suppose that you use a separate AWS host to generate the tiles.


Configure SNS
-------------

SNS can be used to send a message when the generation ends.

The configuration is like this:

.. code:: yaml

    sns:
        topic: arn:aws:sns:eu-west-1:your-account-id:tilecloud
        region: eu-west-1

The topic should already exists.

Before running the generation miss to set the following variable::

    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...


Openlayers pink tiles
---------------------

To avoid the OpenLayers red tiles on missing empty tiles we can add the following CSS rule:

.. code:: css

    .olImageLoadError {
        display: none;
    }


OpenLayers test page
--------------------

To generate a test page use::

    ./buildout/bin/generate_controller --openlayers-test


Configure and explain AWS
-------------------------

The generation can be deported on an external host.


Other usefull options
---------------------

``--verbose`` or ``-v``: used to display info message.

``--debug`` or ``-d``: used to display debug message, pleas use this option to report issue.
With the debug mode we don't catch exceptions, and we don't log time messages.

``--test <n>`` or ``-t <n>``: used to generate only ``<n>`` tiles, useful for test.


Important remarks
-------------------

Especially on S3 the grid name, the layer name, the dimensions, can't be changed
(understand if we want to change them we should regenerate all the tiles).

By default we also can't insert a zoom level, if you think that you need it we can
set the grid property ``matrix_identifier: resolution``, bit it don't work with MapCache.

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

.. code:: yaml

    layers:
        layer_name:
            sqs:
                # The region where the SQS queue is
                region: eu-west-1
                # The SQS queue name, it should already exists
                queue: the_name

2. Add debug option (``--debug``), please use it to report issue.

3. Now the ``sql`` request can return a set of geometries in a column names geom
   but the syntax change a little bit => ``<column> AS geom FROM <table>``
