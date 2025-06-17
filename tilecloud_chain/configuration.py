"""
Automatically generated file from a JSON schema.
"""


from typing import Any, Literal, TypedDict, Union
from typing_extensions import Required


ADMIN_PATH_DEFAULT = 'admin'
""" Default value of the field path 'Server admin_path' """



ALLOWED_ARGUMENTS_DEFAULT = ['--layer', '--get-hash', '--generate-legend-images', '--get-bbox', '--ignore-error', '--bbox', '--zoom', '--test', '--near', '--time', '--measure-generation-time', '--no-geom', '--dimensions']
""" Default value of the field path 'Server allowed_arguments' """



ALLOWED_COMMANDS_DEFAULT = ['generate-tiles', 'generate-controller', 'generate-cost']
""" Default value of the field path 'Server allowed_commands' """



AWS_REGION_DEFAULT = 'eu-west-1'
""" Default value of the field path 'aws_region' """



class Address(TypedDict, total=False):
    """
    Address.

    The address
    """

    delivery: str
    """
    Delivery.

    The delivery
    """

    city: str
    """
    City.

    The city
    """

    area: str
    """
    Area.

    The area
    """

    postal_code: int
    """
    Postal code.

    The postal code
    """

    country: str
    """
    Country.

    The country
    """

    email: str
    """
    Email.

    The email
    """



class Argument(TypedDict, total=False):
    """
    Argument.

    Used to build the `%(args)`
    """

    default: str
    """
    Properties.

    The arguments used by default
    """

    verbose: str
    """
    Verbose.

    The arguments used on verbose mode
    """

    debug: str
    """
    Debug.

    The arguments used on debug mode
    """

    quiet: str
    """
    Quiet.

    The arguments used on quiet mode
    """



class Authentication(TypedDict, total=False):
    """
    Authentication.

    The authentication configuration
    """

    github_repository: str
    """
    GitHub repository.

    The GitHub repository name, on witch one we will check the access rights
    """

    github_access_type: "GithubAccess"
    """
    GitHub access.

    The kind of rights the user should have on the repository

    default: pull
    """



AwsRegion = str
"""
AWS region.

The region

pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
default: eu-west-1
"""



CACHE_FOLDER_DEFAULT = ''
""" Default value of the field path 'cache_folder' """



CACHE_WMST_CAPABILITIES_FILE_DEFAULT = '1.0.0/WMTSCapabilities.xml'
""" Default value of the field path 'cache_wmtscapabilities_file' """



CENTER_X_DEFAULT = 2600000
""" Default value of the field path 'OpenLayers center_x' """



CENTER_Y_DEFAULT = 1200000
""" Default value of the field path 'OpenLayers center_y' """



CLOUDFRONT_DOWNLOAD_DEFAULT = 0.12
""" Default value of the field path 'CloudFront cost download' """



CLOUDFRONT_GET_DEFAULT = 0.009
""" Default value of the field path 'CloudFront cost get' """



COST_TILE_SIZE_DEFAULT = 20
""" Default value of the field path 'Layer cost tile_size' """



Cache = Union["CacheFilesystem", "CacheS3", "CacheAzure", "CacheMbtiles", "CacheBsddb"]
"""
Cache.

The tiles cache definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches

Aggregation type: anyOf
"""



CacheAzure = Union[dict[str, str], "CacheAzureTyped"]
"""
Cache Azure.

Azure Blob Storage


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheAzureTyped(TypedDict, total=False):
    type: Literal['azure']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    """
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    """
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    """
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    """ Cache HTTP URLs. """

    folder: "CacheFolder"
    """
    Cache folder.

    The root folder of the cache

    default: 
    """

    container: Required[str]
    """
    Container.

    The Azure container name

    Required property
    """

    cache_control: str
    """
    Cache control.

    The Cache-Control used to store tiles on Azure
    """



CacheBsddb = Union[dict[str, str], "CacheBsddbTyped"]
"""
Cache BSDDB.


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheBsddbTyped(TypedDict, total=False):
    type: Literal['bsddb']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    """
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    """
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    """
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    """ Cache HTTP URLs. """

    folder: "CacheFolder"
    """
    Cache folder.

    The root folder of the cache

    default: 
    """



CacheFilesystem = Union[dict[str, str], "CacheFilesystemTyped"]
"""
Cache filesystem.


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheFilesystemTyped(TypedDict, total=False):
    type: Literal['filesystem']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    """
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    """
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    """
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    """ Cache HTTP URLs. """

    folder: "CacheFolder"
    """
    Cache folder.

    The root folder of the cache

    default: 
    """



CacheFolder = str
"""
Cache folder.

The root folder of the cache

default: 
"""



CacheHost = list[str]
"""
Cache host.

The host used to build the HTTP URLs
"""



CacheHttpUrl = str
"""
Cache HTTP URL.

The HTTP URL %host will be replaces by one of the hosts
"""



CacheHttpUrls = list[str]
""" Cache HTTP URLs. """



CacheMbtiles = Union[dict[str, str], "CacheMbtilesTyped"]
"""
Cache MBtiles.


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheMbtilesTyped(TypedDict, total=False):
    type: Literal['mbtiles']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    """
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    """
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    """
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    """ Cache HTTP URLs. """

    folder: "CacheFolder"
    """
    Cache folder.

    The root folder of the cache

    default: 
    """



