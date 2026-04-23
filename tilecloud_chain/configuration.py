"""
Automatically generated file from a JSON schema.
"""


from typing import Any, Literal, Required, TypedDict, Union


ALLOWED_ARGUMENTS_DEFAULT = ['--layer', '--get-hash', '--generate-legend-images', '--get-bbox', '--ignore-error', '--bbox', '--zoom', '--grid', '--test', '--near', '--time', '--measure-generation-time', '--no-geom', '--dimensions']
r""" Default value of the field path 'Server allowed_arguments' """



ALLOWED_COMMANDS_DEFAULT = ['generate-tiles', 'generate-controller', 'generate-cost']
r""" Default value of the field path 'Server allowed_commands' """



AWS_REGION_DEFAULT = 'eu-west-1'
r""" Default value of the field path 'aws_region' """



class Address(TypedDict, total=False):
    r"""
    Address.

    The address
    """

    delivery: str
    r"""
    Delivery.

    The delivery
    """

    city: str
    r"""
    City.

    The city
    """

    area: str
    r"""
    Area.

    The area
    """

    postal_code: int
    r"""
    Postal code.

    The postal code
    """

    country: str
    r"""
    Country.

    The country
    """

    email: str
    r"""
    Email.

    The email
    """



class Argument(TypedDict, total=False):
    r"""
    Argument.

    Used to build the `%(args)`
    """

    default: str
    r"""
    Properties.

    The arguments used by default
    """

    verbose: str
    r"""
    Verbose.

    The arguments used on verbose mode
    """

    debug: str
    r"""
    Debug.

    The arguments used on debug mode
    """

    quiet: str
    r"""
    Quiet.

    The arguments used on quiet mode
    """



class Authentication(TypedDict, total=False):
    r"""
    Authentication.

    The authentication configuration
    """

    github_repository: str
    r"""
    GitHub repository.

    The GitHub repository name, on witch one we will check the access rights
    """

    github_access_type: "GithubAccess"
    r"""
    GitHub access.

    The kind of rights the user should have on the repository

    default: pull
    """



AwsRegion = str
r"""
AWS region.

The region

pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
default: eu-west-1
"""



CACHE_FOLDER_DEFAULT = ''
r""" Default value of the field path 'cache_folder' """



CACHE_WMST_CAPABILITIES_FILE_DEFAULT = '1.0.0/WMTSCapabilities.xml'
r""" Default value of the field path 'cache_wmtscapabilities_file' """



CENTER_X_DEFAULT = 2600000
r""" Default value of the field path 'OpenLayers center_x' """



CENTER_Y_DEFAULT = 1200000
r""" Default value of the field path 'OpenLayers center_y' """



CLOUDFRONT_DOWNLOAD_DEFAULT = 0.12
r""" Default value of the field path 'CloudFront cost download' """



CLOUDFRONT_GET_DEFAULT = 0.009
r""" Default value of the field path 'CloudFront cost get' """



COST_TILE_SIZE_DEFAULT = 20
r""" Default value of the field path 'Layer cost tile_size' """



Cache = Union["CacheFilesystem", "CacheS3", "CacheAzure", "CacheMbtiles", "CacheBsddb"]
r"""
Cache.

The tiles cache definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches

Aggregation type: anyOf
"""



CacheAzure = Union[dict[str, str], "CacheAzureTyped"]
r"""
Cache Azure.

Azure Blob Storage


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheAzureTyped(TypedDict, total=False):
    type: Literal['azure']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    r"""
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    r"""
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    r"""
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    r""" Cache HTTP URLs. """

    folder: "CacheFolder"
    r"""
    Cache folder.

    The root folder of the cache

    default: 
    """

    container: Required[str]
    r"""
    Container.

    The Azure container name

    Required property
    """

    cache_control: str
    r"""
    Cache control.

    The Cache-Control used to store tiles on Azure
    """



CacheBsddb = Union[dict[str, str], "CacheBsddbTyped"]
r"""
Cache BSDDB.


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheBsddbTyped(TypedDict, total=False):
    type: Literal['bsddb']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    r"""
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    r"""
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    r"""
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    r""" Cache HTTP URLs. """

    folder: "CacheFolder"
    r"""
    Cache folder.

    The root folder of the cache

    default: 
    """



CacheFilesystem = Union[dict[str, str], "CacheFilesystemTyped"]
r"""
Cache filesystem.


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheFilesystemTyped(TypedDict, total=False):
    type: Literal['filesystem']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    r"""
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    r"""
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    r"""
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    r""" Cache HTTP URLs. """

    folder: "CacheFolder"
    r"""
    Cache folder.

    The root folder of the cache

    default: 
    """



CacheFolder = str
r"""
Cache folder.

The root folder of the cache

default: 
"""



CacheHost = list[str]
r"""
Cache host.

The host used to build the HTTP URLs
"""



CacheHttpUrl = str
r"""
Cache HTTP URL.

The HTTP URL %host will be replaces by one of the hosts
"""



CacheHttpUrls = list[str]
r""" Cache HTTP URLs. """



CacheMbtiles = Union[dict[str, str], "CacheMbtilesTyped"]
r"""
Cache MBtiles.


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheMbtilesTyped(TypedDict, total=False):
    type: Literal['mbtiles']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    r"""
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    r"""
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    r"""
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    r""" Cache HTTP URLs. """

    folder: "CacheFolder"
    r"""
    Cache folder.

    The root folder of the cache

    default: 
    """



