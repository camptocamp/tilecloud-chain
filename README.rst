TileCloud Chain
===============

The goal of TileCloud Chain is to have tools around tile generation on a chain like:

Source: WMS, Mapnik.

Optionally use an SQS queue, AWS host, SNS topic.

Destination in WMTS layout, on S3, on Berkley DB (``bsddb``), on MBTiles, or on local filesystem.

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


------
Get it
------

Install::

    virtualenv buildout
    ./buildout/bin/pip install tilecloud-chain
    ./buildout/bin/pcreate -s tilecloud_chain .

Edit your layers configuration in ``./tilegeneration/config.yaml``.

`Default configuration file <https://github.com/sbrunner/tilecloud-chain/blob/master/tilecloud_chain/scaffolds/create/tilegeneration/config.yaml.in_tmpl>`_.

---------
Configure
---------

Configure grids
---------------

The ``grid`` describe hos the tiles are arranged.

Especially on ``s3`` be careful to choice every theres before generating the tiles.
It possible that to change one of them you should regenerate all the tiles.

The ``resolutions`` in [px/m] describe all the resolution available for this layer.
On raster layer have a look on the maximum resolution of the source files, it's not needed
to generate tiles in smaller resolution than the sources, it preferable to use the OpenLayers client zoom.
Notes that you can add a resolution at the end without regeneration all the tiles.

The ``bbox`` should correspond to the resolution extent. **CAREFUL: you will have big issue if you
use this parameter to generate the tile on a restricted area** use the ``bbox`` on the layer instead.

The ``srs`` specify the code of the projection.

The ``unit`` unit used by the projection.

The ``tile_size`` in [px] default to 256.

The ``matrix_identifier`` default to ``zoom`` can also be ``resolution`` is how the z index is build to store
the tiles, for example, for the resolutions ``[2, 1, 0.5]`` the used value are ``[0, 1, 2]`` it it's based on the zoom
and ``[2, 1, 0_5]`` if it's based on the resolution. The second has the advantage to allows to add a new
resolution without regenerate all the tiles, but it don't work with MapCache.


Configure caches
----------------

The available tiles cache are: ``s3``, ``bsddb``, ``mbtile`` and ``filesystem``.

The best solution to store the tiles is ``s3``, ``mbtiles`` and ``bsddb`` has the advantage to have only one file per
layer - style  dimensions. To serve the ``mbtile`` and the ``bsddb`` see `Distribute the tiles`_.

``s3`` need a ``bucket`` and a ``folder`` (default to '').

``mbtiles``, ``bsddb`` and ``filesystem`` just need a ``folder``.

On all the cache we can add some information to generate the URL where the tiles are available.
This is needed to generate the capabilities. We can specify:

* ``http_url`` direct url to the tiles root.
* ``http_urls`` (array) urls ti the tiles root.
* ``http_url`` and ``hosts`` (array), where each value of ``hosts`` is used to replace ``%(host)s`` in ``http_url``.

In all case ``http_url`` or ``http_urls`` can include all attribute of this cache as ``%(attribute)s``.

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

The ``min_resolution_seed`` included minimum resolution that is seeded, other resolutions are served by MapCache.

The ``bbox`` is used to limit the tiles generation.


WMTS layout
~~~~~~~~~~~

To generate the files path sand the WMTS capabilities we need some additional informations:

The ``mime_type`` of the tiles, it's also used by the WMS GetMap ant to upload the tile.

The ``wmts_style``, default to 'default'.

The ``extension`` is used to end the filename.

The ``dimensions`` (default to  []) is an array of object that have a ``name``,
a ``default`` value specified in the capabilities,
a ``value`` to generate the tiles (it can be overwrite by an argument),
and an array of ``values`` that all the possible value available in the capabilities.

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

We will have two set of tiles ``2012`` and ``2013`` that booth are accessible by the capabilities, and by default we will see the first set of tiles.


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
    geoms:
    -   sql: <column> AS geom FROM <table>
        min_resolution: <resolution> # included, optional, last win
        max_resolution: <resolution> # included, optional, last win

Example:

.. code:: yaml

    connection: user=postgres password=postgres dbname=tests host=localhost
    geoms:
    -   sql: the_geom AS geom FROM tests.polygon
    -   sql: the_geom AS geom FROM tests.point
        min_resolution: 10
        max_resolution: 20