CacheS3 = Union[dict[str, str], "CacheS3Typed"]
"""
Cache S3.


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheS3Typed(TypedDict, total=False):
    type: Literal['s3']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    """
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    """
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    """
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    """ Cache HTTP URLs. """

    tiles_url: str
    """
    Tiles URL.

    The template tiles URL on S3, the argument can be region, bucket and folder

    default: http://s3-{region}.amazonaws.com/{bucket}/{folder}
    """

    host: str
    """
    Host.

    The S3 host

    default: s3-eu-west-1.amazonaws.com
    """

    bucket: Required[str]
    """
    Bucket.

    The S3 bucker name

    Required property
    """

    region: "AwsRegion"
    """
    AWS region.

    The region

    pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
    default: eu-west-1
    """

    cache_control: str
    """
    Cache control.

    The Cache-Control used to store tiles on S3
    """

    folder: "CacheFolder"
    """
    Cache folder.

    The root folder of the cache

    default: 
    """



CacheWmstCapabilitiesFile = str
"""
Cache WMST capabilities file.

The generated WMTS capabilities file name

default: 1.0.0/WMTSCapabilities.xml
"""



class CloudfrontCost(TypedDict, total=False):
    """
    CloudFront cost.

    The CloudFront cost (main configuration)
    """

    get: int | float
    """
    CloudFront Get.

    The cost of get in $ per 10 000 requests (main configuration)

    default: 0.009
    """

    download: int | float
    """
    CloudFront Download.

    The cost of download in $ per Gio (main configuration)

    default: 0.12
    """



class Configuration(TypedDict, total=False):
    """ TileCloud-chain configuration. """

    defaults: dict[str, Any]
    """
    Defaults.

    Used to put YAML references
    """

    grids: dict[str, "Grid"]
    """
    Grids.

    The WMTS grid definitions by grid name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids

    propertyNames:
      pattern: ^[a-zA-Z0-9_\-~\.]+$
    """

    caches: dict[str, "Cache"]
    """
    Caches.

    The tiles caches definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches

    propertyNames:
      pattern: ^[a-zA-Z0-9_\-~\.]+$
    """

    layers: dict[str, "Layer"]
    """
    Layers.

    The layers definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers

    propertyNames:
      pattern: ^[a-zA-Z0-9_\-~\.]+$
    """

    process: dict[str, "ProcessCommand"]
    """
    Process.

    List of available commands by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#process
    """

    generation: "Generation"
    """
    Generation.

    The configuration used for the generation
    """

    sqs: "Sqs"
    """
    SQS.

    The Simple Queue Service configuration
    """

    sns: "Sns"
    """
    SNS.

    The Simple Notification Service configuration, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sns
    """

    queue_store: "QueueStore"
    """
    Queue store.

    The used queue store

    default: redis
    """

    redis: "Redis"
    """
    Redis.

    The Redis configuration (main configuration)
    """

    postgresql: "Postgresql"
    """
    PostgreSQL.

    The PostgreSQL configuration (main configuration), the schema can be configured with the `TILECLOUD_CHAIN_POSTGRESQL_SCHEMA` environment variable
    """

    openlayers: "Openlayers"
    """
    OpenLayers.

    Configuration used to generate the OpenLayers example page
    """

    server: "Server"
    """
    Server.

    Configuration used by the tile server, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#distribute-the-tiles
    """

    cost: "Cost"
    """
    Cost.

    The configuration use to calculate the cast (unmaintained)
    """

    metadata: "Metadata"
    """
    Metadata.

    The configuration of the WMTS capabilities metadata
    """

    provider: "Provider"
    """
    Provider.

    The provider
    """

    logging: "Logging"
    """
    Logging.

    The logging configuration to database, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#logging (main configuration)
    """

    authentication: "Authentication"
    """
    Authentication.

    The authentication configuration
    """



class Contact(TypedDict, total=False):
    """
    Contact.

    The contact
    """

    name: str
    """ Name. """

    position: str
    """ Position. """

    info: "Info"
    """
    Info.

    The information
    """



class Cost(TypedDict, total=False):
    """
    Cost.

    The configuration use to calculate the cast (unmaintained)
    """

    request_per_layers: int
    """
    Request per layers.

    Tile request per hours

    default: 10000000
    """

    s3: "S3Cost"
    """
    S3 cost.

    The S3 cost (main configuration)
    """

    cloudfront: "CloudfrontCost"
    """
    CloudFront cost.

    The CloudFront cost (main configuration)
    """

    sqs: "SqsCost"
    """
    SQS cost.

    The SQS cost, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sqs (main configuration)
    """



DATA_BUFFER_DEFAULT = 128
""" Default value of the field path 'Layer Mapnik data_buffer' """



DEFAULT_CACHE_DEFAULT = 'default'
""" Default value of the field path 'Generation default_cache' """



DROP_EMPTY_UTFGRID_DEFAULT = False
""" Default value of the field path 'Layer Mapnik drop_empty_utfgrid' """



class Database(TypedDict, total=False):
    """
    Database.

    The database (main configuration)
    """

    host: str
    """
    Host.

    The host (main configuration)
    """

    port: int
    """
    Port.

    The port (main configuration)

    default: 5432
    """

    dbname: Required[str]
    """
    Database.

    The database name (main configuration)

    Required property
    """

    table: Required[str]
    """
    Table.

    The table name (main configuration)

    Required property
    """

    user: Required[str]
    """
    User.

    The user name (main configuration)

    Required property
    """

    password: Required[str]
    """
    Password.

    The password (main configuration)

    Required property
    """



EXPIRATION_DEFAULT = 28800
""" Default value of the field path 'Redis expiration' """



EXPIRES_DEFAULT = 8
""" Default value of the field path 'Server expires' """



GENERATE_SALT_DEFAULT = False
""" Default value of the field path 'Layer WMS generate_salt' """



GEOMETRIES_REDIRECT_DEFAULT = False
""" Default value of the field path 'Server geoms_redirect' """



GITHUB_ACCESS_DEFAULT = 'pull'
""" Default value of the field path 'Authentication github_access_type' """



