Configuration
-------------

This guide covers configuration options for tilecloud-chain, a tool for generating and serving map tiles.

Configure Grids
~~~~~~~~~~~~~~

The ``grid`` configuration describes how map tiles are arranged in your tileset.

For cloud storage backends like ``s3`` or ``azure``, carefully consider grid settings before generating tiles, as changing them later requires regenerating all tiles.

Key grid settings:

- ``resolutions``: Tile resolutions in pixels/meter. For raster layers, consider the maximum resolution of source files. OpenLayers client zoom can handle display at smaller resolutions.

- ``bbox``: Bounding box that matches resolution extent. Warning: Do not use this to restrict tile generation area - use layer ``bbox`` instead.

- ``srs``: Projection code (e.g. ``EPSG:3857``)

- ``unit``: Unit used by projection (e.g. ``meters``)

- ``tile_size``: Tile dimensions in pixels (default: ``256``)

- ``matrix_identifier``: How z-index is built for tile storage:
    - ``zoom`` (default): Uses zoom levels ``[0, 1, 2]`` for the resolutions ``[2, 1, 0.5]``
    - ``resolution``: Uses resolution values ``[2, 1, 0_5]`` for the same resolutions
    Resolution-based indexing allows adding resolutions without regenerating tiles, but is incompatible with MapCache.

Configure Caches
~~~~~~~~~~~~~~~

Available tile cache backends:

- Cloud storage: ``s3``, ``azure``
- Local storage: ``bsddb``, ``mbtiles``, ``filesystem``

Cache configuration:

``s3`` requires:
- ``bucket``: S3 bucket name
- ``folder``: Path prefix (default: '')

``azure`` requires:
- ``container``: Azure container name

``mbtiles``, ``bsddb``, ``filesystem`` require:
- ``folder``: Storage directory path

On all the caches we can add some information to generate the URL where the tiles are available. This is
needed to generate the capabilities. We can specify:

-  ``http_url`` direct url to the tiles root.
-  ``http_urls`` (array) urls to the tiles root.
-  ``http_url`` and ``hosts`` (array), where each value of ``hosts`` is used to replace ``%(host)s`` in
   ``http_url``.

In all case ``http_url`` or ``http_urls`` can include all attributes of this cache as ``%(attribute)s``.

