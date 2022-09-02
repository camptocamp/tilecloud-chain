"""
Automatically generated file from a JSON schema.
"""


from typing import Any, Dict, List, Literal, Tuple, TypedDict, Union

# Default value of the field path 'Server admin_path'
ADMIN_PATH_DEFAULT = "admin"


# Address
#
# The address
class Address(TypedDict, total=False):
    delivery: str
    city: str
    area: str
    postal_code: int
    country: str
    email: str


# Argument
#
# Used to build the %(args)
class Argument(TypedDict, total=False):
    default: str
    verbose: str
    debug: str
    quiet: str


# Authentication
#
# The authentication configuration
class Authentication(TypedDict, total=False):
    github_repository: str
    github_access_type: "GithubAccess"


# AWS region
#
# The region, default is 'eu-west-1'
#
# pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
AwsRegion = str


# Default value of the field path 'Cache filesystem folder'
CACHE_FOLDER_DEFAULT = ""


# Default value of the field path 'OpenLayers center_x'
CENTER_X_DEFAULT = 2600000


# Default value of the field path 'OpenLayers center_y'
CENTER_Y_DEFAULT = 1200000


# Cache
#
# The tiles cache definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches
Cache = Union["CacheFilesystem", "CacheS3", "CacheAzure", "CacheMbtiles", "CacheBsddb"]


# Cache Azure
#
# Azure Blob Storage
#
# WARNING: The required are not correctly taken in account,
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
#
# WARNING: Normally the types should be a mix of each other instead of Union.
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
CacheAzure = Union[Dict[str, str], "CacheAzureTyped"]