class Generation(TypedDict, total=False):
    """
    Generation.

    The configuration used for the generation
    """

    default_cache: str
    """
    Default cache.

    The default cache name to be used, default do 'default'

    default: default
    """

    default_layers: list[str]
    """
    Default layers.

    The default layers to be generated
    """

    authorised_user: str
    """
    Authorized user.

    The authorized user to generate the tiles (used to avoid permission issue on generated tiles) (main configuration)
    """

    maxconsecutive_errors: int
    """
    Max consecutive errors.

    The maximum number of consecutive errors (main configuration)

    default: 10
    """

    error_file: str
    """
    Error file.

    File name generated with the tiles in error, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#tiles-error-file (main configuration)
    """

    number_process: int
    """
    Number process.

    Number of process used to generate the tiles (main configuration)

    default: 1
    """



GithubAccess = Literal['push'] | Literal['pull'] | Literal['admin']
"""
GitHub access.

The kind of rights the user should have on the repository

default: pull
"""
GITHUBACCESS_PUSH: Literal['push'] = "push"
"""The values for the 'GitHub access' enum"""
GITHUBACCESS_PULL: Literal['pull'] = "pull"
"""The values for the 'GitHub access' enum"""
GITHUBACCESS_ADMIN: Literal['admin'] = "admin"
"""The values for the 'GitHub access' enum"""



class Grid(TypedDict, total=False):
    """
    Grid.

    The WMTS grid definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids
    """

    resolution_scale: int
    """
    Resolution scale.

    The scale used to build a FreeTileGrid typically '2'
    """

    resolutions: Required[list[int | float]]
    """
    Resolutions.

    The resolutions in pixel per meter

    Required property
    """

    bbox: Required[list[int | float]]
    """
    Bounding box.

    The bounding box in meter

    minLength: 4
    maxLength: 4

    Required property
    """

    srs: Required[str]
    """
    SRS.

    The projection reference

    pattern: ^EPSG:[0-9]+$

    Required property
    """

    proj4_literal: str
    """
    Proj4 literal.

    The Proj4 definition
    """

    unit: str
    """
    Unit.

    The projection unit

    default: m
    """

    tile_size: int
    """
    Tile size.

    The tile size in pixel

    default: 256
    """

    matrix_identifier: "MatrixIdentifier"
    """
    Matrix identifier.

    The identifier to use in the tiles URL, recommend to be resolution (default)

    default: zoom
    """



HOST_DEFAULT = 's3-eu-west-1.amazonaws.com'
""" Default value of the field path 'Cache S3 host' """



Headers = dict[str, "_HeadersAdditionalproperties"]
"""
Headers.

The headers that we send to the WMS backend
"""



class Info(TypedDict, total=False):
    """
    Info.

    The information
    """

    phone: "Phone"
    """
    Phone.

    The phone
    """

    address: "Address"
    """
    Address.

    The address
    """



LAYER_LEGEND_EXTENSION_DEFAULT = 'png'
""" Default value of the field path 'layer_legend_extension' """



LAYER_LEGEND_MIME_DEFAULT = 'image/png'
""" Default value of the field path 'layer_legend_mime' """



LAYER_META_BUFFER_DEFAULT = 128
""" Default value of the field path 'layer_meta_buffer' """



LAYER_META_DEFAULT = False
""" Default value of the field path 'layer_meta' """



LAYER_META_SIZE_DEFAULT = 5
""" Default value of the field path 'layer_meta_size' """



LAYER_PIXEL_BUFFER_DEFAULT = 0
""" Default value of the field path 'layer_px_buffer' """



Layer = Union["LayerWms", "LayerMapnik"]
"""
Layer.

The layer definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers

Aggregation type: anyOf
"""



LayerBoundingBox = list[int | float]
"""
Layer bounding box.

The bounding box where we will generate the tiles

minLength: 4
maxLength: 4
"""



class LayerCost(TypedDict, total=False):
    """
    Layer cost.

    The rules used to calculate the cost
    """

    tileonly_generation_time: int | float
    """
    tile only generation time.

    The time to generate a tile without meta-tile

    default: 40
    """

    tile_generation_time: int | float
    """
    tile generation time.

    The time to generate a tile from the meta-tile

    default: 30
    """

    metatile_generation_time: int | float
    """
    Meta tile generation time.

    The time to generate a meta-tile

    default: 30
    """

    tile_size: int | float
    """
    Cost tile size.

    The tile mean size in bytes

    default: 20
    """



LayerDimensionName = str
"""
Layer dimension name.

The dimension name

pattern: (?i)^(?!(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\-~\.]+$
"""



LayerDimensions = list["_LayerDimensionsItem"]
"""
layer dimensions.

The WMTS dimensions
"""



class LayerEmptyMetaTileDetection(TypedDict, total=False):
    """
    Layer empty meta-tile detection.

    The rules used to detect the empty meta-tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    size: Required[int]
    """
    Size.

    The meta-tile size

    Required property
    """

    hash: Required[str]
    """
    Hash.

    The meta-tile hash

    Required property
    """



class LayerEmptyTileDetection(TypedDict, total=False):
    """
    Layer empty tile detection.

    The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    size: Required[int]
    """
    Title.

    The tile size

    Required property
    """

    hash: Required[str]
    """
    Hash.

    The tile hash

    Required property
    """



LayerExtension = str
"""
Layer extension.

The layer extension
"""



LayerGeometries = list["_LayerGeometriesItem"]
"""
Layer geometries.

The geometries used to determine where we should create the tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-geomsql
"""



LayerGrid = str
"""
Layer grid.

The grid name, deprecated, use `grids` instead
"""



LayerGrids = list[str]
"""
Layer grids.

All the used grids name used in the capabilities, by default only the `grid` is used, if `grid` is not defined, all the grids are used
"""



