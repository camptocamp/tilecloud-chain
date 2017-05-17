TileCloud Chain
===============

.. image:: https://secure.travis-ci.org/camptocamp/tilecloud-chain.svg?branch=master
.. image:: https://coveralls.io/repos/camptocamp/tilecloud-chain/badge.png?branch=master

The goal of TileCloud Chain is to provide tools around tile generation on a chain like:

Source: WMS, Mapnik.

Optionally using an SQS queue, AWS host, SNS topic.

Destination in WMTS layout, on S3, on Berkley DB (``bsddb``), on MBTiles, or on local filesystem.

Features:

- Generate tiles.
- Drop empty tiles.
- Drop tiles outside a geometry or a bbox.
- Use MetaTiles.
- Generate the legend images.
- Generate GetCapabilities.
- Generate OpenLayers example page.
- Generate the Apache configuration.
- Obtain the hash of an empty tile.
- In future, measure tile generation speed.
- Calculate cost and generation time.
- In future, manage the AWS hosts that generate tiles.
- Delete empty tiles.
- Copy files between caches.
- Be able to use an SQS queue to dispatch the generation.
- Post processing the generated tiles.
- ...


.. contents:: Table of contents


------
Get it
------

With Docker
-----------

.. code:: bash

   # Login to docker hub
   docker login
   docker pull camptocamp/tilecloud-chain

   # Initialyse the project
   docker run -ti \
        --volume .:/project \
        camptocamp/tilecloud-chain \
        pcreate -s tilecloud_chain .

   # Run the commands
   DOCKER_ADRS=`ifconfig docker0 | head -n 2 | tail -n 1 | awk -F : '{print $2}' | awk '{print $1}'`
   docker run -ti \
        --volume .:/project \
        --add-host=db:${DOCKER_ADRS} \
        --add-host=mapserver:${DOCKER_ADRS} \
        --env=USER_NAME=`whoami` \
        --env=USER_ID=`id -u` \
        --env=GROUP_ID=`id -g` \
        --env=UMASK=`umask` \
        camptocamp/tilecloud-chain \
        run <a command>

To share the home folder you should add the arguments:

.. code:: bash

    --volume=${HOME}:${HOME} \
    --env=HOME=${HOME} \

The image also contains some tools needed to render OSM data like: ``fonts-dejavu``, ``node-carto`` and ``osm2pgsql``.

With pip
--------

Requirements::

    pg_config and a build environment.

Install::

    pip install tilecloud-chain
    pcreate -s tilecloud_chain .

Edit your layers configuration in ``./tilegeneration/config.yaml``.

`Default configuration file <https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/scaffolds/create/tilegeneration/config.yaml.mako_tmpl>`_.

---------
Configure
---------

Configure grids
---------------

The ``grid`` describes how the tiles are arranged.

Especially on ``s3`` be careful to choose every of the grid settings before generating the tiles.
If you change one of them you must regenerate all the tiles.

The ``resolutions`` in [px/m] describes all the resolutions available for this layer.
For a raster layer, have a look to the maximum resolution of the source files. It is not needed
to generate tiles at smaller resolutions than the sources, it is preferable to use the OpenLayers client zoom.
Note that you can add a resolution in the end without regenerating all the tiles.

The ``bbox`` should match the resolution of the extent. **CAREFUL: you will have big issue if you
use this parameter to generate the tile on a restricted area**: use the ``bbox`` on the layer instead.

The ``srs`` specifies the code of the projection.

The ``unit`` is the unit used by the projection.

The ``tile_size`` is the tile size in [px], defaults to 256.

The ``matrix_identifier`` is ``zoom`` by default and can also be set to ``resolution``. It specifies how the z index is build to store
the tiles, for example, for the resolutions ``[2, 1, 0.5]`` the used values are ``[0, 1, 2]`` based on the zoom
and ``[2, 1, 0_5]`` based on the resolution. The second has the advantage of allowing to add a new
resolution without regenerating all the tiles, but it does not work with MapCache.


Configure caches
----------------

The available tile caches are: ``s3``, ``bsddb``, ``mbtile`` and ``filesystem``.

The best solution to store the tiles, ``s3``, ``mbtiles`` and ``bsddb``, have the advantage of using only one file per
layer - style  dimensions. To serve the ``mbtile`` and the ``bsddb`` see `Distribute the tiles`_.