class CacheAzureTyped(TypedDict, total=False):
    type: Literal["azure"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    folder: "CacheFolder"
    container: str
    cache_control: str


# Cache BSDDB
#
# WARNING: The required are not correctly taken in account,
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
#
# WARNING: Normally the types should be a mix of each other instead of Union.
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
CacheBsddb = Union[Dict[str, str], "CacheBsddbTyped"]


class CacheBsddbTyped(TypedDict, total=False):
    type: Literal["bsddb"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    folder: "CacheFolder"


# Cache filesystem
#
# WARNING: The required are not correctly taken in account,
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
#
# WARNING: Normally the types should be a mix of each other instead of Union.
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
CacheFilesystem = Union[Dict[str, str], "CacheFilesystemTyped"]


class CacheFilesystemTyped(TypedDict, total=False):
    type: Literal["filesystem"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    folder: "CacheFolder"


# Cache folder
#
# The root folder of the cache, default is ''
#
# default:
CacheFolder = str


# Cache host
#
# The host used to build the HTTP URLs
CacheHost = List[str]


# Cache HTTP URL
#
# The HTTP URL %host will be replaces by one of the hosts
CacheHttpUrl = str


# Cache HTTP URLs
CacheHttpUrls = List[str]


# Cache MBtiles
#
# WARNING: The required are not correctly taken in account,
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
#
# WARNING: Normally the types should be a mix of each other instead of Union.
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
CacheMbtiles = Union[Dict[str, str], "CacheMbtilesTyped"]


class CacheMbtilesTyped(TypedDict, total=False):
    type: Literal["mbtiles"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    folder: "CacheFolder"


# Cache S3
#
# WARNING: The required are not correctly taken in account,
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
#
# WARNING: Normally the types should be a mix of each other instead of Union.
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
CacheS3 = Union[Dict[str, str], "CacheS3Typed"]


class CacheS3Typed(TypedDict, total=False):
    type: Literal["s3"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    tiles_url: str
    host: str
    bucket: str
    region: "AwsRegion"
    cache_control: str
    folder: "CacheFolder"


# Cache WMST capabilities file
#
# The generated WMTS capabilities file name (by 'default 1.0.0/WMTSCapabilities.xml')
CacheWmstCapabilitiesFile = str


# CloudFront cost
#
# The CloudFront cost (main configuration)
class CloudfrontCost(TypedDict, total=False):
    get: Union[int, float]
    download: Union[int, float]


# TileCloud-chain configuration
class Configuration(TypedDict, total=False):
    defaults: Dict[str, Any]
    grids: Dict[str, "Grid"]
    caches: Dict[str, "Cache"]
    layers: Dict[str, "Layer"]
    process: Dict[str, "ProcessCommand"]
    generation: "Generation"
    sqs: "Sqs"
    sns: "Sns"
    redis: "Redis"
    openlayers: "Openlayers"
    server: "Server"
    cost: "Cost"
    metadata: "Metadata"
    provider: "Provider"
    logging: "Logging"
    authentication: "Authentication"


# Contact
#
# The contact
class Contact(TypedDict, total=False):
    name: str
    position: str
    info: "Info"


# Cost
#
# The configuration use to calculate the cast (unmaintained)
class Cost(TypedDict, total=False):
    request_per_layers: int
    s3: "S3Cost"
    cloudfront: "CloudfrontCost"
    sqs: "SqsCost"


# Default value of the field path 'Generation default_cache'
DEFAULT_CACHE_DEFAULT = "default"


# Default value of the field path 'S3 cost download'
DOWNLOAD_DEFAULT = 0.12


# Default value of the field path 'CloudFront cost download'
DOWNLOAD_DEFAULTGen253567 = 0.12


# Database
#
# The database (main configuration)
class Database(TypedDict, total=False):
    host: str
    port: int
    dbname: str
    table: str
    user: str
    password: str


# Default value of the field path 'Redis expiration'
EXPIRATION_DEFAULT = 28800


# Default value of the field path 'Server expires'
EXPIRES_DEFAULT = 8


# Default value of the field path 'Server geoms_redirect'
GEOMETRIES_REDIRECT_DEFAULT = False


# Default value of the field path 'S3 cost get'
GET_DEFAULT = 0.01


# Default value of the field path 'CloudFront cost get'
GET_DEFAULTGen24276 = 0.009


# Default value of the field path 'Authentication github_access_type'
GITHUB_ACCESS_DEFAULT = "pull"


# Generation
#
# The configuration used for the generation
class Generation(TypedDict, total=False):
    default_cache: str
    default_layers: List[str]
    authorised_user: str
    maxconsecutive_errors: int
    error_file: str
    number_process: int


# GitHub access
#
# The kind of rights the user should have on the repository
#
# default: pull
GithubAccess = Union[Literal["push"], Literal["pull"], Literal["admin"]]
# The values for the enum
GITHUBACCESS_PUSH: Literal["push"] = "push"
GITHUBACCESS_PULL: Literal["pull"] = "pull"
GITHUBACCESS_ADMIN: Literal["admin"] = "admin"


# Grid
#
# The WMTS grid definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids
class Grid(TypedDict, total=False):
    resolution_scale: int
    resolutions: List[Union[int, float]]
    bbox: List[Union[int, float]]
    srs: str
    proj4_literal: str
    unit: str
    tile_size: int
    matrix_identifier: "MatrixIdentifier"


# Headers
#
# The headers that we send to the WMS backend
Headers = Dict[str, "_HeadersAdditionalproperties"]


# Info
#
# The information
class Info(TypedDict, total=False):
    phone: "Phone"
    address: "Address"


# Default value of the field path 'Layer WMS meta_buffer'
LAYER_META_BUFFER_DEFAULT = 128


# Default value of the field path 'Layer WMS meta'
LAYER_META_DEFAULT = False


# Default value of the field path 'Layer WMS meta_size'
LAYER_META_SIZE_DEFAULT = 5


# Default value of the field path 'Layer WMS px_buffer'
LAYER_PIXEL_BUFFER_DEFAULT = 0


# Layer
#
# The layer definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers
Layer = Union["LayerWms", "LayerMapnik"]


# Layer bounding box
#
# The bounding box where we will generate the tiles
#
# minLength: 4
# maxLength: 4
LayerBoundingBox = List[Union[int, float]]


# Layer cost
#
# The rules used to calculate the cost
class LayerCost(TypedDict, total=False):
    tileonly_generation_time: Union[int, float]
    tile_generation_time: Union[int, float]
    metatile_generation_time: Union[int, float]
    tile_size: Union[int, float]


# Layer dimension name
#
# The dimension name
#
# pattern: ^(?!(?i)(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\-~\.]+$
LayerDimensionName = str


# layer dimensions
#
# The WMTS dimensions
LayerDimensions = List["_LayerDimensionsItem"]


# Layer empty meta-tile detection
#
# The rules used to detect the empty meta-tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
class LayerEmptyMetaTileDetection(TypedDict, total=False):
    size: int
    hash: str


# Layer empty tile detection
#
# The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
class LayerEmptyTileDetection(TypedDict, total=False):
    size: int
    hash: str


# Layer extension
#
# The layer extension
LayerExtension = str


# Layer geometries
#
# The geometries used to determine where we should create the tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-geomsql
LayerGeometries = List["_LayerGeometriesItem"]


# Layer grid
#
# The used grid name
LayerGrid = str


# Layer layers
#
# The WMS layers
LayerLayers = str


# Layer legend extension
#
# The extension used to store the generated legend
#
# pattern: ^[a-zA-Z0-9]+$
LayerLegendExtension = str


# Layer legend MIME
#
# The mime type used to store the generated legend
#
# pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
LayerLegendMime = str


# Layer legends
#
# The provided legend
LayerLegends = List["_LayerLegendsItem"]


# Layer Mapnik
class LayerMapnik(TypedDict, total=False):
    type: Literal["mapnik"]
    title: "LayerTitle"
    grid: "LayerGrid"
    bbox: "LayerBoundingBox"
    min_resolution_seed: "LayerMinResolutionSeed"
    px_buffer: "LayerPixelBuffer"
    meta: "LayerMeta"
    meta_size: "LayerMetaSize"
    meta_buffer: "LayerMetaBuffer"
    layers: "LayerLayers"
    wmts_style: "LayerWmtsStyle"
    mime_type: "LayerMimeType"
    extension: "LayerExtension"
    dimensions: "LayerDimensions"
    legends: "LayerLegends"
    legend_mime: "LayerLegendMime"
    legend_extension: "LayerLegendExtension"
    pre_hash_post_process: "LayerPreHashPostProcess"
    post_process: "LayerPostProcess"
    geoms: "LayerGeometries"
    empty_tile_detection: "LayerEmptyTileDetection"
    empty_metatile_detection: "LayerEmptyMetaTileDetection"
    cost: "LayerCost"
    mapfile: str
    data_buffer: int
    output_format: "OutputFormat"
    wms_url: str
    resolution: int
    layers_fields: Dict[str, "_LayersFieldsAdditionalproperties"]
    drop_empty_utfgrid: bool


# Layer meta
#
# Use meta-tiles, default is False, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles
#
# default: False
LayerMeta = bool


# Layer meta buffer
#
# The meta-tiles buffer in pixels, default is 128
#
# default: 128
LayerMetaBuffer = int


# Layer meta size
#
# The meta-tile size in tiles, default is 5
#
# default: 5
LayerMetaSize = int


# Layer MIME type
#
# The MIME type of the tiles
#
# pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
LayerMimeType = str


# layer min resolution seed
#
# The minimum resolutions to pre-generate
LayerMinResolutionSeed = Union[int, float]


# Layer pixel buffer
#
# The buffer in pixel used to calculate geometry intersection, default is 0
#
# default: 0
LayerPixelBuffer = int


# Layer post process
#
# Do an image post process after the empty hash check
LayerPostProcess = str


# Layer pre hash post process
#
# Do an image post process before the empty hash check
LayerPreHashPostProcess = str


# Layer title
#
# The title, use to generate the capabilities
LayerTitle = str


# Layer WMS
class LayerWms(TypedDict, total=False):
    type: Literal["wms"]
    title: "LayerTitle"
    grid: "LayerGrid"
    bbox: "LayerBoundingBox"
    min_resolution_seed: "LayerMinResolutionSeed"
    px_buffer: "LayerPixelBuffer"
    meta: "LayerMeta"
    meta_size: "LayerMetaSize"
    meta_buffer: "LayerMetaBuffer"
    layers: "LayerLayers"
    wmts_style: "LayerWmtsStyle"
    mime_type: "LayerMimeType"
    extension: "LayerExtension"
    dimensions: "LayerDimensions"
    legends: "LayerLegends"
    legend_mime: "LayerLegendMime"
    legend_extension: "LayerLegendExtension"
    pre_hash_post_process: "LayerPreHashPostProcess"
    post_process: "LayerPostProcess"
    geoms: "LayerGeometries"
    empty_tile_detection: "LayerEmptyTileDetection"
    empty_metatile_detection: "LayerEmptyMetaTileDetection"
    cost: "LayerCost"
    url: str
    generate_salt: bool
    query_layers: str
    info_formats: List[str]
    params: Dict[str, "_ParametersAdditionalproperties"]
    headers: "Headers"
    version: str


# Layer WMTS style
#
# The WMTS style
#
# pattern: ^[a-zA-Z0-9_\-\+~\.]+$
LayerWmtsStyle = str


# Logging
#
# The logging configuration to database, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#logging (main configuration)
class Logging(TypedDict, total=False):
    database: "Database"


# Default value of the field path 'OpenLayers zoom'
MAP_INITIAL_ZOOM_DEFAULT = 3


# Default value of the field path 'Grid matrix_identifier'
MATRIX_IDENTIFIER_DEFAULT = "zoom"


# Default value of the field path 'Generation maxconsecutive_errors'
MAX_CONSECUTIVE_ERRORS_DEFAULT = 10


# Default value of the field path 'Redis max_errors_age'
MAX_ERRORS_AGE_DEFAULT = 86400


# Default value of the field path 'Redis max_errors_nb'
MAX_ERRORS_NUMBER_DEFAULT = 100


# Default value of the field path 'Redis max_retries'
MAX_RETRIES_DEFAULT = 5


# Default value of the field path 'Layer cost metatile_generation_time'
META_TILE_GENERATION_TIME_DEFAULT = 30


# Matrix identifier
#
# The identifier to use in the tiles URL, recommend to be resolution (default)
#
# default: zoom
MatrixIdentifier = Union[Literal["zoom"], Literal["resolution"]]
# The values for the enum
MATRIXIDENTIFIER_ZOOM: Literal["zoom"] = "zoom"
MATRIXIDENTIFIER_RESOLUTION: Literal["resolution"] = "resolution"


# Metadata
#
# The configuration of the WMTS capabilities metadata
class Metadata(TypedDict, total=False):
    title: str
    abstract: str
    servicetype: str
    keywords: List[str]
    fees: str
    access_constraints: str


# Default value of the field path 'Process command item need_out'
NEED_OUT_DEFAULT = False


# Default value of the field path 'Generation number_process'
NUMBER_PROCESS_DEFAULT = 1


# OpenLayers
#
# Configuration used to generate the OpenLayers example page
class Openlayers(TypedDict, total=False):
    srs: str
    proj4js_def: str
    center_x: Union[int, float]
    center_y: Union[int, float]
    zoom: Union[int, float]


# Output format
#
# The Mapnik output format, default is 'png'
OutputFormat = Union[Literal["png"], Literal["png256"], Literal["jpeg"], Literal["grid"]]
# The values for the enum
OUTPUTFORMAT_PNG: Literal["png"] = "png"
OUTPUTFORMAT_PNG256: Literal["png256"] = "png256"
OUTPUTFORMAT_JPEG: Literal["jpeg"] = "jpeg"
OUTPUTFORMAT_GRID: Literal["grid"] = "grid"


# Default value of the field path 'Redis pending_timeout'
PENDING_TIMEOUT_DEFAULT = 300


# Default value of the field path 'Database port'
PORT_DEFAULT = 5432


# Default value of the field path 'Redis prefix'
PREFIX_DEFAULT = "tilecloud_cache"


# Default value of the field path 'S3 cost put'
PUT_DEFAULT = 0.01


# Phone
#
# The phone
class Phone(TypedDict, total=False):
    voice: str
    fax: str


# Process command
#
# A command
ProcessCommand = List["_ProcessCommandItem"]


# Provider
#
# The provider
class Provider(TypedDict, total=False):
    name: str
    url: str
    contact: "Contact"


# Default value of the field path 'Redis queue'
QUEUE_DEFAULT = "tilecloud"


# Default value of the field path 'SQS cost request'
REQUEST_DEFAULT = 0.01


# Default value of the field path 'Cost request_per_layers'
REQUEST_PER_LAYERS_DEFAULT = 10000000


# Redis
#
# The Redis configuration (main configuration)
class Redis(TypedDict, total=False):
    url: str
    sentinels: List["_SentinelsItem"]
    connection_kwargs: Dict[str, Any]
    sentinel_kwargs: Dict[str, Any]
    service_name: str
    socket_timeout: int
    db: int
    queue: str
    timeout: int
    pending_timeout: int
    max_retries: int
    max_errors_age: int
    max_errors_nb: int
    prefix: str
    expiration: int


# S3 cost
#
# The S3 cost (main configuration)
class S3Cost(TypedDict, total=False):
    storage: Union[int, float]
    put: Union[int, float]
    get: Union[int, float]
    download: Union[int, float]


# Default value of the field path 'Redis service_name'
SERVICE_NAME_DEFAULT = "mymaster"


# Default value of the field path 'Metadata servicetype'
SERVICE_TYPE_DEFAULT = "OGC WMTS"


# Default value of the field path 'OpenLayers srs'
SRS_DEFAULT = "EPSG:2056"


# Default value of the field path 'Server static_path'
STATIC_PATH_DEFAULT = "static"


# Default value of the field path 'S3 cost storage'
STORAGE_DEFAULT = 0.125


# Sentinel host
#
# The sentinel host name (main configuration)
SentinelHost = str


# Sentinel port
#
# The sentinel port (main configuration)
SentinelPort = Union[str, int]


# Server
#
# Configuration used by the tile server, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#distribute-the-tiles
class Server(TypedDict, total=False):
    cache: str
    layers: List[str]
    geoms_redirect: bool
    static_allow_extension: List[str]
    wmts_path: str
    static_path: str
    admin_path: str
    expires: int
    predefined_commands: List["_PredefinedCommandsItem"]
    allowed_commands: List[str]
    allowed_arguments: List[str]


# SNS
#
# The Simple Notification Service configuration, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sns
class Sns(TypedDict, total=False):
    topic: str
    region: "AwsRegion"


# SQS
#
# The Simple Queue Service configuration
class Sqs(TypedDict, total=False):
    queue: str
    region: "AwsRegion"


# SQS cost
#
# The SQS cost, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sqs (main configuration)
class SqsCost(TypedDict, total=False):
    request: Union[int, float]


# Default value of the field path 'OpenLayers proj4js_def'
THE_PROJ4JS_DEFINITION_DEFAULT = "+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs"


# Default value of the field path 'Layer cost tile_generation_time'
TILE_GENERATION_TIME_DEFAULT = 30


# Default value of the field path 'Layer cost tileonly_generation_time'
TILE_ONLY_GENERATION_TIME_DEFAULT = 40


# Default value of the field path 'Grid tile_size'
TILE_SIZE_DEFAULT = 256


# Default value of the field path 'Layer cost tile_size'
TILE_SIZE_DEFAULTGen627171 = 20


# Default value of the field path 'Redis timeout'
TIMEOUT_DEFAULT = 5


# Default value of the field path 'Grid unit'
UNIT_DEFAULT = "m"


# Default value of the field path 'Server wmts_path'
WMTS_PATH_DEFAULT = "wmts"


# pattern: ^[a-zA-Z0-9_\-\+~\.]+$
_GenerateItem = str


# The header value
_HeadersAdditionalproperties = str


# Default value of the field path 'Layer Mapnik layers'
_LAYER_MAPNIK_LAYERS_DEFAULT = "__all__"


# Default value of the field path 'Layer Mapnik meta_buffer'
_LAYER_MAPNIK_META_BUFFER_DEFAULT = 0


# Default value of the field path 'Layer Mapnik meta_size'
_LAYER_MAPNIK_META_SIZE_DEFAULT = 1


# Default value of the field path 'Layer WMS meta_buffer'
_LAYER_WMS_META_BUFFER_DEFAULT = 128


# Default value of the field path 'Layer WMS meta_size'
_LAYER_WMS_META_SIZE_DEFAULT = 5


class _LayerDimensionsItem(TypedDict, total=False):
    name: "LayerDimensionName"
    generate: List["_GenerateItem"]
    values: List["_ValuesItem"]
    default: str


class _LayerGeometriesItem(TypedDict, total=False):
    connection: str
    sql: str
    min_resolution: Union[int, float]
    max_resolution: Union[int, float]


class _LayerLegendsItem(TypedDict, total=False):
    mime_type: str
    href: str
    width: str
    height: str
    min_scale: str
    max_scale: str
    min_resolution: str
    max_resolution: str


# The Mapnik layer fields
_LayersFieldsAdditionalproperties = List[str]


# The parameter value
_ParametersAdditionalproperties = str


class _PredefinedCommandsItem(TypedDict, total=False):
    command: str
    name: str


class _ProcessCommandItem(TypedDict, total=False):
    cmd: str
    need_out: bool
    arg: "Argument"


# A sentinel (main configuration)
#
# additionalItems: False
_SentinelsItem = Tuple["SentinelHost", "SentinelPort"]


# pattern: ^[a-zA-Z0-9_\-\+~\.]+$
_ValuesItem = str