LayerLayers = str
"""
Layer layers.

The WMS layers
"""



LayerLegendExtension = str
"""
Layer legend extension.

The extension used to store the generated legend

default: png
pattern: ^[a-zA-Z0-9]+$
"""



LayerLegendMime = str
"""
Layer legend MIME.

The mime type used to store the generated legend

default: image/png
pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
"""



LayerLegends = list["_LayerLegendsItem"]
"""
Layer legends.

The provided legend
"""



class LayerMapnik(TypedDict, total=False):
    """ Layer Mapnik. """

    type: Literal['mapnik']
    title: "LayerTitle"
    """
    Layer title.

    The title, use to generate the capabilities
    """

    grid: "LayerGrid"
    """
    Layer grid.

    The grid name, deprecated, use `grids` instead
    """

    grids: "LayerGrids"
    """
    Layer grids.

    All the used grids name used in the capabilities, by default only the `grid` is used, if `grid` is not defined, all the grids are used
    """

    srs: "LayerSrs"
    """
    Layer SRS.

    The projection reference, used for the bbox, the geoms, and the --bbox argument.

    pattern: ^EPSG:[0-9]+$
    """

    proj4_literal: "LayerProj4Literal"
    """
    Layer Proj4 literal.

    The Proj4 definition, used for the bbox, the geoms, and the --bbox argument.
    """

    bbox: "LayerBoundingBox"
    """
    Layer bounding box.

    The bounding box where we will generate the tiles

    minLength: 4
    maxLength: 4
    """

    min_resolution_seed: "LayerMinResolutionSeed"
    """
    layer min resolution seed.

    The minimum resolutions to pre-generate
    """

    px_buffer: "LayerPixelBuffer"
    """
    Layer pixel buffer.

    The buffer in pixel used to calculate geometry intersection

    default: 0
    """

    meta: "LayerMeta"
    """
    Layer meta.

    Use meta-tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles

    default: False
    """

    meta_size: "LayerMetaSize"
    """
    Layer meta size.

    The meta-tile size in tiles

    default: 5
    """

    meta_buffer: "LayerMetaBuffer"
    """
    Layer meta buffer.

    The meta-tiles buffer in pixels

    default: 128
    """

    layers: "LayerLayers"
    """
    Layer layers.

    The WMS layers
    """

    wmts_style: Required["LayerWmtsStyle"]
    """
    Layer WMTS style.

    The WMTS style

    pattern: ^[a-zA-Z0-9_\-\+~\.]+$

    Required property
    """

    mime_type: Required["LayerMimeType"]
    """
    Layer MIME type.

    The MIME type of the tiles

    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$

    Required property
    """

    extension: Required["LayerExtension"]
    """
    Layer extension.

    The layer extension

    Required property
    """

    dimensions: "LayerDimensions"
    """
    layer dimensions.

    The WMTS dimensions
    """

    legends: "LayerLegends"
    """
    Layer legends.

    The provided legend
    """

    legend_mime: "LayerLegendMime"
    """
    Layer legend MIME.

    The mime type used to store the generated legend

    default: image/png
    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
    """

    legend_extension: "LayerLegendExtension"
    """
    Layer legend extension.

    The extension used to store the generated legend

    default: png
    pattern: ^[a-zA-Z0-9]+$
    """

    pre_hash_post_process: "LayerPreHashPostProcess"
    """
    Layer pre hash post process.

    Do an image post process before the empty hash check
    """

    post_process: "LayerPostProcess"
    """
    Layer post process.

    Do an image post process after the empty hash check
    """

    geoms: "LayerGeometries"
    """
    Layer geometries.

    The geometries used to determine where we should create the tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-geomsql
    """

    empty_tile_detection: "LayerEmptyTileDetection"
    """
    Layer empty tile detection.

    The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    empty_metatile_detection: "LayerEmptyMetaTileDetection"
    """
    Layer empty meta-tile detection.

    The rules used to detect the empty meta-tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    cost: "LayerCost"
    """
    Layer cost.

    The rules used to calculate the cost
    """

    mapfile: str
    """
    MapFile.

    The Mapnik map file
    """

    data_buffer: int
    """
    Data buffer.

    The data buffer

    default: 128
    """

    output_format: "OutputFormat"
    """
    Output format.

    The Mapnik output format

    default: png
    """

    wms_url: str
    """
    WMS URL.

    A WMS fallback URL (deprecated)
    """

    resolution: int
    """
    Resolution.

    The resolution

    default: 4
    """

    layers_fields: dict[str, "_LayersFieldsAdditionalproperties"]
    """
    Layers fields.

    The Mapnik layers fields
    """

    drop_empty_utfgrid: bool
    """
    Drop empty UTFGrid.

    Drop if the tile is empty

    default: False
    """



LayerMeta = bool
"""
Layer meta.

Use meta-tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles

default: False
"""



LayerMetaBuffer = int
"""
Layer meta buffer.

The meta-tiles buffer in pixels

default: 128
"""



LayerMetaSize = int
"""
Layer meta size.

The meta-tile size in tiles

default: 5
"""



LayerMimeType = str
"""
Layer MIME type.

The MIME type of the tiles

pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
"""



LayerMinResolutionSeed = int | float
"""
layer min resolution seed.

The minimum resolutions to pre-generate
"""



LayerPixelBuffer = int
"""
Layer pixel buffer.

The buffer in pixel used to calculate geometry intersection

default: 0
"""



LayerPostProcess = str
"""
Layer post process.

Do an image post process after the empty hash check
"""



LayerPreHashPostProcess = str
"""
Layer pre hash post process.

Do an image post process before the empty hash check
"""



LayerProj4Literal = str
"""
Layer Proj4 literal.

The Proj4 definition, used for the bbox, the geoms, and the --bbox argument.
"""