CacheS3 = Union[dict[str, str], "CacheS3Typed"]
r"""
Cache S3.


WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""



class CacheS3Typed(TypedDict, total=False):
    type: Literal['s3']
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    r"""
    Cache WMST capabilities file.

    The generated WMTS capabilities file name

    default: 1.0.0/WMTSCapabilities.xml
    """

    http_url: "CacheHttpUrl"
    r"""
    Cache HTTP URL.

    The HTTP URL %host will be replaces by one of the hosts
    """

    hosts: "CacheHost"
    r"""
    Cache host.

    The host used to build the HTTP URLs
    """

    http_urls: "CacheHttpUrls"
    r""" Cache HTTP URLs. """

    tiles_url: str
    r"""
    Tiles URL.

    The template tiles URL on S3, the argument can be region, bucket and folder

    default: http://s3-{region}.amazonaws.com/{bucket}/{folder}
    """

    host: str
    r"""
    Host.

    The S3 host

    default: s3-eu-west-1.amazonaws.com
    """

    bucket: Required[str]
    r"""
    Bucket.

    The S3 bucker name

    Required property
    """

    region: "AwsRegion"
    r"""
    AWS region.

    The region

    pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
    default: eu-west-1
    """

    cache_control: str
    r"""
    Cache control.

    The Cache-Control used to store tiles on S3
    """

    folder: "CacheFolder"
    r"""
    Cache folder.

    The root folder of the cache

    default: 
    """



CacheWmstCapabilitiesFile = str
r"""
Cache WMST capabilities file.

The generated WMTS capabilities file name

default: 1.0.0/WMTSCapabilities.xml
"""



class CloudfrontCost(TypedDict, total=False):
    r"""
    CloudFront cost.

    The CloudFront cost (main configuration)
    """

    get: int | float
    r"""
    CloudFront Get.

    The cost of get in $ per 10 000 requests (main configuration)

    default: 0.009
    """

    download: int | float
    r"""
    CloudFront Download.

    The cost of download in $ per Gio (main configuration)

    default: 0.12
    """



class Configuration(TypedDict, total=False):
    r""" TileCloud-chain configuration. """

    defaults: dict[str, Any]
    r"""
    Defaults.

    Used to put YAML references
    """

    grids: dict[str, "Grid"]
    r"""
    Grids.

    The WMTS grid definitions by grid name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids

    propertyNames:
      pattern: ^[a-zA-Z0-9_\-~\.]+$
    """

    caches: dict[str, "Cache"]
    r"""
    Caches.

    The tiles caches definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches

    propertyNames:
      pattern: ^[a-zA-Z0-9_\-~\.]+$
    """

    layers: dict[str, "Layer"]
    r"""
    Layers.

    The layers definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers

    propertyNames:
      pattern: ^[a-zA-Z0-9_\-~\.]+$
    """

    process: dict[str, "ProcessCommand"]
    r"""
    Process.

    List of available commands by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#process
    """

    generation: "Generation"
    r"""
    Generation.

    The configuration used for the generation
    """

    sqs: "Sqs"
    r"""
    SQS.

    The Simple Queue Service configuration
    """

    sns: "Sns"
    r"""
    SNS.

    The Simple Notification Service configuration, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sns
    """

    queue_store: "QueueStore"
    r"""
    Queue store.

    The used queue store

    default: redis
    """

    redis: "Redis"
    r"""
    Redis.

    The Redis configuration (main configuration)
    """

    postgresql: "Postgresql"
    r"""
    PostgreSQL.

    The PostgreSQL configuration (main configuration), the schema can be configured with the `TILECLOUD_CHAIN_POSTGRESQL_SCHEMA` environment variable
    """

    openlayers: "Openlayers"
    r"""
    OpenLayers.

    Configuration used to generate the OpenLayers example page
    """

    server: "Server"
    r"""
    Server.

    Configuration used by the tile server, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#distribute-the-tiles
    """

    cost: "Cost"
    r"""
    Cost.

    The configuration use to calculate the cast (unmaintained)
    """

    metadata: "Metadata"
    r"""
    Metadata.

    The configuration of the WMTS capabilities metadata
    """

    provider: "Provider"
    r"""
    Provider.

    The provider
    """

    logging: "Logging"
    r"""
    Logging.

    The logging configuration to database, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#logging (main configuration)
    """

    authentication: "Authentication"
    r"""
    Authentication.

    The authentication configuration
    """



class Contact(TypedDict, total=False):
    r"""
    Contact.

    The contact
    """

    name: str
    r""" Name. """

    position: str
    r""" Position. """

    info: "Info"
    r"""
    Info.

    The information
    """



class Cost(TypedDict, total=False):
    r"""
    Cost.

    The configuration use to calculate the cast (unmaintained)
    """

    request_per_layers: int
    r"""
    Request per layers.

    Tile request per hours

    default: 10000000
    """

    s3: "S3Cost"
    r"""
    S3 cost.

    The S3 cost (main configuration)
    """

    cloudfront: "CloudfrontCost"
    r"""
    CloudFront cost.

    The CloudFront cost (main configuration)
    """

    sqs: "SqsCost"
    r"""
    SQS cost.

    The SQS cost, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sqs (main configuration)
    """



DATA_BUFFER_DEFAULT = 128
r""" Default value of the field path 'Layer Mapnik data_buffer' """



DEFAULT_CACHE_DEFAULT = 'default'
r""" Default value of the field path 'Generation default_cache' """



DROP_EMPTY_UTFGRID_DEFAULT = False
r""" Default value of the field path 'Layer Mapnik drop_empty_utfgrid' """



class Database(TypedDict, total=False):
    r"""
    Database.

    The database (main configuration)
    """

    host: str
    r"""
    Host.

    The host (main configuration)
    """

    port: int
    r"""
    Port.

    The port (main configuration)

    default: 5432
    """

    dbname: Required[str]
    r"""
    Database.

    The database name (main configuration)

    Required property
    """

    table: Required[str]
    r"""
    Table.

    The table name (main configuration)

    Required property
    """

    user: Required[str]
    r"""
    User.

    The user name (main configuration)

    Required property
    """

    password: Required[str]
    r"""
    Password.

    The password (main configuration)

    Required property
    """



EXPIRATION_DEFAULT = 28800
r""" Default value of the field path 'Redis expiration' """



EXPIRES_DEFAULT = 8
r""" Default value of the field path 'Server expires' """



GENERATE_SALT_DEFAULT = False
r""" Default value of the field path 'Layer WMS generate_salt' """



GEOMETRIES_REDIRECT_DEFAULT = False
r""" Default value of the field path 'Server geoms_redirect' """



GITHUB_ACCESS_DEFAULT = 'pull'
r""" Default value of the field path 'Authentication github_access_type' """



class Generation(TypedDict, total=False):
    r"""
    Generation.

    The configuration used for the generation
    """

    default_cache: str
    r"""
    Default cache.

    The default cache name to be used, default do 'default'

    default: default
    """

    default_layers: list[str]
    r"""
    Default layers.

    The default layers to be generated
    """

    authorised_user: str
    r"""
    Authorized user.

    The authorized user to generate the tiles (used to avoid permission issue on generated tiles) (main configuration)
    """

    maxconsecutive_errors: int
    r"""
    Max consecutive errors.

    The maximum number of consecutive errors (main configuration)

    default: 10
    """

    error_file: str
    r"""
    Error file.

    File name generated with the tiles in error, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#tiles-error-file (main configuration)
    """

    number_process: int
    r"""
    Number process.

    Number of process used to generate the tiles (main configuration)

    default: 1
    """



GithubAccess = Literal['push'] | Literal['pull'] | Literal['admin']
r"""
GitHub access.