MBTiles vs Berkeley DB (``bsddb``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

-  Read performance: similar, eventually the MBTiles is 10% faster.
-  Write performance: The Berkeley DB is largely faster, about 10 times.
-  List the tiles: the MBTiles is largely faster, but we usually don't need it.

Configure layers
~~~~~~~~~~~~~~~~

First, all the attributes in ``layer_default`` are copied in all the layers to define the default values.

We have two ``type`` of layer: ``wms`` or ``mapnik``.

To start the common attributes are:

``min_resolution_seed`` the minimum resolution that is seeded, other resolutions are served by MapCache.

``bbox`` used to limit the tiles generation.

``px_buffer`` a buffer in px around the object area (geoms or extent).

WMTS layout
^^^^^^^^^^^

To generate the file paths and the WMTS capabilities we need additional information:

The ``mime_type`` of the tiles, it's also used by the WMS GetMap and to upload the tiles.

The ``wmts_style`` defaults to 'default'.

The ``extension`` is used to end the filename.

The ``dimensions`` (defaults to []) is an array of objects that have a ``name``, a ``default`` value specified
in the capabilities, a ``value`` to generate the tiles (it can be overwritten by an argument), and an array of
``values`` that contains all the possible values available in the capabilities.

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

We will have two set of tiles ``2012`` and ``2013``, both accessible by the capabilities, and by default we
will see the first set of tiles.

Meta tiles
^^^^^^^^^^

The meta tiles are activated by setting ``meta`` to ``on`` (by default it's ``off``).

The meta tiles are used for two things: first to generate multiple tiles with only one WMS query. By setting
``meta_size`` to 8 we will generate a square of 8 by 8 tiles in one shot.

The second usage of meta tiles is prevent cut label names: this is solved by getting a bigger image and cutting
the borders. The ``meta_buffer`` should be set to a bigger value than half the size of the longest label.

Configure hash
^^^^^^^^^^^^^^

We can filter tiles and meta tiles by using an hash.

The configuration of this hash is in the layer like this:

.. code:: yaml

    empty_metatile_detection:
        size: 740
        hash: 3237839c217b51b8a9644d596982f342f8041546
    empty_tile_detection:
        size: 921
        hash: 1e3da153be87a493c4c71198366485f290cad43c

To easily generate this configuration we can use the following command:

::

    generate-tiles --get-hash <z/x/y> -l <layer_name>

Where ``<z/x/y>`` should refer to an empty tile/metatile. Generally it's a good idea to use z as the maximum
zoom, x and y as 0.

Configure geom/sql
^^^^^^^^^^^^^^^^^^

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
    -   connection: user=postgresql password=postgresql dbname=tests host=localhost
        sql: the_geom AS geom FROM tests.polygon
    -   connection: user=postgresql password=postgresql dbname=tests host=localhost
        sql: the_geom AS geom FROM tests.point
        min_resolution: 10
        max_resolution: 20

It's preferable to use simple geometries, too complex geometries can slow down the generation.

Legends
^^^^^^^

To be able to generate legends with ``generate-controller --generate-legend-images`` you should have
``legend_mime`` and ``legend_extension`` in the layer configuration.

for example:

.. code:: yaml

    legend_mime: image/png
    legend_extension: png

Then it will create a legend image per layer and per zoom level named
``.../1.0.0/{{layer}}/{{wmts_style}}/legend{{zoom}}.{{legend_extension}}`` only if she is different from the
previous zoom level. If we have only one legend image it still stores in the file named
``legend0.{{legend_extension}}``.

When we do ``generate-controller --generate-wmts-capabilities`` we will at first parse the legend images to
generate a layer configuration like this:

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
^^^^^^^^^^

The additional value needed by the WMS is the URL of the server and the ``layers``.

The previously defined ``mime_type`` is also used in the WMS requests.

To customize the request you also have the attributes ``params``, ``headers`` and ``generate_salt``. In
``params`` you can specify additional parameter of the WMS request, in ``headers`` you can modify the request
headers. In ``version``, you can change the WMS version. See the Proxy/cache issue for additional information.

Mapnik layers
^^^^^^^^^^^^^

We need to specify the ``mapfile`` path.

With Mapnik we have the possibility to specify a ``data_buffer`` then we should set the unneeded
``meta_buffer`` to 0.

And the ``output_format`` used for the Mapnik renderer, can be ``png``, ``png256``, ``jpeg``, ``grid``
(grid_renderer).

Mapnik grid layers
''''''''''''''''''

With Mapnik we can generate UTFGrid tiles (JSON format that describes the tiles present on a corresponding
tile) by using the ``output_format`` 'grid', see also:
https://github.com/mapnik/mapnik/wiki/MapnikRenderers#grid_renderer.

Specific configuration:

We have a specific way to ``drop_empty_utfgrid`` by using the ``on`` value.

We should specify the pseudo pixel size [px] with the ``resolution``.

And the ``layers_fields`` that we want to get the attributes. Object with the layer name as key and the values
in an array as value.

In fact the Mapnik documentation says that's working only for one layer.

And don't forget to change the ``extension`` to ``json``, and the ``mime_type`` to ``application/utfgrid`` and
the ``meta`` to ``off`` (not supported).

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
~~~~~~~

We can configure some tile commands to process the tiles. They can be automatically be called in the tile
generation it we set the property ``post_process`` or ``pre_hash_post_process`` in the layer configuration.

The process is a set of names processes, and each one has a list of commands declared like this:

.. code:: yaml

    process:  # root process config
        optipng:  # the process command
        -   cmd: optipng %(args)s -q -zc9 -zm8 -zs3 -f5 -o %(out)s %(in)s  # the command line
            need_out: true  # if false the command rewrite the input file, default is false
            arg:  # argument used with the different log switches, in all cases default is ''
                default: '-q' # the argument used by default
                quiet: '-q' # the argument used in quiet mode
                verbose: '-v' # the argument used in verbose mode
                debug: '-log /tmp/optipng.log' # the argument user in debug mode

The ``cmd`` can have the following optional argument:

-  ``args`` the argument configured in the arg section.
-  ``in``, ``out`` the input and output files.
-  ``x``, ``y``, ``z`` the tile coordinates.

Logging
~~~~~~~

Tile logs can be saved to a PostgreSQL database with this configuration:

.. code:: yaml

    logging:
        database:
           dbname: my_db
           host: db
           port: 5432
           table: tilecloud_logs

    PostgreSQL authentication can be specified with the ``PGUSER`` and ``PGPASSWORD`` environment variables.
    If the database is not reachable, the process will wait until it is.


Tiles error file
~~~~~~~~~~~~~~~~

If we set a file path in configuration file:

.. code:: yaml

    generation:
        error_file: <path>

The tiles that's in error will be append to the file, ant the tiles can be regenerated with
``generate-tiles --tiles <path>``.

The ``<path>`` can be ``/tmp/error_{layer}_{datetime:%Y-%m-%d_%H:%M:%S}`` to have one file per layer and per
run.

The tiles file looks like:

``{.sourceCode .} # [time] some comments z/x/y # [time] the error z/x/y:+m/+m # [time] the error``

The first line is just a comment, the second, is for an error on a tile, and the third is for an error on a
meta tile.

Proxy/cache issue
~~~~~~~~~~~~~~~~~

In general we shouldn't generate tiles throw a proxy, to do that you should configure the layers as this:

.. code:: yaml

    layers_name:
        url: http://localhost/wms
        headers:
            Host: the_host_name

The idea is to get the WMS server on ``localhost`` and use the ``Host`` header to select the right Apache
VirtualHost.

To don't have cache we use the as default the headers:

.. code:: yaml

    headers:
        Cache-Control: no-cache, no-store
        Pragma: no-cache

And if you steal have issue you can add a ``SALT`` random argument by setting the layer parameter
``generate_salt`` to ``true``.

Alternate mime type
~~~~~~~~~~~~~~~~~~~

By default TileCloud support only the ``image/jpeg`` and ``image/png`` mime type.

Queue store
-----------

We can store the queue in different store: Redis (``redis``), Amazone SQS (``sqs``) or PostgreSQL
(``postgresql``), see the related section for the configuration.

To configure witch store to use we should set the ``queue_store`` in the configuration file,
default it's on Redis.

PostgreSQL
----------

Is it possible to store the queue in a PostgreSQL database, for that you should at least set the
``queue_store`` to ``postgresql`` in your (main) configuration file, and set the SqlAlchemy URL in the
configuration file or in the ``TILECLOUD_CHAIN_SQLALCHEMY_URL`` environment variable.

See the [configuration reference](https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/CONFIG.md#definitions/postgresql) for the other configuration possibilities.

With that the admin page is enhance with a job concept with enhanced status and they can be
canceled, and restarted.

Note that you should have an external process to clean the old jobs in the database.

Amazon services
---------------

Authentication
~~~~~~~~~~~~~~

To be authenticated by Amazon you should set those environments variable before running a command:

.. prompt:: bash

    export AWS_ACCESS_KEY_ID=...
    export AWS_SECRET_ACCESS_KEY=...

Configure S3
~~~~~~~~~~~~

The cache configuration is like this:

.. code:: yaml

    s3:
        type: s3
        # the s3 bucket name
        bucket: tiles
        # the used folder in the bucket [default is '']
        folder: ''
        # for GetCapabilities
        http_url: https://%(host)s/%(bucket)s/%(folder)s/
        cache_control: 'public, max-age=14400'
        hosts:
        - wmts0.<host>

The bucket should already exists. If you don't use Amazon's S3, you must specify the ``host`` and the
``tiles_url`` configuration parameter.

Configure SQS
~~~~~~~~~~~~~

The configuration in layer is like this:

.. code:: yaml

    sqs:
        # The region where the SQS queue is
        region: eu-west-1
        # The SQS queue name, it should already exists
        queue: the_name

The queue should be used only by one layer.

To use the SQS queue we should first fill the queue:

.. prompt:: bash

    generate-tiles --role master --layer <a_layer>

And then generate the tiles present in the SQS queue:

.. prompt:: bash

    generate-tiles --role slave --layer <a_layer>

For the slave to keep listening when the queue is empty and be able to support more than one layer, you must
enable the daemon mode and must not specify the layer:

.. prompt:: bash

    generate-tiles --role slave --daemon

Configure SNS
~~~~~~~~~~~~~

SNS can be used to send a message when the generation ends.

The configuration is like this:

.. code:: yaml

    sns:
        topic: arn:aws:sns:eu-west-1:your-account-id:tilecloud
        region: eu-west-1

The topic should already exists.

Amazon tool
~~~~~~~~~~~

Amazon has a command line tool (`homepage <http://aws.amazon.com/fr/cli/>`__).

To use it, add in the ``setup.py``:

-  ``awscli`` as an ``install_requires``,
-  ``'aws = awscli.clidriver:main',`` in the ``console_scripts``.

Than install it:

.. code:: bash

    pip install awscli

And use it:

.. code:: bash

    aws help

For example to delete many tiles do:

.. code:: bash

    aws s3 rm --recursive s3://your_bucket_name/folder


Configure Azure
~~~~~~~~~~~~~~~

The cache configuration is like this:

.. code:: yaml

    azure:
        type: azure
        # the Azure container name
        container: tiles
        # the used folder in the container [default is '']
        folder: ''
        # for GetCapabilities
        http_url: https://%(host)s/%(bucket)s/%(folder)s/
        cache_control: 'public, max-age=14400'
        hosts:
        - wmts0.<host>

The container should already exists.

For the authentication you should set those environment variables:
``AZURE_STORAGE_CONNECTION_STRING`` on your local environment,
or ``AZURE_STORAGE_ACCOUNT_URL`` if you run your container on Azure.


Other related configuration
---------------------------

Configure the server
--------------------

The server can be configure as it:

.. code:: yaml

    server:
        layers: a_layer # Restrict to serve an certain number of layers [default is all]
        cache: mbtiles # The used cache [default use generation/default_cache]
        # the URL without location to MapCache, [default is http://localhost/]
        geoms_redirect: true # use the geoms to redirect to MapCache [default is false]
        # allowed extension in the static path (default value), not used for s3.
        static_allow_extension: [jpeg, png, xml, js, html, css]

The minimal configuration is to enable it:

.. code:: yaml

    server: {}

You should also configure the ``http_url`` of the used cache, to something like
``https://%(host)s/${instanceid}/tiles`` or like ``https://%(host)s/${instanceid}/wsgi/tiles`` if you use the
Pyramid view.

Pyramid view
~~~~~~~~~~~~

To use the pyramid view use the following configuration:

.. code:: python

    config.get_settings().update({
        'tilegeneration_configfile': '<the configuration file>',
    })
    config.add_route('tiles', '/tiles/\*path')
    config.add_view('tilecloud_chain.server:PyramidView', route_name='tiles')

Internal WSGI server
~~~~~~~~~~~~~~~~~~~~

in ``application.ini``:

.. code::

    [app:tiles]
    use = egg:tilecloud_chain#server
    configfile = %(here)s/tilegeneration/config.yaml

Commands
--------

Available commands
~~~~~~~~~~~~~~~~~~

-  ``generate-controller`` generate the annex files like legend.
-  ``generate-tiles`` generate the tiles.
-  ``generate-copy`` copy the tiles from a cache to an other.
-  ``generate-process`` process the tiles using a configured process.
-  ``generate-cost`` estimate the cost.
-  ``import-expiretiles`` import the osm2pgsql expire-tiles file as geoms in the database.

Each commands have a ``--help`` option to give a full arguments help.

Generate tiles
~~~~~~~~~~~~~~

Generate all the tiles:

.. prompt:: bash

    generate-tiles

Generate a specific layer:

.. prompt:: bash

    generate-tiles --layer <a_layer>

Generate a specific zoom:

.. prompt:: bash

    generate-tiles --zoom 5

Generate a specific zoom range:

.. prompt:: bash

    generate-tiles --zoom 2-8

Generate a specific some zoom levels:

.. prompt:: bash

    generate-tiles --zoom 2,4,7

Generate tiles from an (error) tiles file:

.. prompt:: bash

    generate-tiles --layer <a_layer> --tiles <z/x/y>

Generate tiles on a bbox:

.. prompt:: bash

    generate-tiles --bbox <MINX> <MINY> <MAXX> <MAXY>

Generate a tiles near a tile coordinate (useful for test):

.. prompt:: bash

    generate-tiles --near <X> <Y>

Generate a tiles in a different cache than the default one:

.. prompt:: bash

    generate-tiles --cache <a_cache>


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

The following commands can be used to know the time and cost to do generation:

.. prompt:: bash

    generate-controller --cost

Useful options
~~~~~~~~~~~~~~

``--quiet`` or ``-q``: used to display only errors.

``--verbose`` or ``-v``: used to display info messages.

``--debug`` or ``-d``: used to display debug message, please use this option to report issue. With the debug
mode we don't catch exceptions, and we don't log time messages.

``--test <n>`` or ``-t <n>``: used to generate only ``<n>`` tiles, useful for test.


Mutualized
----------

The multi-tenant mode consist by having multiple project files with the projects related configurations
(layers, cache, ...) and one main configuration file with the global configuration (number of process,
log format, redis, ...).

Configuration keys which should be set in the main configuration file are identified in property's
descriptions of the ``schema.json`` file.

Important remarks
-----------------

Especially on S3 the grid name, the layer name, the dimensions, can't be changed (understand if we want to
change them we should regenerate all the tiles).

By default we also can't insert a zoom level, if you think that you need it we can set the grid property
``matrix_identifier: resolution``, bit it don't work with MapCache.

Please use the ``--debug`` to report issue.

Environment variables
---------------------

Environment Variables Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configuration can be customized through the following environment variables:

- ``TILEGENERATION_CONFIGFILE``: Path to the main configuration file
  (default: ``/etc/tilegeneration/config.yaml``)

- ``TILEGENERATION_MAIN_CONFIGFILE``: Path to the main configuration file when using multi-tenant mode
  (default: ``/etc/tilegeneration/config.yaml``)

- ``TILEGENERATION_HOSTSFILE``: Path to hosts mapping configuration
  (default: ``/etc/tilegeneration/hosts.yaml``)

- ``TILEGENERATION_MAX_GENERATION_TIME``: Maximum tile generation time in seconds before timeout
  (default: ``60``)

- ``TILECLOUD_CHAIN_MAX_OUTPUT_LENGTH``: Maximum output length shown in admin interface
  (default: ``1000``)

Logging Configuration:

- ``LOG_TYPE``: Logging output format, either ``console`` or ``json`` for Logstash
  (default: ``console``)

- ``TILECLOUD_CHAIN_LOG_LEVEL``: Log level for TileCloud Chain
  (default: ``INFO``)

- ``TILECLOUD_LOG_LEVEL``: Log level for TileCloud core
  (default: ``INFO``)

- ``C2CWSGI_LOG_LEVEL``: Log level for C2C WSGI
  (default: ``WARN``)

- ``OTHER_LOG_LEVEL``: Log level for other components
  (default: ``WARN``)

Valid log levels: ``DEBUG``, ``INFO``, ``WARN``, ``ERROR``, ``CRITICAL``

Server Configuration:

- ``TILE_SERVER_LOG_LEVEL``: Server component log verbosity
  (default: ``quiet``)

- ``TILE_MAPCACHE_LOG_LEVEL``: Internal MapCache log verbosity
  (default: ``verbose``)

- ``DEVELOPMENT``: Enable Pyramid development features if set to ``1``
  (default: ``0``)

- ``VISIBLE_ENTRY_POINT``: Base URL path for tile access
  (default: ``/tiles/``)

-  ``TILEGENERATION_HOSTS_LIMIT``: File that contains the maximum request per host
   (default: ``/etc/tilegeneration/hosts_limit.yaml``)

Worker Configuration:

- ``TILECLOUD_CHAIN_NB_TASKS``: Number of concurrent tasks to run in parallel
  (default: ``1``)

Admin and test pages
--------------------

On the URL `<base URL>/admin/` you can see the status of the generation, a tool to generate the tiles, and a link
to a test page.

Beware, the test page assumes we have configured only one grid.