LayerSrs = str
"""
Layer SRS.

The projection reference, used for the bbox, the geoms, and the --bbox argument.

pattern: ^EPSG:[0-9]+$
"""



LayerTitle = str
"""
Layer title.

The title, use to generate the capabilities
"""



class LayerWms(TypedDict, total=False):
    """ Layer WMS. """

    type: Literal['wms']
    title: "LayerTitle"
    """
    Layer title.

    The title, use to generate the capabilities
    """

    grid: "LayerGrid"
    """
    Layer grid.

    The grid name, deprecated, use `grids` instead
    """

    grids: "LayerGrids"
    """
    Layer grids.

    All the used grids name used in the capabilities, by default only the `grid` is used, if `grid` is not defined, all the grids are used
    """

    srs: "LayerSrs"
    """
    Layer SRS.

    The projection reference, used for the bbox, the geoms, and the --bbox argument.

    pattern: ^EPSG:[0-9]+$
    """

    proj4_literal: "LayerProj4Literal"
    """
    Layer Proj4 literal.

    The Proj4 definition, used for the bbox, the geoms, and the --bbox argument.
    """

    bbox: "LayerBoundingBox"
    """
    Layer bounding box.

    The bounding box where we will generate the tiles

    minLength: 4
    maxLength: 4
    """

    min_resolution_seed: "LayerMinResolutionSeed"
    """
    layer min resolution seed.

    The minimum resolutions to pre-generate
    """

    px_buffer: "LayerPixelBuffer"
    """
    Layer pixel buffer.

    The buffer in pixel used to calculate geometry intersection

    default: 0
    """

    meta: "LayerMeta"
    """
    Layer meta.

    Use meta-tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles

    default: False
    """

    meta_size: "LayerMetaSize"
    """
    Layer meta size.

    The meta-tile size in tiles

    default: 5
    """

    meta_buffer: "LayerMetaBuffer"
    """
    Layer meta buffer.

    The meta-tiles buffer in pixels

    default: 128
    """

    layers: Required["LayerLayers"]
    """
    Layer layers.

    The WMS layers

    Required property
    """

    wmts_style: Required["LayerWmtsStyle"]
    """
    Layer WMTS style.

    The WMTS style

    pattern: ^[a-zA-Z0-9_\-\+~\.]+$

    Required property
    """

    mime_type: Required["LayerMimeType"]
    """
    Layer MIME type.

    The MIME type of the tiles

    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$

    Required property
    """

    extension: Required["LayerExtension"]
    """
    Layer extension.

    The layer extension

    Required property
    """

    dimensions: "LayerDimensions"
    """
    layer dimensions.

    The WMTS dimensions
    """

    legends: "LayerLegends"
    """
    Layer legends.

    The provided legend
    """

    legend_mime: "LayerLegendMime"
    """
    Layer legend MIME.

    The mime type used to store the generated legend

    default: image/png
    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
    """

    legend_extension: "LayerLegendExtension"
    """
    Layer legend extension.

    The extension used to store the generated legend

    default: png
    pattern: ^[a-zA-Z0-9]+$
    """

    pre_hash_post_process: "LayerPreHashPostProcess"
    """
    Layer pre hash post process.

    Do an image post process before the empty hash check
    """

    post_process: "LayerPostProcess"
    """
    Layer post process.

    Do an image post process after the empty hash check
    """

    geoms: "LayerGeometries"
    """
    Layer geometries.

    The geometries used to determine where we should create the tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-geomsql
    """

    empty_tile_detection: "LayerEmptyTileDetection"
    """
    Layer empty tile detection.

    The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    empty_metatile_detection: "LayerEmptyMetaTileDetection"
    """
    Layer empty meta-tile detection.

    The rules used to detect the empty meta-tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    cost: "LayerCost"
    """
    Layer cost.

    The rules used to calculate the cost
    """

    url: Required[str]
    """
    URL.

    The WMS service URL

    Required property
    """

    generate_salt: bool
    """
    Generate salt.

    Should generate a salt to drop the cache

    default: False
    """

    query_layers: str
    """
    Query layers.

    The layers use for query (To be used with the server)
    """

    info_formats: list[str]
    """
    Info formats.

    The query info format
    """

    params: dict[str, "_ParametersAdditionalproperties"]
    """
    Parameters.

    Additional parameters to the WMS query (like dimension)
    """

    headers: "Headers"
    """
    Headers.

    The headers that we send to the WMS backend
    """

    version: str
    """
    Version.

    The used WMS version

    default: 1.1.1
    """



LayerWmtsStyle = str
"""
Layer WMTS style.

The WMTS style

pattern: ^[a-zA-Z0-9_\-\+~\.]+$
"""



class Logging(TypedDict, total=False):
    """
    Logging.

    The logging configuration to database, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#logging (main configuration)
    """

    database: Required["Database"]
    """
    Database.

    The database (main configuration)

    Required property
    """



MAP_INITIAL_ZOOM_DEFAULT = 3
""" Default value of the field path 'OpenLayers zoom' """



MATRIX_IDENTIFIER_DEFAULT = 'zoom'
""" Default value of the field path 'Grid matrix_identifier' """



MAX_CONSECUTIVE_ERRORS_DEFAULT = 10
""" Default value of the field path 'Generation maxconsecutive_errors' """



MAX_ERRORS_AGE_DEFAULT = 86400
""" Default value of the field path 'Redis max_errors_age' """



MAX_ERRORS_NUMBER_DEFAULT = 100
""" Default value of the field path 'Redis max_errors_nb' """



MAX_PENDING_MINUTES_DEFAULT = 10
""" Default value of the field path 'PostgreSQL max_pending_minutes' """



MAX_RETRIES_DEFAULT = 5
""" Default value of the field path 'Redis max_retries' """