It's preferable to use simple geometries, too complex geometries can slow down the generation.

Legends
~~~~~~~

To be able to generate legends with ``./buildout/bin/generate_controler --generate_legend_images``
you should have ``legend_mime`` and ``legend_extention`` in the layer config.

for example:

.. code:: yaml

   legend_mime: image/png
   legend_extention: png

Then it will create a legend image per layer and per zoom level named 
``.../1.0.0/{{layer}}/{{wmts_style}}/legend{{zoom}}.{{legend_extention}}``
only if she is deferent than the previous zoom level. Than if we have only one legend image
it sill store in the file named ``legend0.{{legend_extention}}``.

When we do ``./buildout/bin/generate_controler --generate_wmts-capabilities`` we will at first
parse the legend images to generate a layer config like this:

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

With Mapnik we have the possibility to specify a ``data_buffer`` than we should set the unneeded ``meta_buffer`` to 0.

And the ``output_format`` used for the Mapnik renderer, can be ``png``, ``png256``, ``jpeg``, ``grid`` (grid_renderer).


~~~~~~~~~~~~~~~~~~
Mapnik grid layers
~~~~~~~~~~~~~~~~~~

With Mapnik we can generate UTFGrid tiles (JSON format that describe the tiles present on a corresponding tile)
by using the ``output_format`` 'grid', see also: https://github.com/mapnik/mapnik/wiki/MapnikRenderers#grid_renderer.

Specific configuration:

We have a specific way to ``drop_empty_utfgrid`` by using the ``on`` value.

We should specify the pseudo pixel size [px] with the ``resolution``.

And the ``layers_fields`` that we want to get the attributes.
Object withe the layer name as key and the values in an array as value.

In fact the Mapnik documentation say that's working only for one layer.

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

Tiles error file
----------------

If we set a file path in config file:

.. code:: yaml

    generation:
        error_file: <path>

The tiles that in error will be append to the file, ant the tiles can be regenerated with
``./buildout/bin/generate_tiles --layer <layer> --tiles <path>``.

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


----------------
Amazon services
----------------

Authentication
-------------

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
        http_url: https://%(host)s/%(bucket)s/%(folder)s
        hosts:
        - wmts0.<host>

The bucket should already exists.

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

    ./buildout/bin/generate_tiles --role master --layer <a_layer>

And then generate the tiles present in the SQS queue::

    ./buildout/bin/generate_tiles --role slave --layer <a_layer>

Configure SNS
-------------

SNS can be used to send a message when the generation ends.

The configuration is like this:

.. code:: yaml

    sns:
        topic: arn:aws:sns:eu-west-1:your-account-id:tilecloud
        region: eu-west-1

The topic should already exists.

Configure and explain EC2
-------------------------

The generation can be deported on an external host.

This will deploy the code the database and the geodata to an external host,
configure or build the application, configure apache, and run the tile generation.

This work only with S3 and needs SQS.

In a future version it will start the new EC2 host, join an ESB, run the tile generation,
and do snapshot on the ESB.

The configuration is like this:

.. code:: yaml

    ec2:
        geodata_folder: /var/sig
        deploy_config: tilegeneration/deploy.cfg
        build_cmds:
        - rm .installed.cfg
        - python bootstrap.py --distribute -v 1.7.1
        - ./buildout/bin/buildout -c buildout_tilegeneration.cfg install template
        deploy_user: deploy
        code_folder: /var/www/vhost/project/private/project
        apache_config: /var/www/vhost/project/conf/tilegeneration.conf
        apache_content: Include /var/www/vhost/project/private/project/apache/\*.conf

Amazon tool
-----------

Amazon has a command line tool (`homepage <http://aws.amazon.com/fr/cli/>`_).

To use it, add in the ``setup.py``:

* ``awscli`` as an ``install_requires``, 
* ``'aws = awscli.clidriver:main',`` in the ``console_scripts``.

Than install it: 

.. code:: bash

    ./buildout/bin/buildout install eggs

And use it:

.. code:: bash

    ./buildout/bin/aws help

For example to delete many tiles do:

.. code:: bash

    ./buildout/bin/aws s3 rm --recursive s3://your_bucket_name/folder

---------------------------
Other related configuration
---------------------------

