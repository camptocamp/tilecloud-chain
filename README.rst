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


Configure grids
---------------

The ``grid`` describe hos the tiles are arranged.

Especially on ``s3`` be careful to choice every theres before generating the tiles.
It possible that to change one of them you should regenerate all the tiles.

The ``resolutions`` in [px/m] describe all the resolution available for this layer.
On raster layer have a look on the maximum resolution of the source files, it's not needed
to generate tiles in smaller resolution than the sources, it preferable to use the OpenLayers client zoom.
Notes that you can add a resolution at the end without regeneration all the tiles.

The ``bbox`` should correspond to the resolution extent, to reduce where the tiles are generated use the
``bbox`` available on the layer.

The ``srs`` specify the code of the projection.

The ``unit`` unit used by the projection.

The ``tile_size`` in [px] default to 256.

The ``matrix_identifier`` default to ``zoom`` can also be ``resolution`` is how the z index is build to store
the tiles, for example, for the resolutions ``[2, 1, 0.5]`` the used value are ``[0, 1, 2]`` it it's based on the zoom
and ``[2, 1, 0_5]`` if it's based on the resolution. The second has the advantage to allows to add a new
resolution without regenerate all the tiles, but it don't work with MapCache.


Configure caches
----------------

There tree available tiles cache: ``s3``, ``mbtile`` and ``filesystem``.

The best solution to store the tiles is ``s3``, ``mbtiles`` has the advantage to have only one file per
layer - style  dimensions. To serve the ``mbtile`` there is a view named ``serve_tiles``.

``s3`` need a ``bucket`` an a ``folder`` (default to '').

``mbtiles`` and ``filesystem`` just need a ``folder``.

On all the cache we can add some information to generate the url where the tiles are available.
This is needed to generate the capabilities. We can specify:

* ``http_url`` direct url to the tiles root.
* ``http_urls`` (array) urls ti the tiles root.
* ``http_url`` and ``hosts`` (array), where each value of ``hosts`` is used to replace ``%(host)s`` in ``http_url``.

In all case ``http_url`` or ``http_urls`` can include all attribute of this cache as ``%(attribute)s``.


Configure layers
----------------

First of all, all the attributes in ``layer_default`` are copied in all the layers to define the default values.

We have two ``type`` of layer: ``wms`` or ``mapnik``.

To start the common attributes are:

The ``min_resolution_seed`` included minimum resolution that is seeded, other resolutions are served by MapCache.

The ``bbox`` is used to limit the tiles generation.


WMTS layout
~~~~~~~~~~~

To generate the files path sand the WMTS capabilities we need some additional informations:

The ``mime_type`` of the tiles, it's also used by the WMS GetMap ant to upload the tile.

The ``wmts_style``, default to 'default'.

The ``extension`` is used to end the filename.

The ``dimensions`` (default to  []) is an array of object that have a ``name``, a ``default`` value specified in the capabilities,
a ``value`` to generate the tiles, and an array of ``values`` that all the possible value available in the capabilities.

For example if you generate the tiles and capabilities with the following configuration:

.. code:: yaml

    dimensions:
        -   name: DATE
            default: 2012
            value: 2012
            values: [2012]

than with the following configuration:

.. code:: yaml

    dimensions:
        -   name: DATE
            default: 2012
            value: 2013
            values: [2012, 2013]

We will have two set of tiles 2012 and 2013 that booth are accessible by the capabilities, and by default we will see the first set of tiles.


Metatiles
~~~~~~~~~