META_TILE_GENERATION_TIME_DEFAULT = 30
""" Default value of the field path 'Layer cost metatile_generation_time' """



MatrixIdentifier = Literal['zoom'] | Literal['resolution']
"""
Matrix identifier.

The identifier to use in the tiles URL, recommend to be resolution (default)

default: zoom
"""
MATRIXIDENTIFIER_ZOOM: Literal['zoom'] = "zoom"
"""The values for the 'Matrix identifier' enum"""
MATRIXIDENTIFIER_RESOLUTION: Literal['resolution'] = "resolution"
"""The values for the 'Matrix identifier' enum"""



class Metadata(TypedDict, total=False):
    """
    Metadata.

    The configuration of the WMTS capabilities metadata
    """

    title: Required[str]
    """
    Title.

    The title

    Required property
    """

    abstract: str
    """
    Abstract.

    The abstract
    """

    servicetype: str
    """
    Service type.

    The service type

    default: OGC WMTS
    """

    keywords: list[str]
    """
    Keywords.

    The keywords
    """

    fees: str
    """
    Fees.

    The fees
    """

    access_constraints: str
    """
    Access constraints.

    The access constraints
    """



NEED_OUT_DEFAULT = False
""" Default value of the field path 'Process command item need_out' """



NUMBER_PROCESS_DEFAULT = 1
""" Default value of the field path 'Generation number_process' """



OUTPUT_FORMAT_DEFAULT = 'png'
""" Default value of the field path 'Layer Mapnik output_format' """



class Openlayers(TypedDict, total=False):
    """
    OpenLayers.

    Configuration used to generate the OpenLayers example page
    """

    srs: str
    """
    SRS.

    The projection code

    pattern: ^EPSG:[0-9]+$
    default: EPSG:2056
    """

    proj4js_def: str
    """
    Proj4js definition.

    The `proj4js` definition, by default it will be build with pyproj
    """

    center_x: int | float
    """
    Center x.

    The center easting

    default: 2600000
    """

    center_y: int | float
    """
    Center y.

    The center northing

    default: 1200000
    """

    zoom: int | float
    """
    Map initial zoom.

    The initial zoom

    default: 3
    """



OutputFormat = Literal['png'] | Literal['png256'] | Literal['jpeg'] | Literal['grid']
"""
Output format.

The Mapnik output format

default: png
"""
OUTPUTFORMAT_PNG: Literal['png'] = "png"
"""The values for the 'Output format' enum"""
OUTPUTFORMAT_PNG256: Literal['png256'] = "png256"
"""The values for the 'Output format' enum"""
OUTPUTFORMAT_JPEG: Literal['jpeg'] = "jpeg"
"""The values for the 'Output format' enum"""
OUTPUTFORMAT_GRID: Literal['grid'] = "grid"
"""The values for the 'Output format' enum"""



PENDING_COUNT_DEFAULT = 10
""" Default value of the field path 'Redis pending_count' """



PENDING_MAX_COUNT_DEFAULT = 10000
""" Default value of the field path 'Redis pending_max_count' """



PENDING_TIMEOUT_DEFAULT = 300
""" Default value of the field path 'Redis pending_timeout' """



PORT_DEFAULT = 5432
""" Default value of the field path 'Database port' """



PREFIX_DEFAULT = 'tilecloud_cache'
""" Default value of the field path 'Redis prefix' """



class Phone(TypedDict, total=False):
    """
    Phone.

    The phone
    """

    voice: str
    """
    Voice.

    The voice number
    """

    fax: str
    """
    Fax.

    The fax number
    """



class Postgresql(TypedDict, total=False):
    """
    PostgreSQL.

    The PostgreSQL configuration (main configuration), the schema can be configured with the `TILECLOUD_CHAIN_POSTGRESQL_SCHEMA` environment variable
    """

    sqlalchemy_url: str
    """
    SQLAlchemy URL.

    The SQLAlchemy URL (like: `postgresql+psycopg2://username:password@host:5432/database`) (main configuration), can also be set in the `TILECLOUD_CHAIN_SQLALCHEMY_URL` environment variable
    """

    max_pending_minutes: int
    """
    Max pending minutes.

    The max pending minutes (main configuration)

    default: 10
    """



ProcessCommand = list["_ProcessCommandItem"]
"""
Process command.

A command
"""



class Provider(TypedDict, total=False):
    """
    Provider.

    The provider
    """

    name: str
    """ Name. """

    url: str
    """
    URL.

    The public URL
    """

    contact: "Contact"
    """
    Contact.

    The contact
    """



QUEUE_STORE_DEFAULT = 'redis'
""" Default value of the field path 'TileCloud-chain configuration queue_store' """



QueueStore = Literal['redis'] | Literal['sqs'] | Literal['postgresql']
"""
Queue store.

The used queue store

default: redis
"""
QUEUESTORE_REDIS: Literal['redis'] = "redis"
"""The values for the 'Queue store' enum"""
QUEUESTORE_SQS: Literal['sqs'] = "sqs"
"""The values for the 'Queue store' enum"""
QUEUESTORE_POSTGRESQL: Literal['postgresql'] = "postgresql"
"""The values for the 'Queue store' enum"""



REDIS_QUEUE_DEFAULT = 'tilecloud'
""" Default value of the field path 'Redis queue' """



REQUEST_DEFAULT = 0.01
""" Default value of the field path 'SQS cost request' """



REQUEST_PER_LAYERS_DEFAULT = 10000000
""" Default value of the field path 'Cost request_per_layers' """



RESOLUTION_DEFAULT = 4
""" Default value of the field path 'Layer Mapnik resolution' """