The kind of rights the user should have on the repository

default: pull
"""
GITHUBACCESS_PUSH: Literal['push'] = "push"
r"""The values for the 'GitHub access' enum"""
GITHUBACCESS_PULL: Literal['pull'] = "pull"
r"""The values for the 'GitHub access' enum"""
GITHUBACCESS_ADMIN: Literal['admin'] = "admin"
r"""The values for the 'GitHub access' enum"""



class Grid(TypedDict, total=False):
    r"""
    Grid.

    The WMTS grid definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids
    """

    resolution_scale: int
    r"""
    Resolution scale.

    The scale used to build a FreeTileGrid typically '2'
    """

    resolutions: Required[list[int | float]]
    r"""
    Resolutions.

    The resolutions in pixel per meter

    Required property
    """

    bbox: Required[list[int | float]]
    r"""
    Bounding box.

    The bounding box in meter

    minLength: 4
    maxLength: 4

    Required property
    """

    srs: Required[str]
    r"""
    SRS.

    The projection reference

    pattern: ^EPSG:[0-9]+$

    Required property
    """

    proj4_literal: str
    r"""
    Proj4 literal.

    The Proj4 definition
    """

    unit: str
    r"""
    Unit.

    The projection unit

    default: m
    """

    tile_size: int
    r"""
    Tile size.

    The tile size in pixel

    default: 256
    """

    matrix_identifier: "MatrixIdentifier"
    r"""
    Matrix identifier.

    The identifier to use in the tiles URL, recommend to be resolution (default)

    default: zoom
    """



HOST_DEFAULT = 's3-eu-west-1.amazonaws.com'
r""" Default value of the field path 'Cache S3 host' """



Headers = dict[str, "_HeadersAdditionalproperties"]
r"""
Headers.

The headers that we send to the WMS backend
"""



class Info(TypedDict, total=False):
    r"""
    Info.

    The information
    """

    phone: "Phone"
    r"""
    Phone.

    The phone
    """

    address: "Address"
    r"""
    Address.

    The address
    """



LAYER_LEGEND_DEFAULT: dict[str, Any] = {}
r""" Default value of the field path 'layer_legend' """



LAYER_LEGEND_ENABLED_DEFAULT = True
r""" Default value of the field path 'Layer legend enabled' """



LAYER_LEGEND_EXTENSION_DEFAULT = 'png'
r""" Default value of the field path 'layer_legend_extension' """



LAYER_LEGEND_MIME_TYPE_DEFAULT = 'image/png'
r""" Default value of the field path 'layer_legend_mime_type' """



LAYER_META_BUFFER_DEFAULT = 128
r""" Default value of the field path 'layer_meta_buffer' """



LAYER_META_DEFAULT = False
r""" Default value of the field path 'layer_meta' """



LAYER_META_SIZE_DEFAULT = 5
r""" Default value of the field path 'layer_meta_size' """



LAYER_PIXEL_BUFFER_DEFAULT = 0
r""" Default value of the field path 'layer_px_buffer' """



Layer = Union["LayerWms", "LayerMapnik"]
r"""
Layer.

The layer definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers

Aggregation type: anyOf
"""



LayerBoundingBox = list[int | float]
r"""
Layer bounding box.

The bounding box where we will generate the tiles

minLength: 4
maxLength: 4
"""



class LayerCost(TypedDict, total=False):
    r"""
    Layer cost.

    The rules used to calculate the cost
    """

    tileonly_generation_time: int | float
    r"""
    tile only generation time.

    The time to generate a tile without meta-tile

    default: 40
    """

    tile_generation_time: int | float
    r"""
    tile generation time.

    The time to generate a tile from the meta-tile

    default: 30
    """

    metatile_generation_time: int | float
    r"""
    Meta tile generation time.

    The time to generate a meta-tile

    default: 30
    """

    tile_size: int | float
    r"""
    Cost tile size.

    The tile mean size in bytes

    default: 20
    """



LayerDimensionName = str
r"""
Layer dimension name.

The dimension name