The metatiles are activated by setting ``meta`` to ``on`` (by default it's ``off``).

The metatiles are used for two thing first to generate multiple tiles with only one WMS query
by setting ``meta_size`` to 8 we will generate a square of 8 by 8 tiles in one shot.

The second usage of metatiles is to don't have cutted label name, this is solved by getting a bigger image
and cutting the borders. The ``meta_buffer`` should be set to a bigger value to the half size of the longest label.


Configure hash
~~~~~~~~~~~~~~

We can filter tiles and metatiles by using an hash.

The configuration of this hash is in the layer like this:

.. code:: yaml

    empty_metatile_detection:
        size: 740
        hash: 3237839c217b51b8a9644d596982f342f8041546
    empty_tile_detection:
        size: 921
        hash: 1e3da153be87a493c4c71198366485f290cad43c

To easily generate this configuration we can use the following command::

    ./buildout/bin/generate_tiles --get-hash <z/x/y> -l <layer_name>

Where ``<z/x/y>`` should refers en empty tile/metatile. Generally it's a good
idea to use z as the maximum zoom, x and y as 0.


Configure geom/sql
~~~~~~~~~~~~~~~~~~

We can generate the tiles only on some geometries stored in PostGis.

The configuration is in the layer like this:

.. code:: yaml

    connection: user=www-data password=www-data dbname=<db> host=localhost
    sql: <column> AS geom FROM <table>

It's preferable to use simple geometries, too complex geometries can slow down the generation.


WMS layers
~~~~~~~~~~

The additional value needed by the WMS is the URL of the server and the ``layers``.

The previously defined ``mime_type`` is also used in the WMS requests.


Mapnik layers
~~~~~~~~~~~~~

We ned to specify the ``mapfile`` path.

With mapnik we have the possibility to specify a ``data_buffer`` than we should set the unneeded ``meta_buffer`` to 0.

And the ``output_format`` used for the mapnik renderer, can be ``png``, ``png256``, ``jpeg``, ``grid`` (grid_renderer).


~~~~~~~~~~~~~~~~~~
Mapnik grid layers
~~~~~~~~~~~~~~~~~~

With mapnik we can generate UTFGrid tiles (JSON format that describe the tiles present on a corresponding tile)
by using the ``output_format`` 'grid', see also: https://github.com/mapnik/mapnik/wiki/MapnikRenderers#grid_renderer.

Specific configuration:

We have a specific way to ``drop_empty_utfgrid`` by using the ``on`` value.

We should specify the speudo pixel size [px] with the ``resolution``.

And the ``layers_fields`` that we want to get the attributes.
Object withe the layer name as key and the values in an array as value.

Il fact the Mapnik documentation say that's working only for one layer.

And don't miss the change the ``extension`` to ``json``, and the ``mime_type`` to ``application/utfgrid``
and the ``meta`` to ``off`` (not supported).

Configuration example:

.. code:: yaml

    grid:
        type: mapnik
        mapfile: style.mapnik
        output_format: grid
        extension: json
        mime_type: application/utfgrid
        drop_empty_utfgrid: on
        resolution: 4
        meta: off
        data_buffer: 128
        layers_fields:
            buildings: [name, street]

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
        # The memcache port
        memcache_port: 11211
        # The mapcache location, default is /mapcache
        location: /${vars:instanceid}/mapcache

    apache:
        # Generated file
        config_file: apache/tiles.conf
        # Serve tiles location, default is /tiles
        location: /${vars:instanceid}/tiles
        # Expires header in hours
        expires: 8

To generate the MapCache configuration we use the command::

    ./buildout/bin/generate_controller --generate-mapcache-config

To generate the Apache configuration we use the command::

    ./buildout/bin/generate_controller --generate-apache-config

We can also use a buildout task to automatise it::

    [buildout]
    parts: += mapcache

    [mapcache]
    recipe = collective.recipe.cmd
    on_install = true
    on_update = true
    cmds =
      ./buildout/bin/generate_controller --generate-mapcache-config
      ./buildout/bin/generate_controller --generate-apache-config
    uninstall_cmds =
      rm apache/mapcache.xml
      rm apache/tiles.conf.in


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

To use the SQS queue we should first fill the queue::

    ./buildout/bin/generate_tiles --role master --layer <a_layer>

And then generate the tiles present in the SQS queue::

    ./buildout/bin/generate_tiles --role slave --layer <a_layer>


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


Tiles error file
----------------

If we set a file path in config file:

.. code:: yaml

    generation:
        error_file: <path>

The tiles that in error will be appen to the file, ant the tiles can be regenerated with
``./buildout/bin/generate_tiles --layer <layer> --tiles-file <path>``.


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

To completely hide the missing tiles, useful for a transparent layer,
or for an opaque layer:

.. code:: css

    .olImageLoadError {
        background-color: white;
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

Release 0.6
~~~~~~~~~~~

1. Now the apache configuration can be generated with ``./buildout/bin/generate_controller --generate-apache-config``,
   it support ``filesystem`` ``cache`` and ``MapCache``.

2. Windows fixes.

3. Use console revrite (\r) to log generated tiles coordinates.

4. Now if no layers is specified in ``generation:default_layers`` we generate all layers by default.

5. Now bbox to be floats.

6. New ``--get-bbox`` option to get the bboy of a tile.

7. Add coveralls support (https://coveralls.io/r/sbrunner/tilecloud-chain).

8. Add an config option ``generation:error_file`` and a command option ``--tiles-file``
   to store and regenerate errored tiles. 


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