class Redis(TypedDict, total=False):
    """
    Redis.

    The Redis configuration (main configuration)
    """

    url: str
    """
    URL.

    The server URL (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_URL` environment variable

    pattern: ^rediss?://([^:@/]*:[^:@/]*@)?[^:@/]+(:[0-9]+)?(/.*)?$
    """

    sentinels: list["_SentinelsItem"]
    """
    Sentinels.

    The sentinels (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_SENTINELS` environment variable
    """

    connection_kwargs: dict[str, Any]
    """ The Redis connection arguments (main configuration) """

    sentinel_kwargs: dict[str, Any]
    """ The Redis sentinel arguments (main configuration) """

    service_name: str
    """
    Service name.

    The service name (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_SERVICE_NAME` environment variable

    default: mymaster
    """

    socket_timeout: int
    """
    Socket timeout.

    The socket timeout (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_SOCKET_TIMEOUT` environment variable
    """

    db: int
    """
    Database.

    The database number (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_DB` environment variable
    """

    queue: str
    """
    Redis queue.

    The queue name (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_QUEUE` environment variable

    default: tilecloud
    """

    timeout: int
    """
    Timeout.

    The timeout (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_TIMEOUT` environment variable

    default: 5
    """

    pending_timeout: int
    """
    Pending timeout.

    The pending timeout (main configuration)

    default: 300
    """

    max_retries: int
    """
    Max retries.

    The max retries (main configuration)

    default: 5
    """

    max_errors_age: int
    """
    Max errors age.

    The max error age (main configuration), default is 1 day

    default: 86400
    """

    max_errors_nb: int
    """
    Max errors number.

    The max error number (main configuration)

    default: 100
    """

    prefix: str
    """
    Prefix.

    The prefix (main configuration)

    default: tilecloud_cache
    """

    expiration: int
    """
    Expiration.

    The meta-tile in queue expiration (main configuration), default is 8 hours

    default: 28800
    """

    pending_count: int
    """
    Pending count.

    The pending count: the number of pending tiles get in one request (main configuration)

    default: 10
    """

    pending_max_count: int
    """
    Pending max count.

    The pending max count: the maximum number of pending tiles get in one pass (if not generating other tiles, every second) (main configuration)

    default: 10000
    """



class S3Cost(TypedDict, total=False):
    """
    S3 cost.

    The S3 cost (main configuration)
    """

    storage: int | float
    """
    S3 Storage.

    The storage cost in $ / Gio / month (main configuration)

    default: 0.125
    """

    put: int | float
    """
    S3 Put.

    The cost of put in $ per 10 000 requests (main configuration)

    default: 0.01
    """

    get: int | float
    """
    S3 Get.

    The cost of get in $ per 10 000 requests (main configuration)

    default: 0.01
    """

    download: int | float
    """
    S3 Download.

    The cost of download in $ per Gio (main configuration)

    default: 0.12
    """



S3_DOWNLOAD_DEFAULT = 0.12
""" Default value of the field path 'S3 cost download' """



S3_GET_DEFAULT = 0.01
""" Default value of the field path 'S3 cost get' """



S3_PUT_DEFAULT = 0.01
""" Default value of the field path 'S3 cost put' """



S3_STORAGE_DEFAULT = 0.125
""" Default value of the field path 'S3 cost storage' """



SERVICE_NAME_DEFAULT = 'mymaster'
""" Default value of the field path 'Redis service_name' """



SERVICE_TYPE_DEFAULT = 'OGC WMTS'
""" Default value of the field path 'Metadata servicetype' """



SQS_QUEUE_DEFAULT = 'tilecloud'
""" Default value of the field path 'SQS queue' """



SRS_DEFAULT = 'EPSG:2056'
""" Default value of the field path 'OpenLayers srs' """



STATIC_ALLOW_EXTENSION_DEFAULT = ['jpeg', 'png', 'xml', 'js', 'html', 'css']
""" Default value of the field path 'Server static_allow_extension' """



STATIC_PATH_DEFAULT = 'static'
""" Default value of the field path 'Server static_path' """



SentinelHost = str
"""
Sentinel host.

The sentinel host name (main configuration)
"""



SentinelPort = str | int
"""
Sentinel port.

The sentinel port (main configuration)

Aggregation type: anyOf
"""



class Server(TypedDict, total=False):
    """
    Server.

    Configuration used by the tile server, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#distribute-the-tiles
    """

    cache: str
    """
    Cache.

    The used cache name
    """

    layers: list[str]
    """
    WMS Layers.

    Layers available in the server, default is all layers
    """

    geoms_redirect: bool
    """
    Geometries redirect.

    Take care on the geometries

    default: False
    """

    static_allow_extension: list[str]
    """
    Static allow extension.

    The allowed extension of static files

    default:
      - jpeg
      - png
      - xml
      - js
      - html
      - css
    """

    wmts_path: str
    """
    WMTS path.

    The sub-path for the WMTS (main configuration)

    default: wmts
    """

    static_path: str
    """
    Static path.

    The sub-path for the static files (main configuration)

    default: static
    """

    admin_path: str
    """
    Admin path.

    The sub-path for the admin (main configuration)

    default: admin
    """

    expires: int
    """
    Expires.

    The browser cache expiration in hours

    default: 8
    """

    predefined_commands: list["_PredefinedCommandsItem"]
    """
    Predefined commands.

    The predefined commands used to generate the tiles
    """

    allowed_commands: list[str]
    """
    Allowed commands.

    The allowed commands (main configuration)

    default:
      - generate-tiles
      - generate-controller
      - generate-cost
    """

    allowed_arguments: list[str]
    """
    Allowed arguments.

    The allowed arguments (main configuration)

    default:
      - --layer
      - --get-hash
      - --generate-legend-images
      - --get-bbox
      - --ignore-error
      - --bbox
      - --zoom
      - --test
      - --near
      - --time
      - --measure-generation-time
      - --no-geom
      - --dimensions
    """

    admin_footer: str
    """
    admin footer.

    The footer of the admin interface
    """

    admin_footer_classes: str
    """
    admin footer classes.

    The CSS classes used on the footer of the admin interface
    """



