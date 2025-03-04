# TileCloud-chain configuration

## Properties

- **`defaults`** _(object)_: Used to put YAML references.
- **`grids`** _(object)_: The WMTS grid definitions by grid name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids. Can contain additional properties.
  - **Additional properties**: Refer to _[#/definitions/grid](#definitions/grid)_.
- **`caches`** _(object)_: The tiles caches definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches. Can contain additional properties.
  - **Additional properties**: Refer to _[#/definitions/cache](#definitions/cache)_.
- **`layers`** _(object)_: The layers definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers. Can contain additional properties.
  - **Additional properties**: Refer to _[#/definitions/layer](#definitions/layer)_.
- **`process`** _(object)_: List of available commands by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#process. Can contain additional properties.
  - **Additional properties**: Refer to _[#/definitions/process](#definitions/process)_.
- **`generation`**: Refer to _[#/definitions/generation](#definitions/generation)_.
- **`sqs`** _(object)_: The Simple Queue Service configuration. Cannot contain additional properties.
  - **`queue`** _(string)_: The queue name. Default: `"tilecloud"`.
  - **`region`**: Refer to _[#/definitions/aws_region](#definitions/aws_region)_.
- **`sns`** _(object)_: The Simple Notification Service configuration, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sns. Cannot contain additional properties.
  - **`topic`** _(string, required)_: The topic.
  - **`region`**: Refer to _[#/definitions/aws_region](#definitions/aws_region)_.
- **`queue_store`** _(string)_: The used queue store. Must be one of: `["redis", "sqs", "postgresql"]`. Default: `"redis"`.
- **`redis`**: Refer to _[#/definitions/redis](#definitions/redis)_.
- **`postgresql`**: Refer to _[#/definitions/postgresql](#definitions/postgresql)_.
- **`openlayers`** _(object)_: Configuration used to generate the OpenLayers example page. Cannot contain additional properties.
  - **`srs`** _(string)_: The projection code. Default: `"EPSG:2056"`.
  - **`proj4js_def`** _(string)_: The `proj4js` definition, by default it will be build with pyproj.
  - **`center_x`** _(number)_: The center easting. Default: `2600000`.
  - **`center_y`** _(number)_: The center northing. Default: `1200000`.
  - **`zoom`** _(number)_: The initial zoom. Default: `3`.
- **`server`**: Refer to _[#/definitions/server](#definitions/server)_.
- **`cost`**: Refer to _[#/definitions/cost](#definitions/cost)_.
- **`metadata`**: Refer to _[#/definitions/metadata](#definitions/metadata)_.
- **`provider`**: Refer to _[#/definitions/provider](#definitions/provider)_.
- **`logging`**: Refer to _[#/definitions/logging](#definitions/logging)_.
- **`authentication`** _(object)_: The authentication configuration. Cannot contain additional properties.
  - **`github_repository`** _(string)_: The GitHub repository name, on witch one we will check the access rights.
  - **`github_access_type`** _(string)_: The kind of rights the user should have on the repository. Must be one of: `["push", "pull", "admin"]`. Default: `"pull"`.

## Definitions

- <a id="definitions/headers"></a>**`headers`** _(object)_: The headers that we send to the WMS backend. Can contain additional properties.
  - **Additional properties** _(string)_: The header value.
- <a id="definitions/grid"></a>**`grid`** _(object)_: The WMTS grid definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids. Cannot contain additional properties.
  - **`resolution_scale`** _(integer)_: The scale used to build a FreeTileGrid typically '2'.
  - **`resolutions`** _(array, required)_: The resolutions in pixel per meter.
    - **Items** _(number)_
  - **`bbox`** _(array, required)_: The bounding box in meter.
    - **Items** _(number)_
  - **`srs`** _(string, required)_: The projection reference.
  - **`proj4_literal`** _(string)_: The Proj4 definition.
  - **`unit`** _(string)_: The projection unit. Default: `"m"`.
  - **`tile_size`** _(integer)_: The tile size in pixel. Default: `256`.
  - **`matrix_identifier`** _(string)_: The identifier to use in the tiles URL, recommend to be resolution (default). Must be one of: `["zoom", "resolution"]`. Default: `"zoom"`.
- <a id="definitions/cache_wmtscapabilities_file"></a>**`cache_wmtscapabilities_file`** _(string)_: The generated WMTS capabilities file name. Default: `"1.0.0/WMTSCapabilities.xml"`.
- <a id="definitions/cache_http_url"></a>**`cache_http_url`** _(string)_: The HTTP URL %host will be replaces by one of the hosts.
- <a id="definitions/cache_hosts"></a>**`cache_hosts`** _(array)_: The host used to build the HTTP URLs.
  - **Items** _(string)_
- <a id="definitions/cache_http_urls"></a>**`cache_http_urls`** _(array)_
  - **Items** _(string)_
- <a id="definitions/cache_folder"></a>**`cache_folder`** _(string)_: The root folder of the cache. Default: `""`.
- <a id="definitions/cache_filesystem"></a>**`cache_filesystem`** _(object)_: Can contain additional properties.
  - **Additional properties** _(string)_
  - **`type`**: Must be: `"filesystem"`.
  - **`wmtscapabilities_file`**: Refer to _[#/definitions/cache_wmtscapabilities_file](#definitions/cache_wmtscapabilities_file)_.
  - **`http_url`**: Refer to _[#/definitions/cache_http_url](#definitions/cache_http_url)_.
  - **`hosts`**: Refer to _[#/definitions/cache_hosts](#definitions/cache_hosts)_.
  - **`http_urls`**: Refer to _[#/definitions/cache_http_urls](#definitions/cache_http_urls)_.
  - **`folder`**: Refer to _[#/definitions/cache_folder](#definitions/cache_folder)_.
- <a id="definitions/cache_s3"></a>**`cache_s3`** _(object)_: Can contain additional properties.
  - **Additional properties** _(string)_
  - **`type`**: Must be: `"s3"`.
  - **`wmtscapabilities_file`**: Refer to _[#/definitions/cache_wmtscapabilities_file](#definitions/cache_wmtscapabilities_file)_.
  - **`http_url`**: Refer to _[#/definitions/cache_http_url](#definitions/cache_http_url)_.
  - **`hosts`**: Refer to _[#/definitions/cache_hosts](#definitions/cache_hosts)_.
  - **`http_urls`**: Refer to _[#/definitions/cache_http_urls](#definitions/cache_http_urls)_.
  - **`tiles_url`** _(string)_: The template tiles URL on S3, the argument can be region, bucket and folder. Default: `"http://s3-{region}.amazonaws.com/{bucket}/{folder}"`.
  - **`host`** _(string)_: The S3 host. Default: `"s3-eu-west-1.amazonaws.com"`.
  - **`bucket`** _(string, required)_: The S3 bucker name.
  - **`region`**: Refer to _[#/definitions/aws_region](#definitions/aws_region)_.
  - **`cache_control`** _(string)_: The Cache-Control used to store tiles on S3.
  - **`folder`**: Refer to _[#/definitions/cache_folder](#definitions/cache_folder)_.
- <a id="definitions/cache_azure"></a>**`cache_azure`** _(object)_: Azure Blob Storage. Can contain additional properties.
  - **Additional properties** _(string)_
  - **`type`**: Must be: `"azure"`.
  - **`wmtscapabilities_file`**: Refer to _[#/definitions/cache_wmtscapabilities_file](#definitions/cache_wmtscapabilities_file)_.
  - **`http_url`**: Refer to _[#/definitions/cache_http_url](#definitions/cache_http_url)_.
  - **`hosts`**: Refer to _[#/definitions/cache_hosts](#definitions/cache_hosts)_.
  - **`http_urls`**: Refer to _[#/definitions/cache_http_urls](#definitions/cache_http_urls)_.
  - **`folder`**: Refer to _[#/definitions/cache_folder](#definitions/cache_folder)_.
  - **`container`** _(string, required)_: The Azure container name.
  - **`cache_control`** _(string)_: The Cache-Control used to store tiles on Azure.
- <a id="definitions/cache_mbtiles"></a>**`cache_mbtiles`** _(object)_: Can contain additional properties.
  - **Additional properties** _(string)_
  - **`type`**: Must be: `"mbtiles"`.
  - **`wmtscapabilities_file`**: Refer to _[#/definitions/cache_wmtscapabilities_file](#definitions/cache_wmtscapabilities_file)_.
  - **`http_url`**: Refer to _[#/definitions/cache_http_url](#definitions/cache_http_url)_.
  - **`hosts`**: Refer to _[#/definitions/cache_hosts](#definitions/cache_hosts)_.
  - **`http_urls`**: Refer to _[#/definitions/cache_http_urls](#definitions/cache_http_urls)_.
  - **`folder`**: Refer to _[#/definitions/cache_folder](#definitions/cache_folder)_.
- <a id="definitions/cache_bsddb"></a>**`cache_bsddb`** _(object)_: Can contain additional properties.
  - **Additional properties** _(string)_
  - **`type`**: Must be: `"bsddb"`.
  - **`wmtscapabilities_file`**: Refer to _[#/definitions/cache_wmtscapabilities_file](#definitions/cache_wmtscapabilities_file)_.
  - **`http_url`**: Refer to _[#/definitions/cache_http_url](#definitions/cache_http_url)_.
  - **`hosts`**: Refer to _[#/definitions/cache_hosts](#definitions/cache_hosts)_.
  - **`http_urls`**: Refer to _[#/definitions/cache_http_urls](#definitions/cache_http_urls)_.
  - **`folder`**: Refer to _[#/definitions/cache_folder](#definitions/cache_folder)_.
- <a id="definitions/cache"></a>**`cache`**: The tiles cache definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches.
  - **Any of**
    - : Refer to _[#/definitions/cache_filesystem](#definitions/cache_filesystem)_.
    - : Refer to _[#/definitions/cache_s3](#definitions/cache_s3)_.
    - : Refer to _[#/definitions/cache_azure](#definitions/cache_azure)_.
    - : Refer to _[#/definitions/cache_mbtiles](#definitions/cache_mbtiles)_.
    - : Refer to _[#/definitions/cache_bsddb](#definitions/cache_bsddb)_.
- <a id="definitions/layer_title"></a>**`layer_title`** _(string)_: The title, use to generate the capabilities.
- <a id="definitions/layer_grid"></a>**`layer_grid`** _(string)_: The used grid name.
- <a id="definitions/layer_bbox"></a>**`layer_bbox`** _(array)_: The bounding box where we will generate the tiles.
  - **Items** _(number)_
- <a id="definitions/layer_min_resolution_seed"></a>**`layer_min_resolution_seed`** _(number)_: The minimum resolutions to pre-generate.
- <a id="definitions/layer_px_buffer"></a>**`layer_px_buffer`** _(integer)_: The buffer in pixel used to calculate geometry intersection. Default: `0`.
- <a id="definitions/layer_meta"></a>**`layer_meta`** _(boolean)_: Use meta-tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles. Default: `false`.
- <a id="definitions/layer_meta_size"></a>**`layer_meta_size`** _(integer)_: The meta-tile size in tiles. Default: `5`.
- <a id="definitions/layer_meta_buffer"></a>**`layer_meta_buffer`** _(integer)_: The meta-tiles buffer in pixels. Default: `128`.
- <a id="definitions/layer_layers"></a>**`layer_layers`** _(string)_: The WMS layers.
- <a id="definitions/layer_wmts_style"></a>**`layer_wmts_style`** _(string)_: The WMTS style.
- <a id="definitions/layer_mime_type"></a>**`layer_mime_type`** _(string)_: The MIME type of the tiles.
- <a id="definitions/layer_extension"></a>**`layer_extension`** _(string)_: The layer extension.
- <a id="definitions/layer_dimension_name"></a>**`layer_dimension_name`** _(string)_: The dimension name.
- <a id="definitions/layer_dimensions"></a>**`layer_dimensions`** _(array)_: The WMTS dimensions.
  - **Items** _(object)_: Cannot contain additional properties.
    - **`name`**: Refer to _[#/definitions/layer_dimension_name](#definitions/layer_dimension_name)_.
    - **`generate`** _(array, required)_: The values that should be generate.
      - **Items** _(string)_
    - **`values`** _(array, required)_: The values present in the capabilities.
      - **Items** _(string)_
    - **`default`** _(string, required)_: The default value present in the capabilities.
- <a id="definitions/layer_legends"></a>**`layer_legends`** _(array)_: The provided legend.
  - **Items** _(object)_: Cannot contain additional properties.
    - **`mime_type`** _(string, required)_: The mime type used in the WMS request.
    - **`href`** _(string, required)_: The URL of the legend image.
    - **`width`** _(string)_: The width of the legend image.
    - **`height`** _(string)_: The height of the legend image.
    - **`min_scale`** _(string)_: The max scale of the legend image.
    - **`max_scale`** _(string)_: The max scale of the legend image.
    - **`min_resolution`** _(string)_: The max resolution of the legend image.
    - **`max_resolution`** _(string)_: The max resolution of the legend image.
- <a id="definitions/layer_legend_mime"></a>**`layer_legend_mime`** _(string)_: The mime type used to store the generated legend.
- <a id="definitions/layer_legend_extension"></a>**`layer_legend_extension`** _(string)_: The extension used to store the generated legend.
- <a id="definitions/layer_pre_hash_post_process"></a>**`layer_pre_hash_post_process`** _(string)_: Do an image post process before the empty hash check.
- <a id="definitions/layer_post_process"></a>**`layer_post_process`** _(string)_: Do an image post process after the empty hash check.
- <a id="definitions/layer_geoms"></a>**`layer_geoms`** _(array)_: The geometries used to determine where we should create the tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-geomsql.
  - **Items** _(object)_: Cannot contain additional properties.
    - **`connection`** _(string, required)_: The PostgreSQL connection string.
    - **`sql`** _(string, required)_: The SQL query that get the geometry in geom e.g. `the_geom AS geom FROM my_table`.
    - **`min_resolution`** _(number)_: The min resolution where the query is valid.
    - **`max_resolution`** _(number)_: The max resolution where the query is valid.
- <a id="definitions/layer_empty_tile_detection"></a>**`layer_empty_tile_detection`** _(object)_: The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash. Cannot contain additional properties.
  - **`size`** _(integer, required)_: The tile size.
  - **`hash`** _(string, required)_: The tile hash.
- <a id="definitions/layer_empty_metatile_detection"></a>**`layer_empty_metatile_detection`** _(object)_: The rules used to detect the empty meta-tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash. Cannot contain additional properties.
  - **`size`** _(integer, required)_: The meta-tile size.
  - **`hash`** _(string, required)_: The meta-tile hash.
- <a id="definitions/layer_cost"></a>**`layer_cost`** _(object)_: The rules used to calculate the cost. Cannot contain additional properties.
  - **`tileonly_generation_time`** _(number)_: The time to generate a tile without meta-tile. Default: `40`.
  - **`tile_generation_time`** _(number)_: The time to generate a tile from the meta-tile. Default: `30`.
  - **`metatile_generation_time`** _(number)_: The time to generate a meta-tile. Default: `30`.
  - **`tile_size`** _(number)_: The tile mean size in bytes. Default: `20`.
- <a id="definitions/layer_wms"></a>**`layer_wms`** _(object)_: Cannot contain additional properties.
  - **`type`**: Must be: `"wms"`.
  - **`title`**: Refer to _[#/definitions/layer_title](#definitions/layer_title)_.
  - **`grid`**: Refer to _[#/definitions/layer_grid](#definitions/layer_grid)_.
  - **`bbox`**: Refer to _[#/definitions/layer_bbox](#definitions/layer_bbox)_.
  - **`min_resolution_seed`**: Refer to _[#/definitions/layer_min_resolution_seed](#definitions/layer_min_resolution_seed)_.
  - **`px_buffer`**: Refer to _[#/definitions/layer_px_buffer](#definitions/layer_px_buffer)_.
  - **`meta`**: Refer to _[#/definitions/layer_meta](#definitions/layer_meta)_.
  - **`meta_size`**: Refer to _[#/definitions/layer_meta_size](#definitions/layer_meta_size)_. Default: `5`.
  - **`meta_buffer`**: Refer to _[#/definitions/layer_meta_buffer](#definitions/layer_meta_buffer)_. Default: `128`.
  - **`layers`**: Refer to _[#/definitions/layer_layers](#definitions/layer_layers)_.
  - **`wmts_style`**: Refer to _[#/definitions/layer_wmts_style](#definitions/layer_wmts_style)_.
  - **`mime_type`**: Refer to _[#/definitions/layer_mime_type](#definitions/layer_mime_type)_.
  - **`extension`**: Refer to _[#/definitions/layer_extension](#definitions/layer_extension)_.
  - **`dimensions`**: Refer to _[#/definitions/layer_dimensions](#definitions/layer_dimensions)_.
  - **`legends`**: Refer to _[#/definitions/layer_legends](#definitions/layer_legends)_.
  - **`legend_mime`**: Refer to _[#/definitions/layer_legend_mime](#definitions/layer_legend_mime)_.
  - **`legend_extension`**: Refer to _[#/definitions/layer_legend_extension](#definitions/layer_legend_extension)_.
  - **`pre_hash_post_process`**: Refer to _[#/definitions/layer_pre_hash_post_process](#definitions/layer_pre_hash_post_process)_.
  - **`post_process`**: Refer to _[#/definitions/layer_post_process](#definitions/layer_post_process)_.
  - **`geoms`**: Refer to _[#/definitions/layer_geoms](#definitions/layer_geoms)_.
  - **`empty_tile_detection`**: Refer to _[#/definitions/layer_empty_tile_detection](#definitions/layer_empty_tile_detection)_.
  - **`empty_metatile_detection`**: Refer to _[#/definitions/layer_empty_metatile_detection](#definitions/layer_empty_metatile_detection)_.
  - **`cost`**: Refer to _[#/definitions/layer_cost](#definitions/layer_cost)_.
  - **`url`** _(string, required)_: The WMS service URL.
  - **`generate_salt`** _(boolean)_: Should generate a salt to drop the cache. Default: `false`.
  - **`query_layers`** _(string)_: The layers use for query (To be used with the server).
  - **`info_formats`** _(array)_: The query info format.
    - **Items** _(string)_
  - **`params`** _(object)_: Additional parameters to the WMS query (like dimension). Can contain additional properties.
    - **Additional properties** _(string)_: The parameter value.
  - **`headers`**: Refer to _[#/definitions/headers](#definitions/headers)_.
  - **`version`** _(string)_: The used WMS version. Default: `"1.1.1"`.
- <a id="definitions/layer_mapnik"></a>**`layer_mapnik`** _(object)_: Cannot contain additional properties.
  - **`type`**: Must be: `"mapnik"`.
  - **`title`**: Refer to _[#/definitions/layer_title](#definitions/layer_title)_.
  - **`grid`**: Refer to _[#/definitions/layer_grid](#definitions/layer_grid)_.
  - **`bbox`**: Refer to _[#/definitions/layer_bbox](#definitions/layer_bbox)_.
  - **`min_resolution_seed`**: Refer to _[#/definitions/layer_min_resolution_seed](#definitions/layer_min_resolution_seed)_.
  - **`px_buffer`**: Refer to _[#/definitions/layer_px_buffer](#definitions/layer_px_buffer)_.
  - **`meta`**: Refer to _[#/definitions/layer_meta](#definitions/layer_meta)_.
  - **`meta_size`**: Refer to _[#/definitions/layer_meta_size](#definitions/layer_meta_size)_. Default: `1`.
  - **`meta_buffer`**: Refer to _[#/definitions/layer_meta_buffer](#definitions/layer_meta_buffer)_. Default: `0`.
  - **`layers`**: Refer to _[#/definitions/layer_layers](#definitions/layer_layers)_. Default: `"__all__"`.
  - **`wmts_style`**: Refer to _[#/definitions/layer_wmts_style](#definitions/layer_wmts_style)_.
  - **`mime_type`**: Refer to _[#/definitions/layer_mime_type](#definitions/layer_mime_type)_.
  - **`extension`**: Refer to _[#/definitions/layer_extension](#definitions/layer_extension)_.
  - **`dimensions`**: Refer to _[#/definitions/layer_dimensions](#definitions/layer_dimensions)_.
  - **`legends`**: Refer to _[#/definitions/layer_legends](#definitions/layer_legends)_.
  - **`legend_mime`**: Refer to _[#/definitions/layer_legend_mime](#definitions/layer_legend_mime)_.
  - **`legend_extension`**: Refer to _[#/definitions/layer_legend_extension](#definitions/layer_legend_extension)_.
  - **`pre_hash_post_process`**: Refer to _[#/definitions/layer_pre_hash_post_process](#definitions/layer_pre_hash_post_process)_.
  - **`post_process`**: Refer to _[#/definitions/layer_post_process](#definitions/layer_post_process)_.
  - **`geoms`**: Refer to _[#/definitions/layer_geoms](#definitions/layer_geoms)_.
  - **`empty_tile_detection`**: Refer to _[#/definitions/layer_empty_tile_detection](#definitions/layer_empty_tile_detection)_.
  - **`empty_metatile_detection`**: Refer to _[#/definitions/layer_empty_metatile_detection](#definitions/layer_empty_metatile_detection)_.
  - **`cost`**: Refer to _[#/definitions/layer_cost](#definitions/layer_cost)_.
  - **`mapfile`** _(string)_: The Mapnik map file.
  - **`data_buffer`** _(integer)_: The data buffer. Default: `128`.
  - **`output_format`** _(string)_: The Mapnik output format. Must be one of: `["png", "png256", "jpeg", "grid"]`. Default: `"png"`.
  - **`wms_url`** _(string)_: A WMS fallback URL (deprecated).
  - **`resolution`** _(integer)_: The resolution. Default: `4`.
  - **`layers_fields`** _(object)_: The Mapnik layers fields. Can contain additional properties.
    - **Additional properties** _(array)_: The Mapnik layer fields.
      - **Items** _(string)_
  - **`drop_empty_utfgrid`** _(boolean)_: Drop if the tile is empty. Default: `false`.
- <a id="definitions/layer"></a>**`layer`**: The layer definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers.
  - **Any of**
    - : Refer to _[#/definitions/layer_wms](#definitions/layer_wms)_.
    - : Refer to _[#/definitions/layer_mapnik](#definitions/layer_mapnik)_.
- <a id="definitions/process"></a>**`process`** _(array)_: A command.
  - **Items** _(object)_: Cannot contain additional properties.
    - **`cmd`** _(string, required)_: The shell command, available parameters: `%(in)s`, `%(out)s`,` %(args)s`, `%(x)s`, `%(y)s`, `%(z)s`.
    - **`need_out`** _(boolean)_: The command will generate an output in a file. Default: `false`.
    - **`arg`** _(object)_: Used to build the `%(args)`. Cannot contain additional properties.
      - **`default`** _(string)_: The arguments used by default.
      - **`verbose`** _(string)_: The arguments used on verbose mode.
      - **`debug`** _(string)_: The arguments used on debug mode.
      - **`quiet`** _(string)_: The arguments used on quiet mode.
- <a id="definitions/generation"></a>**`generation`** _(object)_: The configuration used for the generation. Cannot contain additional properties.
  - **`default_cache`** _(string)_: The default cache name to be used, default do 'default'. Default: `"default"`.
  - **`default_layers`** _(array)_: The default layers to be generated.
    - **Items** _(string)_
  - **`authorised_user`** _(string)_: The authorized user to generate the tiles (used to avoid permission issue on generated tiles) (main configuration).
  - **`maxconsecutive_errors`** _(integer)_: The maximum number of consecutive errors (main configuration). Default: `10`.
  - **`error_file`** _(string)_: File name generated with the tiles in error, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#tiles-error-file (main configuration).
  - **`number_process`** _(integer)_: Number of process used to generate the tiles (main configuration). Default: `1`.
- <a id="definitions/aws_region"></a>**`aws_region`** _(string)_: The region. Default: `"eu-west-1"`.
- <a id="definitions/postgresql"></a>**`postgresql`** _(object)_: The PostgreSQL configuration (main configuration), the schema can be configured with the `TILECLOUD_CHAIN_POSTGRESQL_SCHEMA` environment variable. Cannot contain additional properties.
  - **`sqlalchemy_url`** _(string)_: The SQLAlchemy URL (like: `postgresql+psycopg2://username:password@host:5432/database`) (main configuration), can also be set in the `TILECLOUD_CHAIN_SQLALCHEMY_URL` environment variable.
  - **`max_pending_minutes`** _(integer)_: The max pending minutes (main configuration). Default: `10`.
- <a id="definitions/redis"></a>**`redis`** _(object)_: The Redis configuration (main configuration). Cannot contain additional properties.
  - **`url`** _(string)_: The server URL (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_URL` environment variable.
  - **`sentinels`** _(array)_: The sentinels (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_SENTINELS` environment variable.
    - **Items** _(array)_: A sentinel (main configuration).
      - **Items**:
        - _string_: The sentinel host name (main configuration).
        - : The sentinel port (main configuration).
          - **Any of**
            - _string_
            - _integer_
  - **`connection_kwargs`** _(object)_: The Redis connection arguments (main configuration).
  - **`sentinel_kwargs`** _(object)_: The Redis sentinel arguments (main configuration).
  - **`service_name`** _(string)_: The service name (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_SERVICE_NAME` environment variable. Default: `"mymaster"`.
  - **`socket_timeout`** _(integer)_: The socket timeout (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_SOCKET_TIMEOUT` environment variable.
  - **`db`** _(integer)_: The database number (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_DB` environment variable.
  - **`queue`** _(string)_: The queue name (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_QUEUE` environment variable. Default: `"tilecloud"`.
  - **`timeout`** _(integer)_: The timeout (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_TIMEOUT` environment variable. Default: `5`.
  - **`pending_timeout`** _(integer)_: The pending timeout (main configuration). Default: `300`.
  - **`max_retries`** _(integer)_: The max retries (main configuration). Default: `5`.
  - **`max_errors_age`** _(integer)_: The max error age (main configuration), default is 1 day. Default: `86400`.
  - **`max_errors_nb`** _(integer)_: The max error number (main configuration). Default: `100`.
  - **`prefix`** _(string)_: The prefix (main configuration). Default: `"tilecloud_cache"`.
  - **`expiration`** _(integer)_: The meta-tile in queue expiration (main configuration), default is 8 hours. Default: `28800`.
  - **`pending_count`** _(integer)_: The pending count: the number of pending tiles get in one request (main configuration). Default: `10`.
  - **`pending_max_count`** _(integer)_: The pending max count: the maximum number of pending tiles get in one pass (if not generating other tiles, every second) (main configuration). Default: `10000`.
- <a id="definitions/server"></a>**`server`** _(object)_: Configuration used by the tile server, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#distribute-the-tiles. Cannot contain additional properties.
  - **`cache`** _(string)_: The used cache name.
  - **`layers`** _(array)_: Layers available in the server, default is all layers.
    - **Items** _(string)_
  - **`geoms_redirect`** _(boolean)_: Take care on the geometries. Default: `false`.
  - **`static_allow_extension`** _(array)_: The allowed extension of static files. Default: `["jpeg", "png", "xml", "js", "html", "css"]`.
    - **Items** _(string)_
  - **`wmts_path`** _(string)_: The sub-path for the WMTS (main configuration). Default: `"wmts"`.
  - **`static_path`** _(string)_: The sub-path for the static files (main configuration). Default: `"static"`.
  - **`admin_path`** _(string)_: The sub-path for the admin (main configuration). Default: `"admin"`.
  - **`expires`** _(integer)_: The browser cache expiration in hours. Default: `8`.
  - **`predefined_commands`** _(array)_: The predefined commands used to generate the tiles.
    - **Items** _(object)_: Cannot contain additional properties.
      - **`command`** _(string)_: The command to run.
      - **`name`** _(string)_: The name used in the admin interface.
  - **`allowed_commands`** _(array)_: The allowed commands (main configuration). Default: `["generate-tiles", "generate-controller", "generate-cost"]`.
    - **Items** _(string)_
  - **`allowed_arguments`** _(array)_: The allowed arguments (main configuration). Default: `["--layer", "--get-hash", "--generate-legend-images", "--get-bbox", "--ignore-error", "--bbox", "--zoom", "--test", "--near", "--time", "--measure-generation-time", "--no-geom", "--dimensions"]`.
    - **Items** _(string)_
  - **`admin_footer`** _(string)_: The footer of the admin interface.
  - **`admin_footer_classes`** _(string)_: The CSS classes used on the footer of the admin interface.
- <a id="definitions/cost"></a>**`cost`** _(object)_: The configuration use to calculate the cast (unmaintained). Cannot contain additional properties.
  - **`request_per_layers`** _(integer)_: Tile request per hours. Default: `10000000`.
  - **`s3`** _(object)_: The S3 cost (main configuration). Cannot contain additional properties.
    - **`storage`** _(number)_: The storage cost in $ / Gio / month (main configuration). Default: `0.125`.
    - **`put`** _(number)_: The cost of put in $ per 10 000 requests (main configuration). Default: `0.01`.
    - **`get`** _(number)_: The cost of get in $ per 10 000 requests (main configuration). Default: `0.01`.
    - **`download`** _(number)_: The cost of download in $ per Gio (main configuration). Default: `0.12`.
  - **`cloudfront`** _(object)_: The CloudFront cost (main configuration). Cannot contain additional properties.
    - **`get`** _(number)_: The cost of get in $ per 10 000 requests (main configuration). Default: `0.009`.
    - **`download`** _(number)_: The cost of download in $ per Gio (main configuration). Default: `0.12`.
  - **`sqs`** _(object)_: The SQS cost, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sqs (main configuration). Cannot contain additional properties.
    - **`request`** _(number)_: The cost of request in $ per 1 000 000 requests (main configuration). Default: `0.01`.
- <a id="definitions/metadata"></a>**`metadata`** _(object)_: The configuration of the WMTS capabilities metadata. Cannot contain additional properties.
  - **`title`** _(string, required)_: The title.
  - **`abstract`** _(string)_: The abstract.
  - **`servicetype`** _(string)_: The service type. Default: `"OGC WMTS"`.
  - **`keywords`** _(array)_: The keywords.
    - **Items** _(string)_
  - **`fees`** _(string)_: The fees.
  - **`access_constraints`** _(string)_: The access constraints.
- <a id="definitions/provider"></a>**`provider`** _(object)_: The provider. Cannot contain additional properties.
  - **`name`** _(string)_
  - **`url`** _(string)_: The public URL.
  - **`contact`** _(object)_: The contact. Cannot contain additional properties.
    - **`name`** _(string)_
    - **`position`** _(string)_
    - **`info`** _(object)_: The information. Cannot contain additional properties.
      - **`phone`** _(object)_: The phone. Cannot contain additional properties.
        - **`voice`** _(string)_: The voice number.
        - **`fax`** _(string)_: The fax number.
      - **`address`** _(object)_: The address. Cannot contain additional properties.
        - **`delivery`** _(string)_: The delivery.
        - **`city`** _(string)_: The city.
        - **`area`** _(string)_: The area.
        - **`postal_code`** _(integer)_: The postal code.
        - **`country`** _(string)_: The country.
        - **`email`** _(string)_: The email.
- <a id="definitions/logging"></a>**`logging`** _(object)_: The logging configuration to database, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#logging (main configuration). Cannot contain additional properties.
  - **`database`** _(object, required)_: The database (main configuration). Cannot contain additional properties.
    - **`host`** _(string)_: The host (main configuration).
    - **`port`** _(integer)_: The port (main configuration). Default: `5432`.
    - **`dbname`** _(string, required)_: The database name (main configuration).
    - **`table`** _(string, required)_: The table name (main configuration).
    - **`user`** _(string, required)_: The user name (main configuration).
    - **`password`** _(string, required)_: The password (main configuration).