pattern: (?i)^(?!(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\-~\.]+$
"""



LayerDimensions = list["LayerDimensionsItem"]
r"""
layer dimensions.

The WMTS dimensions
"""



class LayerDimensionsItem(TypedDict, total=False):
    r""" layer dimensions item. """

    name: Required["LayerDimensionName"]
    r"""
    Layer dimension name.

    The dimension name

    pattern: (?i)^(?!(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\-~\.]+$

    Required property
    """

    generate: Required[list["_GenerateItem"]]
    r"""
    Generate.

    The values that should be generate

    Required property
    """

    values: Required[list["_ValuesItem"]]
    r"""
    Values.

    The values present in the capabilities

    Required property
    """

    default: Required[str]
    r"""
    Default.

    The default value present in the capabilities

    pattern: ^[a-zA-Z0-9_\-\+~\.]+$

    Required property
    """



class LayerEmptyMetaTileDetection(TypedDict, total=False):
    r"""
    Layer empty meta-tile detection.

    The rules used to detect the empty meta-tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    size: Required[int]
    r"""
    Size.

    The meta-tile size

    Required property
    """

    hash: Required[str]
    r"""
    Hash.

    The meta-tile hash

    Required property
    """



class LayerEmptyTileDetection(TypedDict, total=False):
    r"""
    Layer empty tile detection.

    The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    size: Required[int]
    r"""
    Title.

    The tile size

    Required property
    """

    hash: Required[str]
    r"""
    Hash.

    The tile hash

    Required property
    """



LayerExtension = str
r"""
Layer extension.

The layer extension
"""



LayerGeometries = list["_LayerGeometriesItem"]
r"""
Layer geometries.

The geometries used to determine where we should create the tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-geomsql
"""



LayerGrid = str
r"""
Layer grid.

The grid name, deprecated, use `grids` instead
"""



LayerGrids = list[str]
r"""
Layer grids.

All the used grids name used in the capabilities, by default only the `grid` is used, if `grid` is not defined, all the grids are used
"""



LayerLayers = str
r"""
Layer layers.

The WMS layers
"""



class LayerLegend(TypedDict, total=False):
    r"""
    Layer legend.

    Legend configuration for the layer

    default:
      {}
    """

    enabled: bool
    r"""
    Layer legend enabled.

    Set to false if the layer has no legend

    default: True
    """

    mime_type: "LayerLegendMimeType"
    r"""
    Layer legend MIME type.

    The mime type used to store the generated legend

    default: image/png
    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
    """

    extension: "LayerLegendExtension"
    r"""
    Layer legend extension.

    The extension used to store the generated legend

    default: png
    pattern: ^[a-zA-Z0-9]+$
    """

    items: "LayerLegends"
    r"""
    Layer legends.

    The provided legend
    """



LayerLegendExtension = str
r"""
Layer legend extension.

The extension used to store the generated legend

default: png
pattern: ^[a-zA-Z0-9]+$
"""



class LayerLegendItem(TypedDict, total=False):
    r""" Layer legend item. """

    mime_type: Required[str]
    r"""
    MIME type.

    The mime type used in the WMS request

    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$

    Required property
    """

    href: Required[str]
    r"""
    Href.

    The URL of the legend image

    Required property
    """

    width: int
    r"""
    Width.

    The width of the legend image
    """

    height: int
    r"""
    Height.

    The height of the legend image
    """

    min_scale: int | float
    r"""
    Min scale.

    The min scale of the legend image
    """

    max_scale: int | float
    r"""
    Max scale.

    The max scale of the legend image
    """

    min_resolution: int | float
    r"""
    Min resolution.

    The min resolution of the legend image
    """

    max_resolution: int | float
    r"""
    Max resolution.

    The max resolution of the legend image
    """



LayerLegendMimeType = str
r"""
Layer legend MIME type.

The mime type used to store the generated legend

default: image/png
pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
"""



LayerLegends = list["LayerLegendItem"]
r"""
Layer legends.

The provided legend
"""



class LayerMapnik(TypedDict, total=False):
    r""" Layer Mapnik. """

    type: Literal['mapnik']
    title: "LayerTitle"
    r"""
    Layer title.

    The title, use to generate the capabilities
    """

    grid: "LayerGrid"
    r"""
    Layer grid.

    The grid name, deprecated, use `grids` instead
    """

    grids: "LayerGrids"
    r"""
    Layer grids.

    All the used grids name used in the capabilities, by default only the `grid` is used, if `grid` is not defined, all the grids are used
    """

    srs: "LayerSrs"
    r"""
    Layer SRS.

    The projection reference, used for the bbox, the geoms, and the --bbox argument.

    pattern: ^EPSG:[0-9]+$
    """

    proj4_literal: "LayerProj4Literal"
    r"""
    Layer Proj4 literal.

    The Proj4 definition, used for the bbox, the geoms, and the --bbox argument.
    """

    bbox: "LayerBoundingBox"
    r"""
    Layer bounding box.

    The bounding box where we will generate the tiles

    minLength: 4
    maxLength: 4
    """

    min_resolution_seed: "LayerMinResolutionSeed"
    r"""
    layer min resolution seed.

    The minimum resolutions to pre-generate
    """

    px_buffer: "LayerPixelBuffer"
    r"""
    Layer pixel buffer.

    The buffer in pixel used to calculate geometry intersection

    default: 0
    """

    meta: "LayerMeta"
    r"""
    Layer meta.

    Use meta-tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles

    default: False
    """

    meta_size: "LayerMetaSize"
    r"""
    Layer meta size.

    The meta-tile size in tiles

    default: 5
    """

    meta_buffer: "LayerMetaBuffer"
    r"""
    Layer meta buffer.

    The meta-tiles buffer in pixels

    default: 128
    """

    layers: "LayerLayers"
    r"""
    Layer layers.

    The WMS layers
    """

    wmts_style: Required["LayerWmtsStyle"]
    r"""
    Layer WMTS style.

    The WMTS style

    pattern: ^[a-zA-Z0-9_\-\+~\.]+$

    Required property
    """

    mime_type: Required["LayerMimeType"]
    r"""
    Layer MIME type.

    The MIME type of the tiles

    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$

    Required property
    """

    extension: Required["LayerExtension"]
    r"""
    Layer extension.

    The layer extension

    Required property
    """

    dimensions: "LayerDimensions"
    r"""
    layer dimensions.

    The WMTS dimensions
    """

    legend: "LayerLegend"
    r"""
    Layer legend.

    Legend configuration for the layer

    default:
      {}
    """

    legends: "LayerLegends"
    r"""
    Layer legends.

    The provided legend
    """

    legend_mime: "LayerLegendMimeType"
    r"""
    Layer legend MIME type.

    The mime type used to store the generated legend

    default: image/png
    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
    """

    legend_extension: "LayerLegendExtension"
    r"""
    Layer legend extension.

    The extension used to store the generated legend

    default: png
    pattern: ^[a-zA-Z0-9]+$
    """

    pre_hash_post_process: "LayerPreHashPostProcess"
    r"""
    Layer pre hash post process.

    Do an image post process before the empty hash check
    """

    post_process: "LayerPostProcess"
    r"""
    Layer post process.

    Do an image post process after the empty hash check
    """

    geoms: "LayerGeometries"
    r"""
    Layer geometries.

    The geometries used to determine where we should create the tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-geomsql
    """

    empty_tile_detection: "LayerEmptyTileDetection"
    r"""
    Layer empty tile detection.

    The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    empty_metatile_detection: "LayerEmptyMetaTileDetection"
    r"""
    Layer empty meta-tile detection.

    The rules used to detect the empty meta-tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    cost: "LayerCost"
    r"""
    Layer cost.

    The rules used to calculate the cost
    """

    mapfile: str
    r"""
    MapFile.

    The Mapnik map file
    """

    data_buffer: int
    r"""
    Data buffer.

    The data buffer

    default: 128
    """

    output_format: "OutputFormat"
    r"""
    Output format.

    The Mapnik output format

    default: png
    """

    wms_url: str
    r"""
    WMS URL.

    A WMS fallback URL (deprecated)
    """

    resolution: int
    r"""
    Resolution.

    The resolution

    default: 4
    """

    layers_fields: dict[str, "_LayersFieldsAdditionalproperties"]
    r"""
    Layers fields.

    The Mapnik layers fields
    """

    drop_empty_utfgrid: bool
    r"""
    Drop empty UTFGrid.

    Drop if the tile is empty

    default: False
    """



LayerMeta = bool
r"""
Layer meta.

Use meta-tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles

default: False
"""



LayerMetaBuffer = int
r"""
Layer meta buffer.

The meta-tiles buffer in pixels

default: 128
"""



LayerMetaSaveOptions = dict[str, Any]
r"""
Layer meta save options.

The Pillow options used to save the tile generated from the meta-tiles
"""



LayerMetaSize = int
r"""
Layer meta size.

The meta-tile size in tiles

default: 5
"""



LayerMimeType = str
r"""
Layer MIME type.

The MIME type of the tiles

pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
"""



LayerMinResolutionSeed = int | float
r"""
layer min resolution seed.

The minimum resolutions to pre-generate
"""



LayerPixelBuffer = int
r"""
Layer pixel buffer.

The buffer in pixel used to calculate geometry intersection

default: 0
"""



LayerPostProcess = str
r"""
Layer post process.

Do an image post process after the empty hash check
"""



LayerPreHashPostProcess = str
r"""
Layer pre hash post process.

Do an image post process before the empty hash check
"""



LayerProj4Literal = str
r"""
Layer Proj4 literal.

The Proj4 definition, used for the bbox, the geoms, and the --bbox argument.
"""



LayerSrs = str
r"""
Layer SRS.

The projection reference, used for the bbox, the geoms, and the --bbox argument.

pattern: ^EPSG:[0-9]+$
"""



LayerTitle = str
r"""
Layer title.

The title, use to generate the capabilities
"""



class LayerWms(TypedDict, total=False):
    r""" Layer WMS. """

    type: Literal['wms']
    title: "LayerTitle"
    r"""
    Layer title.

    The title, use to generate the capabilities
    """

    grid: "LayerGrid"
    r"""
    Layer grid.

    The grid name, deprecated, use `grids` instead
    """

    grids: "LayerGrids"
    r"""
    Layer grids.

    All the used grids name used in the capabilities, by default only the `grid` is used, if `grid` is not defined, all the grids are used
    """

    srs: "LayerSrs"
    r"""
    Layer SRS.

    The projection reference, used for the bbox, the geoms, and the --bbox argument.

    pattern: ^EPSG:[0-9]+$
    """

    proj4_literal: "LayerProj4Literal"
    r"""
    Layer Proj4 literal.

    The Proj4 definition, used for the bbox, the geoms, and the --bbox argument.
    """

    bbox: "LayerBoundingBox"
    r"""
    Layer bounding box.

    The bounding box where we will generate the tiles

    minLength: 4
    maxLength: 4
    """

    min_resolution_seed: "LayerMinResolutionSeed"
    r"""
    layer min resolution seed.

    The minimum resolutions to pre-generate
    """

    px_buffer: "LayerPixelBuffer"
    r"""
    Layer pixel buffer.

    The buffer in pixel used to calculate geometry intersection

    default: 0
    """

    meta: "LayerMeta"
    r"""
    Layer meta.

    Use meta-tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles

    default: False
    """

    meta_size: "LayerMetaSize"
    r"""
    Layer meta size.

    The meta-tile size in tiles

    default: 5
    """

    meta_buffer: "LayerMetaBuffer"
    r"""
    Layer meta buffer.

    The meta-tiles buffer in pixels

    default: 128
    """

    meta_save_options: "LayerMetaSaveOptions"
    r"""
    Layer meta save options.

    The Pillow options used to save the tile generated from the meta-tiles
    """

    layers: Required["LayerLayers"]
    r"""
    Layer layers.

    The WMS layers

    Required property
    """

    wmts_style: Required["LayerWmtsStyle"]
    r"""
    Layer WMTS style.

    The WMTS style

    pattern: ^[a-zA-Z0-9_\-\+~\.]+$

    Required property
    """

    mime_type: Required["LayerMimeType"]
    r"""
    Layer MIME type.

    The MIME type of the tiles

    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$

    Required property
    """

    extension: Required["LayerExtension"]
    r"""
    Layer extension.

    The layer extension

    Required property
    """

    dimensions: "LayerDimensions"
    r"""
    layer dimensions.

    The WMTS dimensions
    """

    legend: "LayerLegend"
    r"""
    Layer legend.

    Legend configuration for the layer

    default:
      {}
    """

    legends: "LayerLegends"
    r"""
    Layer legends.

    The provided legend
    """

    legend_mime: "LayerLegendMimeType"
    r"""
    Layer legend MIME type.

    The mime type used to store the generated legend

    default: image/png
    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
    """

    legend_extension: "LayerLegendExtension"
    r"""
    Layer legend extension.

    The extension used to store the generated legend

    default: png
    pattern: ^[a-zA-Z0-9]+$
    """

    pre_hash_post_process: "LayerPreHashPostProcess"
    r"""
    Layer pre hash post process.

    Do an image post process before the empty hash check
    """

    post_process: "LayerPostProcess"
    r"""
    Layer post process.

    Do an image post process after the empty hash check
    """

    geoms: "LayerGeometries"
    r"""
    Layer geometries.

    The geometries used to determine where we should create the tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-geomsql
    """

    empty_tile_detection: "LayerEmptyTileDetection"
    r"""
    Layer empty tile detection.

    The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    empty_metatile_detection: "LayerEmptyMetaTileDetection"
    r"""
    Layer empty meta-tile detection.

    The rules used to detect the empty meta-tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    cost: "LayerCost"
    r"""
    Layer cost.

    The rules used to calculate the cost
    """

    url: Required[str]
    r"""
    URL.

    The WMS service URL

    Required property
    """

    generate_salt: bool
    r"""
    Generate salt.

    Should generate a salt to drop the cache

    default: False
    """

    query_layers: str
    r"""
    Query layers.

    The layers use for query (To be used with the server)
    """

    info_formats: list[str]
    r"""
    Info formats.

    The query info format
    """

    params: dict[str, "_ParametersAdditionalproperties"]
    r"""
    Parameters.

    Additional parameters to the WMS query (like dimension)
    """

    headers: "Headers"
    r"""
    Headers.

    The headers that we send to the WMS backend
    """

    version: str
    r"""
    Version.

    The used WMS version

    default: 1.1.1
    """



LayerWmtsStyle = str
r"""
Layer WMTS style.

The WMTS style

pattern: ^[a-zA-Z0-9_\-\+~\.]+$
"""



class Logging(TypedDict, total=False):
    r"""
    Logging.

    The logging configuration to database, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#logging (main configuration)
    """

    database: Required["Database"]
    r"""
    Database.

    The database (main configuration)

    Required property
    """



MAP_INITIAL_ZOOM_DEFAULT = 3
r""" Default value of the field path 'OpenLayers zoom' """



MATRIX_IDENTIFIER_DEFAULT = 'zoom'
r""" Default value of the field path 'Grid matrix_identifier' """



MAX_CONSECUTIVE_ERRORS_DEFAULT = 10
r""" Default value of the field path 'Generation maxconsecutive_errors' """



MAX_ERRORS_AGE_DEFAULT = 86400
r""" Default value of the field path 'Redis max_errors_age' """



MAX_ERRORS_NUMBER_DEFAULT = 100
r""" Default value of the field path 'Redis max_errors_nb' """



MAX_PENDING_MINUTES_DEFAULT = 10
r""" Default value of the field path 'PostgreSQL max_pending_minutes' """



MAX_RETRIES_DEFAULT = 5
r""" Default value of the field path 'Redis max_retries' """



META_TILE_GENERATION_TIME_DEFAULT = 30
r""" Default value of the field path 'Layer cost metatile_generation_time' """



MatrixIdentifier = Literal['zoom'] | Literal['resolution']
r"""
Matrix identifier.

The identifier to use in the tiles URL, recommend to be resolution (default)

default: zoom
"""
MATRIXIDENTIFIER_ZOOM: Literal['zoom'] = "zoom"
r"""The values for the 'Matrix identifier' enum"""
MATRIXIDENTIFIER_RESOLUTION: Literal['resolution'] = "resolution"
r"""The values for the 'Matrix identifier' enum"""



class Metadata(TypedDict, total=False):
    r"""
    Metadata.

    The configuration of the WMTS capabilities metadata
    """

    title: Required[str]
    r"""
    Title.

    The title

    Required property
    """

    abstract: str
    r"""
    Abstract.

    The abstract
    """

    servicetype: str
    r"""
    Service type.

    The service type

    default: OGC WMTS
    """

    keywords: list[str]
    r"""
    Keywords.

    The keywords
    """

    fees: str
    r"""
    Fees.

    The fees
    """

    access_constraints: str
    r"""
    Access constraints.

    The access constraints
    """



NEED_OUT_DEFAULT = False
r""" Default value of the field path 'Process command item need_out' """



NUMBER_PROCESS_DEFAULT = 1
r""" Default value of the field path 'Generation number_process' """



OUTPUT_FORMAT_DEFAULT = 'png'
r""" Default value of the field path 'Layer Mapnik output_format' """



class Openlayers(TypedDict, total=False):
    r"""
    OpenLayers.

    Configuration used to generate the OpenLayers example page
    """

    srs: str
    r"""
    SRS.

    The projection code

    pattern: ^EPSG:[0-9]+$
    default: EPSG:2056
    """

    proj4js_def: str
    r"""
    Proj4js definition.

    The `proj4js` definition, by default it will be build with pyproj
    """

    center_x: int | float
    r"""
    Center x.

    The center easting

    default: 2600000
    """

    center_y: int | float
    r"""
    Center y.

    The center northing

    default: 1200000
    """

    zoom: int | float
    r"""
    Map initial zoom.

    The initial zoom

    default: 3
    """



OutputFormat = Literal['png'] | Literal['png256'] | Literal['jpeg'] | Literal['grid']
r"""
Output format.

The Mapnik output format

default: png
"""
OUTPUTFORMAT_PNG: Literal['png'] = "png"
r"""The values for the 'Output format' enum"""
OUTPUTFORMAT_PNG256: Literal['png256'] = "png256"
r"""The values for the 'Output format' enum"""
OUTPUTFORMAT_JPEG: Literal['jpeg'] = "jpeg"
r"""The values for the 'Output format' enum"""
OUTPUTFORMAT_GRID: Literal['grid'] = "grid"
r"""The values for the 'Output format' enum"""



PENDING_COUNT_DEFAULT = 10
r""" Default value of the field path 'Redis pending_count' """



PENDING_MAX_COUNT_DEFAULT = 10000
r""" Default value of the field path 'Redis pending_max_count' """



PENDING_TIMEOUT_DEFAULT = 300
r""" Default value of the field path 'Redis pending_timeout' """



PORT_DEFAULT = 5432
r""" Default value of the field path 'Database port' """



PREFIX_DEFAULT = 'tilecloud_cache'
r""" Default value of the field path 'Redis prefix' """



class Phone(TypedDict, total=False):
    r"""
    Phone.

    The phone
    """

    voice: str
    r"""
    Voice.

    The voice number
    """

    fax: str
    r"""
    Fax.

    The fax number
    """



class Postgresql(TypedDict, total=False):
    r"""
    PostgreSQL.

    The PostgreSQL configuration (main configuration), the schema can be configured with the `TILECLOUD_CHAIN_POSTGRESQL_SCHEMA` environment variable
    """

    sqlalchemy_url: str
    r"""
    SQLAlchemy URL.

    The SQLAlchemy URL (like: `postgresql+psycopg2://username:password@host:5432/database`) (main configuration), can also be set in the `TILECLOUD_CHAIN_SQLALCHEMY_URL` environment variable
    """

    max_pending_minutes: int
    r"""
    Max pending minutes.

    The max pending minutes (main configuration)

    default: 10
    """



ProcessCommand = list["_ProcessCommandItem"]
r"""
Process command.

A command
"""



class Provider(TypedDict, total=False):
    r"""
    Provider.

    The provider
    """

    name: str
    r""" Name. """

    url: str
    r"""
    URL.

    The public URL
    """

    contact: "Contact"
    r"""
    Contact.

    The contact
    """



QUEUE_STORE_DEFAULT = 'redis'
r""" Default value of the field path 'TileCloud-chain configuration queue_store' """



QueueStore = Literal['redis'] | Literal['sqs'] | Literal['postgresql']
r"""
Queue store.

The used queue store

default: redis
"""
QUEUESTORE_REDIS: Literal['redis'] = "redis"
r"""The values for the 'Queue store' enum"""
QUEUESTORE_SQS: Literal['sqs'] = "sqs"
r"""The values for the 'Queue store' enum"""
QUEUESTORE_POSTGRESQL: Literal['postgresql'] = "postgresql"
r"""The values for the 'Queue store' enum"""



REDIS_QUEUE_DEFAULT = 'tilecloud'
r""" Default value of the field path 'Redis queue' """



REQUEST_DEFAULT = 0.01
r""" Default value of the field path 'SQS cost request' """



REQUEST_PER_LAYERS_DEFAULT = 10000000
r""" Default value of the field path 'Cost request_per_layers' """



RESOLUTION_DEFAULT = 4
r""" Default value of the field path 'Layer Mapnik resolution' """



class Redis(TypedDict, total=False):
    r"""
    Redis.

    The Redis configuration (main configuration)
    """

    url: str
    r"""
    URL.

    The server URL (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_URL` environment variable

    pattern: ^rediss?://([^:@/]*:[^:@/]*@)?[^:@/]+(:[0-9]+)?(/.*)?$
    """

    sentinels: list["_SentinelsItem"]
    r"""
    Sentinels.

    The sentinels (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_SENTINELS` environment variable
    """

    connection_kwargs: dict[str, Any]
    r""" The Redis connection arguments (main configuration) """

    sentinel_kwargs: dict[str, Any]
    r""" The Redis sentinel arguments (main configuration) """

    service_name: str
    r"""
    Service name.

    The service name (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_SERVICE_NAME` environment variable

    default: mymaster
    """

    socket_timeout: int
    r"""
    Socket timeout.

    The socket timeout (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_SOCKET_TIMEOUT` environment variable
    """

    db: int
    r"""
    Database.

    The database number (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_DB` environment variable
    """

    queue: str
    r"""
    Redis queue.

    The queue name (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_QUEUE` environment variable

    default: tilecloud
    """

    timeout: int
    r"""
    Timeout.

    The timeout (main configuration), can also be set in the `TILECLOUD_CHAIN_REDIS_TIMEOUT` environment variable

    default: 5
    """

    pending_timeout: int
    r"""
    Pending timeout.

    The pending timeout (main configuration)

    default: 300
    """

    max_retries: int
    r"""
    Max retries.

    The max retries (main configuration)

    default: 5
    """

    max_errors_age: int
    r"""
    Max errors age.

    The max error age (main configuration), default is 1 day

    default: 86400
    """

    max_errors_nb: int
    r"""
    Max errors number.

    The max error number (main configuration)

    default: 100
    """

    prefix: str
    r"""
    Prefix.

    The prefix (main configuration)

    default: tilecloud_cache
    """

    expiration: int
    r"""
    Expiration.

    The meta-tile in queue expiration (main configuration), default is 8 hours

    default: 28800
    """

    pending_count: int
    r"""
    Pending count.

    The pending count: the number of pending tiles get in one request (main configuration)

    default: 10
    """

    pending_max_count: int
    r"""
    Pending max count.

    The pending max count: the maximum number of pending tiles get in one pass (if not generating other tiles, every second) (main configuration)

    default: 10000
    """



class S3Cost(TypedDict, total=False):
    r"""
    S3 cost.

    The S3 cost (main configuration)
    """

    storage: int | float
    r"""
    S3 Storage.

    The storage cost in $ / Gio / month (main configuration)

    default: 0.125
    """

    put: int | float
    r"""
    S3 Put.

    The cost of put in $ per 10 000 requests (main configuration)

    default: 0.01
    """

    get: int | float
    r"""
    S3 Get.

    The cost of get in $ per 10 000 requests (main configuration)

    default: 0.01
    """

    download: int | float
    r"""
    S3 Download.

    The cost of download in $ per Gio (main configuration)

    default: 0.12
    """



S3_DOWNLOAD_DEFAULT = 0.12
r""" Default value of the field path 'S3 cost download' """



S3_GET_DEFAULT = 0.01
r""" Default value of the field path 'S3 cost get' """



S3_PUT_DEFAULT = 0.01
r""" Default value of the field path 'S3 cost put' """



S3_STORAGE_DEFAULT = 0.125
r""" Default value of the field path 'S3 cost storage' """



SERVICE_NAME_DEFAULT = 'mymaster'
r""" Default value of the field path 'Redis service_name' """



SERVICE_TYPE_DEFAULT = 'OGC WMTS'
r""" Default value of the field path 'Metadata servicetype' """



SQS_QUEUE_DEFAULT = 'tilecloud'
r""" Default value of the field path 'SQS queue' """



SRS_DEFAULT = 'EPSG:2056'
r""" Default value of the field path 'OpenLayers srs' """



STATIC_ALLOW_EXTENSION_DEFAULT = ['jpeg', 'png', 'xml', 'js', 'html', 'css']
r""" Default value of the field path 'Server static_allow_extension' """



SentinelHost = str
r"""
Sentinel host.

The sentinel host name (main configuration)
"""



SentinelPort = str | int
r"""
Sentinel port.

The sentinel port (main configuration)

Aggregation type: anyOf
"""



class Server(TypedDict, total=False):
    r"""
    Server.

    Configuration used by the tile server, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#distribute-the-tiles
    """

    cache: str
    r"""
    Cache.

    The used cache name
    """

    layers: list[str]
    r"""
    WMS Layers.

    Layers available in the server, default is all layers
    """

    geoms_redirect: bool
    r"""
    Geometries redirect.

    Take care on the geometries

    default: False
    """

    static_allow_extension: list[str]
    r"""
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
    r"""
    WMTS path.

    No more used, replaced by `TILECLOUD_CHAIN__WMTS_PATH` environment variable
    """

    expires: int
    r"""
    Expires.

    The browser cache expiration in hours

    default: 8
    """

    predefined_commands: list["_PredefinedCommandsItem"]
    r"""
    Predefined commands.

    The predefined commands used to generate the tiles
    """

    allowed_commands: list[str]
    r"""
    Allowed commands.

    The allowed commands (main configuration)

    default:
      - generate-tiles
      - generate-controller
      - generate-cost
    """

    allowed_arguments: list[str]
    r"""
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
      - --grid
      - --test
      - --near
      - --time
      - --measure-generation-time
      - --no-geom
      - --dimensions
    """

    admin_footer: str
    r"""
    admin footer.

    The footer of the admin interface
    """

    admin_footer_classes: str
    r"""
    admin footer classes.

    The CSS classes used on the footer of the admin interface
    """



class Sns(TypedDict, total=False):
    r"""
    SNS.

    The Simple Notification Service configuration, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sns
    """

    topic: Required[str]
    r"""
    Topic.

    The topic

    Required property
    """

    region: "AwsRegion"
    r"""
    AWS region.

    The region

    pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
    default: eu-west-1
    """



class Sqs(TypedDict, total=False):
    r"""
    SQS.

    The Simple Queue Service configuration
    """

    queue: str
    r"""
    SQS queue.

    The queue name

    default: tilecloud
    """

    region: "AwsRegion"
    r"""
    AWS region.

    The region

    pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
    default: eu-west-1
    """



class SqsCost(TypedDict, total=False):
    r"""
    SQS cost.

    The SQS cost, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sqs (main configuration)
    """

    request: int | float
    r"""
    Request.

    The cost of request in $ per 1 000 000 requests (main configuration)

    default: 0.01
    """



TILES_URL_DEFAULT = 'http://s3-{region}.amazonaws.com/{bucket}/{folder}'
r""" Default value of the field path 'Cache S3 tiles_url' """



TILE_GENERATION_TIME_DEFAULT = 30
r""" Default value of the field path 'Layer cost tile_generation_time' """



TILE_ONLY_GENERATION_TIME_DEFAULT = 40
r""" Default value of the field path 'Layer cost tileonly_generation_time' """



TILE_SIZE_DEFAULT = 256
r""" Default value of the field path 'Grid tile_size' """



TIMEOUT_DEFAULT = 5
r""" Default value of the field path 'Redis timeout' """



UNIT_DEFAULT = 'm'
r""" Default value of the field path 'Grid unit' """



VERSION_DEFAULT = '1.1.1'
r""" Default value of the field path 'Layer WMS version' """



_GenerateItem = str
r""" pattern: ^[a-zA-Z0-9_\-\+~\.]+$ """



_HeadersAdditionalproperties = str
r""" The header value """



_LAYER_MAPNIK_LAYERS_DEFAULT = '__all__'
r""" Default value of the field path 'Layer Mapnik layers' """



_LAYER_MAPNIK_META_BUFFER_DEFAULT = 0
r""" Default value of the field path 'Layer Mapnik meta_buffer' """



_LAYER_MAPNIK_META_SIZE_DEFAULT = 1
r""" Default value of the field path 'Layer Mapnik meta_size' """



_LAYER_WMS_META_BUFFER_DEFAULT = 128
r""" Default value of the field path 'Layer WMS meta_buffer' """



_LAYER_WMS_META_SIZE_DEFAULT = 5
r""" Default value of the field path 'Layer WMS meta_size' """



class _LayerGeometriesItem(TypedDict, total=False):
    connection: Required[str]
    r"""
    Connection.

    The PostgreSQL connection string

    Required property
    """

    sql: Required[str]
    r"""
    SQL.

    The SQL query that get the geometry in geom e.g. `the_geom AS geom FROM my_table`

    Required property
    """

    min_resolution: int | float
    r"""
    Min resolution.

    The min resolution where the query is valid
    """

    max_resolution: int | float
    r"""
    Max resolution.

    The max resolution where the query is valid
    """



_LayersFieldsAdditionalproperties = list[str]
r""" The Mapnik layer fields """



_ParametersAdditionalproperties = str
r""" The parameter value """



class _PredefinedCommandsItem(TypedDict, total=False):
    command: str
    r"""
    Command.

    The command to run
    """

    name: str
    r"""
    Name.

    The name used in the admin interface
    """



class _ProcessCommandItem(TypedDict, total=False):
    cmd: Required[str]
    r"""
    Command.

    The shell command, available parameters: `%(in)s`, `%(out)s`,` %(args)s`, `%(x)s`, `%(y)s`, `%(z)s`.

    Required property
    """

    need_out: bool
    r"""
    Need out.

    The command will generate an output in a file

    default: False
    """

    arg: "Argument"
    r"""
    Argument.

    Used to build the `%(args)`
    """



_SentinelsItem = tuple["SentinelHost", "SentinelPort"]
r""" A sentinel (main configuration) """



_ValuesItem = str
r""" pattern: ^[a-zA-Z0-9_\-\+~\.]+$ """