class Sns(TypedDict, total=False):
    """
    SNS.

    The Simple Notification Service configuration, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sns
    """

    topic: Required[str]
    """
    Topic.

    The topic

    Required property
    """

    region: "AwsRegion"
    """
    AWS region.

    The region

    pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
    default: eu-west-1
    """



class Sqs(TypedDict, total=False):
    """
    SQS.

    The Simple Queue Service configuration
    """

    queue: str
    """
    SQS queue.

    The queue name

    default: tilecloud
    """

    region: "AwsRegion"
    """
    AWS region.

    The region

    pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
    default: eu-west-1
    """



class SqsCost(TypedDict, total=False):
    """
    SQS cost.

    The SQS cost, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sqs (main configuration)
    """

    request: int | float
    """
    Request.

    The cost of request in $ per 1 000 000 requests (main configuration)

    default: 0.01
    """



TILES_URL_DEFAULT = 'http://s3-{region}.amazonaws.com/{bucket}/{folder}'
""" Default value of the field path 'Cache S3 tiles_url' """



TILE_GENERATION_TIME_DEFAULT = 30
""" Default value of the field path 'Layer cost tile_generation_time' """



TILE_ONLY_GENERATION_TIME_DEFAULT = 40
""" Default value of the field path 'Layer cost tileonly_generation_time' """



TILE_SIZE_DEFAULT = 256
""" Default value of the field path 'Grid tile_size' """



TIMEOUT_DEFAULT = 5
""" Default value of the field path 'Redis timeout' """



UNIT_DEFAULT = 'm'
""" Default value of the field path 'Grid unit' """



VERSION_DEFAULT = '1.1.1'
""" Default value of the field path 'Layer WMS version' """



WMTS_PATH_DEFAULT = 'wmts'
""" Default value of the field path 'Server wmts_path' """



_GenerateItem = str
""" pattern: ^[a-zA-Z0-9_\-\+~\.]+$ """



_HeadersAdditionalproperties = str
""" The header value """



_LAYER_MAPNIK_LAYERS_DEFAULT = '__all__'
""" Default value of the field path 'Layer Mapnik layers' """



_LAYER_MAPNIK_META_BUFFER_DEFAULT = 0
""" Default value of the field path 'Layer Mapnik meta_buffer' """



_LAYER_MAPNIK_META_SIZE_DEFAULT = 1
""" Default value of the field path 'Layer Mapnik meta_size' """



_LAYER_WMS_META_BUFFER_DEFAULT = 128
""" Default value of the field path 'Layer WMS meta_buffer' """



_LAYER_WMS_META_SIZE_DEFAULT = 5
""" Default value of the field path 'Layer WMS meta_size' """



class _LayerDimensionsItem(TypedDict, total=False):
    name: Required["LayerDimensionName"]
    """
    Layer dimension name.

    The dimension name

    pattern: (?i)^(?!(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\-~\.]+$

    Required property
    """

    generate: Required[list["_GenerateItem"]]
    """
    Generate.

    The values that should be generate

    Required property
    """

    values: Required[list["_ValuesItem"]]
    """
    Values.

    The values present in the capabilities

    Required property
    """

    default: Required[str]
    """
    Default.

    The default value present in the capabilities

    pattern: ^[a-zA-Z0-9_\-\+~\.]+$

    Required property
    """



class _LayerGeometriesItem(TypedDict, total=False):
    connection: Required[str]
    """
    Connection.

    The PostgreSQL connection string

    Required property
    """

    sql: Required[str]
    """
    SQL.

    The SQL query that get the geometry in geom e.g. `the_geom AS geom FROM my_table`

    Required property
    """

    min_resolution: int | float
    """
    Min resolution.

    The min resolution where the query is valid
    """

    max_resolution: int | float
    """
    Max resolution.

    The max resolution where the query is valid
    """



class _LayerLegendsItem(TypedDict, total=False):
    mime_type: Required[str]
    """
    MIME type.

    The mime type used in the WMS request

    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$

    Required property
    """

    href: Required[str]
    """
    Href.

    The URL of the legend image

    Required property
    """

    width: str
    """
    Width.

    The width of the legend image
    """

    height: str
    """
    Height.

    The height of the legend image
    """

    min_scale: str
    """
    Min scale.

    The max scale of the legend image
    """

    max_scale: str
    """
    Max scale.

    The max scale of the legend image
    """

    min_resolution: str
    """
    Min resolution.

    The max resolution of the legend image
    """

    max_resolution: str
    """
    Max resolution.

    The max resolution of the legend image
    """



_LayersFieldsAdditionalproperties = list[str]
""" The Mapnik layer fields """



_ParametersAdditionalproperties = str
""" The parameter value """



class _PredefinedCommandsItem(TypedDict, total=False):
    command: str
    """
    Command.

    The command to run
    """

    name: str
    """
    Name.

    The name used in the admin interface
    """



class _ProcessCommandItem(TypedDict, total=False):
    cmd: Required[str]
    """
    Command.

    The shell command, available parameters: `%(in)s`, `%(out)s`,` %(args)s`, `%(x)s`, `%(y)s`, `%(z)s`.

    Required property
    """

    need_out: bool
    """
    Need out.

    The command will generate an output in a file

    default: False
    """

    arg: "Argument"
    """
    Argument.

    Used to build the `%(args)`
    """



_SentinelsItem = tuple["SentinelHost", "SentinelPort"]
""" A sentinel (main configuration) """



_ValuesItem = str
""" pattern: ^[a-zA-Z0-9_\-\+~\.]+$ """