Generate configuration in buildout
----------------------------------

We can also use a buildout task to automatise it::

    [buildout]
    parts += mapcache

    [mapcache]
    recipe = collective.recipe.cmd
    on_install = true
    on_update = true
    cmds =
      ./buildout/bin/generate_controller --generate-mapcache-config
      ./buildout/bin/generate_controller --generate-apache-config
    uninstall_cmds =
      rm apache/mapcache.xml
      rm apache/tiles.conf

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

    ./buildout/bin/generate_controller --generate-apache-config

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

The minimal config is to enable it:

.. code:: yaml

    server: {}

You should also configure the ``http_url`` of the used `cache`, to something like
``https://%(host)s/${instanceid}/tiles`` or like
``https://%(host)s/${instanceid}/wsgi/tiles`` if you use the Pyramid view.

Pyramid view
------------

To use the pyramid view use the following config:

.. code:: python

    config.get_settings().update({
        'tilegeneration_configfile': '<the configuration file>',
    })
    config.add_route('tiles', '/tiles/\*path')
    config.add_view('tilecloud_chain.server:PyramidView', route_name='tiles')


Internal WSGI server
--------------------

To use the WSGI server with buildout, add in ``buildout.cfg``::

    [buildout]
        parts = ...
            modwsgi_tiles
            ...

    [modwsgi_tiles]
    recipe = collective.recipe.modwsgi
    eggs = tileswitch
    config-file = ${buildout:directory}/production.ini
    app_name = tiles

in ``production.ini``::

    [app:tiles]
    use = egg:tilecloud_chain#server
    configfile = %(here)s/tilegeneration/config.yaml

with the apache configuration::

    WSGIDaemonProcess tiles:${vars:instanceid} display-name=%{GROUP} user=${vars:modwsgi_user}
    WSGIScriptAlias /${vars:instanceid}/tiles ${buildout:directory}/buildout/parts/modwsgi_tiles/wsgi
    <Location /${vars:instanceid}/tiles>
        WSGIProcessGroup tiles:${vars:instanceid}
        WSGIApplicationGroup %{GLOBAL}
    </Location>


--------
Commands
--------

Available commands
------------------

* ``./buildout/bin/generate_controller`` generate the annexe files like capabilities, legend, OpenLayers test page, MapCacke config, Apache config.
* ``./buildout/bin/generate_tiles`` generate the tiles.
* ``./buildout/bin/generate_copy`` copy the tiles from a cache to an other.
* ``./buildout/bin/generate_process`` prosses the tiles using a configured prosess.
* ``./buildout/bin/generate_cost`` estimate the cost.
* ``./buildout/bin/generate_amazon`` generate the tiles using EC2.
* ``./buildout/bin/import_expiretiles`` import the osm2pgsql expire-tiles file as geoms in the database.

Each commands have a ``--help`` option to give a full arguments help.


Generate tiles
--------------

Generate all the tiles::

    ./buildout/bin/generate_tiles

Generate a specific layer::

    ./buildout/bin/generate_tiles --layer <a_layer>

Generate a specific zoom::

    ./buildout/bin/generate_tiles --zoom 5

Generate a specific zoom range::

    ./buildout/bin/generate_tiles --zoom 2-8

Generate a specific some zoom levels::

    ./buildout/bin/generate_tiles --zoom 2,4,7

Generate tiles from an (error) tiles file::

    ./buildout/bin/generate_tiles --layer <a_layer> --tiles <a_file.tiles>

Generate tiles on a bbox::

    ./buildout/bin/generate_tiles --bbox <MINX> <MINY> <MAXX> <MAXY>

Generate a tiles near a tile coordinate (useful for test)::

    ./buildout/bin/generate_tiles --near <X> <Y>

Generate a tiles in a deferent cache than the default one::

    ./buildout/bin/generate_tiles --cache <a_cache>

And don't forget to generate the WMTS Capabilities::

    ./buildout/bin/generate_controller --capabilities


OpenLayers test page
--------------------

To generate a test page use::

    ./buildout/bin/generate_controller --openlayers-test


------------
Explain cost
------------

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

This suppose that you use a separate EC2 host to generate the tiles.

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


-----------
From source
-----------

Build it::

    python bootstrap.py --distribute -v 1.7.1
    ./buildout/bin/buildout