``s3`` needs a ``bucket`` and a ``folder`` (defaults to '').

``mbtiles``, ``bsddb`` and ``filesystem`` just need a ``folder``.

On all the caches we can add some information to generate the URL where the tiles are available.
This is needed to generate the capabilities. We can specify:

* ``http_url`` direct url to the tiles root.
* ``http_urls`` (array) urls to the tiles root.
* ``http_url`` and ``hosts`` (array), where each value of ``hosts`` is used to replace ``%(host)s`` in ``http_url``.

In all case ``http_url`` or ``http_urls`` can include all attributes of this cache as ``%(attribute)s``.

MBTiles vs Berkley DB (``bsddb``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Read performance: similar, eventually the MBTiles is 10% faster.
* Write performance: The Berkley DB is largely faster, about 10 times.
* List the tiles: the MBTiles is largely faster but we usually don't need it.


Configure layers
----------------

First of all, all the attributes in ``layer_default`` are copied in all the layers to define the default values.

We have two ``type`` of layer: ``wms`` or ``mapnik``.

To start the common attributes are:

``min_resolution_seed`` the minimum resolution that is seeded, other resolutions are served by MapCache.

``bbox`` used to limit the tiles generation.

``px_buffer`` a buffer in px around the object area (geoms or extent).


WMTS layout
~~~~~~~~~~~

To generate the file paths and the WMTS capabilities we need additional information:

The ``mime_type`` of the tiles, it's also used by the WMS GetMap and to upload the tiles.

The ``wmts_style`` defaults to 'default'.

The ``extension`` is used to end the filename.

The ``dimensions`` (defaults to  []) is an array of objects that have a ``name``,
a ``default`` value specified in the capabilities,
a ``value`` to generate the tiles (it can be overwritten by an argument),
and an array of ``values`` that contains all the possible values available in the capabilities.

For example if you generate the tiles and capabilities with the following configuration:

.. code:: yaml

    dimensions:
        -   name: DATE
            default: 2012
            value: 2012
            values: [2012]

then with the following configuration:

.. code:: yaml

    dimensions:
        -   name: DATE
            default: 2012
            value: 2013
            values: [2012, 2013]

We will have two set of tiles ``2012`` and ``2013``, both accessible by the capabilities, and by default we will see the first set of tiles.


Metatiles
~~~~~~~~~

The metatiles are activated by setting ``meta`` to ``on`` (by default it's ``off``).

The metatiles are used for two things: first to generate multiple tiles with only one WMS query.
By setting ``meta_size`` to 8 we will generate a square of 8 by 8 tiles in one shot.

The second usage of metatiles is prevent cut label names: this is solved by getting a bigger image
and cutting the borders. The ``meta_buffer`` should be set to a bigger value than half the size of the longest label.


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

    generate_tiles --get-hash <z/x/y> -l <layer_name>

Where ``<z/x/y>`` should refer to an empty tile/metatile. Generally it's a good
idea to use z as the maximum zoom, x and y as 0.


Configure geom/sql
~~~~~~~~~~~~~~~~~~

We can generate the tiles only on some geometries stored in PostGis.

The configuration is in the layer like this:

.. code:: yaml

    geoms:
    -   connection: user=www-data password=www-data dbname=<db> host=localhost
        sql: <column> AS geom FROM <table>
        min_resolution: <resolution> # included, optional, last win
        max_resolution: <resolution> # included, optional, last win

Example:

.. code:: yaml

    geoms:
    -   connection: user=postgres password=postgres dbname=tests host=localhost
        sql: the_geom AS geom FROM tests.polygon
    -   connection: user=postgres password=postgres dbname=tests host=localhost
        sql: the_geom AS geom FROM tests.point
        min_resolution: 10
        max_resolution: 20

It's preferable to use simple geometries, too complex geometries can slow down the generation.

Legends
~~~~~~~

To be able to generate legends with ``generate_controller --generate-legend-images``
you should have ``legend_mime`` and ``legend_extention`` in the layer configuration.

for example:

.. code:: yaml

   legend_mime: image/png
   legend_extention: png

Then it will create a legend image per layer and per zoom level named
``.../1.0.0/{{layer}}/{{wmts_style}}/legend{{zoom}}.{{legend_extention}}``
only if she is different than the previous zoom level. If we have only one legend image
it still stores in the file named ``legend0.{{legend_extention}}``.

When we do ``generate_controller --generate-wmts-capabilities`` we will at first
parse the legend images to generate a layer configuration like this:

.. code:: yaml

    legends:
    -   mime_type: image/png
        href: http://host/tiles/layer/style/legend0.png
        min_resolution: 500 # optional, [m/px]
        max_resolution: 2000 # optional, [m/px]
        min_scale: # if define overwrite the min_resolution [m/m]
        max_scale: # if define overwrite the max_resolution [m/m]

If you define a legends array in the layer configuration it is directly used to generate the capabilities.


WMS layers
~~~~~~~~~~

The additional value needed by the WMS is the URL of the server and the ``layers``.

The previously defined ``mime_type`` is also used in the WMS requests.

To customise the request you also have the attributes ``params``, ``headers``
and ``generate_salt``.
In ``params`` you can specify additional parameter of the WMS request,
in ``headers`` you can modify the request headers. See the
`Proxy/cache issue`_ for additional informations.


Mapnik layers
~~~~~~~~~~~~~

We need to specify the ``mapfile`` path.

With Mapnik we have the possibility to specify a ``data_buffer`` then we should set the unneeded ``meta_buffer`` to 0.

And the ``output_format`` used for the Mapnik renderer, can be ``png``, ``png256``, ``jpeg``, ``grid`` (grid_renderer).


~~~~~~~~~~~~~~~~~~
Mapnik grid layers
~~~~~~~~~~~~~~~~~~

With Mapnik we can generate UTFGrid tiles (JSON format that describes the tiles present on a corresponding tile)
by using the ``output_format`` 'grid', see also: https://github.com/mapnik/mapnik/wiki/MapnikRenderers#grid_renderer.

Specific configuration:

We have a specific way to ``drop_empty_utfgrid`` by using the ``on`` value.

We should specify the pseudo pixel size [px] with the ``resolution``.

And the ``layers_fields`` that we want to get the attributes.
Object with the layer name as key and the values in an array as value.

In fact the Mapnik documentation says that's working only for one layer.

And don't forget to change the ``extension`` to ``json``, and the ``mime_type`` to ``application/utfgrid``
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


Process
-------

We can configure some tile commands to process the tiles.
They can be automatically be called in the tile generation it we set the property
``post_process`` or ``pre_hash_post_process`` in the layer configuration.

The process is a set of names processes, and each one has a list of commands declared like this:

.. code:: yaml

    process:  # root process config
        optipng:  # the process command
        -   cmd: optipng %(args)s -q -zc9 -zm8 -zs3 -f5 -o %(out)s %(in)s  # the command line
            need_out: true  # if false the command rewrite the input file, default to false
            arg:  # argument used with the defferant log switches, all default to ''
                default: '-q' # the argument used by default
                quiet: '-q' # the arbument used in quiet mode
                verbose: '-v' # the argument used in verbose mode
                debug: '-log /tmp/optipng.log' # the argument user in debug mode

The ``cmd`` can have the following optional argument:

* ``args`` the argument configured in the `arg` section.
* ``in``, ``out`` the input and output files.
* ``x``, ``y``, ``z`` the tile coordinates.


Logging
-------

Tile logs can be saved to a PostgresQL database with this configuration:

..code:: yaml

    logging:
        database:
            dbname: my_db
            host: db
            port: 5432
            table: tilecloud_logs

PostgresQL authentication can be specified with the ``PGUSER`` and ``PGPASSWORD`` environment variables.
If the database is not reachable, the process will wait until it is.


Configure Apache
----------------

To generate the Apache configuration we use the command::

    generate_controller --generate-apache-config

The Apache configuration look like this (default values):

.. code:: yaml

    apache:
        # Generated file
        config_file: apache/tiles.conf
        # Serve tiles location, default is /tiles
        location: /${instanceid}/tiles
        # Expires header in hours
        expires: 8

        # Headers added to the ressponces
        headers:
            Cache-Control: max-age=864000, public

If we use a proxy to access to the tiles we can specify a different URL to access
to the tiles by adding the parameter ``tiles_url`` in the cache.

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
        location: /${instanceid}/mapcache


To generate the MapCache configuration we use the command::

    generate_controller --generate-mapcache-config

Tiles error file
----------------

If we set a file path in configuration file:

.. code:: yaml

    generation:
        error_file: <path>

The tiles that in error will be append to the file, ant the tiles can be regenerated with
``generate_tiles --layer <layer> --tiles <path>``.

The ``<path>`` can be ``/tmp/error_{layer}_{datetime:%Y-%m-%d_%H:%M:%S}``
to have one file per layer and per run.

The tiles file looks like:

.. code::

    # [time] some comments
    z/x/y # [time] the error
    z/x/y:+m/+m # [time] the error

The first line is just a comment, the second, is for an error on a tile,
and the third is for an error on a metatile.

Proxy/cache issue
-----------------

In general we shouldn't generate tiles throw a proxy, to do that you
should configure the layers as this:

.. code:: yaml

    layers_name:
        url: http://localhost/wms
        headers:
            Host: the_host_name

The idea is to get the WMS server on ``localhost`` and use the ``Host`` header
to select the right Apache VirtualHost.

To don't have cache we use the as default the headers:

.. code:: yaml

    headers:
        Cache-Control: no-cache, no-store
        Pragma: no-cache

And if you steal have issue you can add a ``SALT`` random argument by setting
the layer parameter ``generate_salt`` to ``true``.


Alternate mime type
-------------------

By default TileCloud support only the ``image/jpeg`` and ``image/png`` mime type.


----------------
Amazon services
----------------

Authentication
--------------

To be authenticated by Amazon you should set those environment variable before running a command::

    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...

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
        http_url: https://%(host)s/%(bucket)s/%(folder)s/
        hosts:
        - wmts0.<host>

The bucket should already exists. If you don't use Amazon's S3, you must specify the ``host`` and
the ``tiles_url`` configuration parameter.

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

To use the SQS queue we should first fill the queue::

    generate_tiles --role master --layer <a_layer>

And then generate the tiles present in the SQS queue::

    generate_tiles --role slave --layer <a_layer>

For the slave to keep listening when the queue is empty and be able to support more than one layer, you must
enable the daemon mode and must not specify the layer::

    generate_tiles --role slave --daemon


Configure SNS
-------------

SNS can be used to send a message when the generation ends.

The configuration is like this:

.. code:: yaml

    sns:
        topic: arn:aws:sns:eu-west-1:your-account-id:tilecloud
        region: eu-west-1

The topic should already exists.

Amazon tool
-----------

Amazon has a command line tool (`homepage <http://aws.amazon.com/fr/cli/>`_).

To use it, add in the ``setup.py``:

* ``awscli`` as an ``install_requires``,
* ``'aws = awscli.clidriver:main',`` in the ``console_scripts``.

Than install it:

.. code:: bash

    pip install awscli

And use it:

.. code:: bash

    aws help

For example to delete many tiles do:

.. code:: bash

    aws s3 rm --recursive s3://your_bucket_name/folder

---------------------------
Other related configuration
---------------------------

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


--------------------
Distribute the tiles
--------------------

There two ways to serve the tiles, with Apache configuration, or with an internal server.

The advantage of the internal server are:

* Can distribute Mbtiles or Berkley DB.
* Return ``204 No Content`` HTTP code in place of ``404 Not Found`` (or ``403 Forbidden`` for s3).
* Can be used in `KVP` mode.
* Can have zone per layer where are the tiles, otherwise it redirect on mapcache.

To generate the Apache configuration we use the command::

    generate_controller --generate-apache-config

The server can be configure as it:

.. code:: yaml

    server:
        layers: a_layer # Restrict to serve an certain number of layers [default to all]
        cache: mbtiles # The used cache [default use generation/default_cache]
        # the URL without location to MapCache, [default to http://localhost/]
        mapcache_base: http://localhost/
        mapcache_headers: # headers, can be used to access to an other Apache vhost [default to {}]
            Host: localhost
        geoms_redirect: true # use the geoms to redirect to MapCache [defaut to false]
        # allowed extension in the static path (default value), not used for s3.
        static_allow_extension: [jpeg, png, xml, js, html, css]

The minimal configuration is to enable it:

.. code:: yaml

    server: {}

You should also configure the ``http_url`` of the used `cache`, to something like
``https://%(host)s/${instanceid}/tiles`` or like
``https://%(host)s/${instanceid}/wsgi/tiles`` if you use the Pyramid view.

Pyramid view
------------

To use the pyramid view use the following configuration:

.. code:: python

    config.get_settings().update({
        'tilegeneration_configfile': '<the configuration file>',
    })
    config.add_route('tiles', '/tiles/\*path')
    config.add_view('tilecloud_chain.server:PyramidView', route_name='tiles')


Internal WSGI server
--------------------

in ``production.ini``::

    [app:tiles]
    use = egg:tilecloud_chain#server
    configfile = %(here)s/tilegeneration/config.yaml

with the Apache configuration::

    WSGIDaemonProcess tiles:${instanceid} display-name=%{GROUP} user=${modwsgi_user}
    WSGIScriptAlias /${instanceid}/tiles ${directory}/apache/wmts.wsgi
    <Location /${instanceid}/tiles>
        WSGIProcessGroup tiles:${instanceid}
        WSGIApplicationGroup %{GLOBAL}
    </Location>


--------
Commands
--------

Available commands
------------------

* ``generate_controller`` generate the annexe files like capabilities, legend, OpenLayers test page, MapCache configuration, Apache configuration.
* ``generate_tiles`` generate the tiles.
* ``generate_copy`` copy the tiles from a cache to an other.
* ``generate_process`` process the tiles using a configured process.
* ``generate_cost`` estimate the cost.
* ``import_expiretiles`` import the osm2pgsql expire-tiles file as geoms in the database.

Each commands have a ``--help`` option to give a full arguments help.


Generate tiles
--------------

Generate all the tiles::

    generate_tiles

Generate a specific layer::

    generate_tiles --layer <a_layer>

Generate a specific zoom::

    generate_tiles --zoom 5

Generate a specific zoom range::

    generate_tiles --zoom 2-8

Generate a specific some zoom levels::

    generate_tiles --zoom 2,4,7

Generate tiles from an (error) tiles file::

    generate_tiles --layer <a_layer> --tiles <a_file.tiles>

Generate tiles on a bbox::

    generate_tiles --bbox <MINX> <MINY> <MAXX> <MAXY>

Generate a tiles near a tile coordinate (useful for test)::

    generate_tiles --near <X> <Y>

Generate a tiles in a different cache than the default one::

    generate_tiles --cache <a_cache>

And don't forget to generate the WMTS Capabilities::

    generate_controller --capabilities


OpenLayers test page
--------------------

To generate a test page use::

    generate_controller --openlayers


------------
Explain cost
------------

Configuration (default values):

.. code:: yaml

    cost:
        # [nb/month]
        request_per_layers: 10000000
        cloudfront:
            download: 0.12,
            get: 0.009
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

    generate_controller --cost

Useful options
--------------

``--quiet`` or ``-q``: used to display only errors.

``--verbose`` or ``-v``: used to display info messages.

``--debug`` or ``-d``: used to display debug message, pleas use this option to report issue.
With the debug mode we don't catch exceptions, and we don't log time messages.

``--test <n>`` or ``-t <n>``: used to generate only ``<n>`` tiles, useful for test.

The logging format is configurable in the``config.yaml`` - ``generation/log_format``,
`See <http://docs.python.org/2/library/logging.html#logrecord-attributes>`_.


-----------------
Important remarks
-----------------

Especially on S3 the grid name, the layer name, the dimensions, can't be changed
(understand if we want to change them we should regenerate all the tiles).

By default we also can't insert a zoom level, if you think that you need it we can
set the grid property ``matrix_identifier: resolution``, bit it don't work with MapCache.

Please use the ``--debug`` to report issue.


------------
From sources
------------

Build it:

.. code:: bash

   git submodule update --recursive
   mkdir .build
   virtualenv venv
   venv/bin/pip install -e .
   venv/bin/pip install -r dev-requirements.txt


-------------
Run the tests
-------------

Setup your environment:

.. code:: bash

   sudo apt-get install optipng libdb-dev
   virtualenv .venv
   .venv/bin/pip install -r dev-requirements.txt -r requirements.txt mapnik bsddb3 -e .
   virtualenv --python=python3 .venv3
   .venv3/bin/pip install -r dev-requirements.txt -r requirements.txt bsddb3 -e .
   touch tilecloud_chain/OpenLayers.js
   docker-compose -f test-docker-compose.yml up

To run the tests:

.. code:: bash

   .venv/bin/python setup.py nosetests --logging-filter=tilecloud,tilecloud_chain --attr '!'nopy2
   .venv3/bin/python setup.py nosetests --logging-filter=tilecloud,tilecloud_chain --attr '!'nopy3
