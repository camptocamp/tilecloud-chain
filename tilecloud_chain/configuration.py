"""
Automatically generated file from a JSON schema.
"""


from typing import Any, Dict, List, Literal, Tuple, TypedDict, Union

ADMIN_PATH_DEFAULT = "admin"
"""Default value of the field path 'Server admin_path'"""


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

    Used to build the %(args)
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


AwsRegion = str
"""
AWS region.

The region, default is 'eu-west-1'

pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
"""


CACHE_FOLDER_DEFAULT = ""
"""Default value of the field path 'Cache filesystem folder'"""


CENTER_X_DEFAULT = 2600000
"""Default value of the field path 'OpenLayers center_x'"""


CENTER_Y_DEFAULT = 1200000
"""Default value of the field path 'OpenLayers center_y'"""


CLOUDFRONT_DOWNLOAD_DEFAULT = 0.12
"""Default value of the field path 'CloudFront cost download'"""


CLOUDFRONT_GET_DEFAULT = 0.009
"""Default value of the field path 'CloudFront cost get'"""


COST_TILE_SIZE_DEFAULT = 20
"""Default value of the field path 'Layer cost tile_size'"""


Cache = Union["CacheFilesystem", "CacheS3", "CacheAzure", "CacheMbtiles", "CacheBsddb"]
"""
Cache.

The tiles cache definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches
"""


CacheAzure = Union[Dict[str, str], "CacheAzureTyped"]
"""
Cache Azure.

Azure Blob Storage

WARNING: The required are not correctly taken in account,
See: https://github.com/camptocamp/jsonschema-gentypes/issues/6

WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""


class CacheAzureTyped(TypedDict, total=False):
    type: Literal["azure"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    folder: "CacheFolder"
    container: str
    """
    Container.

    The Azure container name

    required
    """

    cache_control: str
    """
    Cache control.

    The Cache-Control used to store tiles on Azure
    """


CacheBsddb = Union[Dict[str, str], "CacheBsddbTyped"]
"""
Cache BSDDB.

WARNING: The required are not correctly taken in account,
See: https://github.com/camptocamp/jsonschema-gentypes/issues/6

WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""


class CacheBsddbTyped(TypedDict, total=False):
    type: Literal["bsddb"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    folder: "CacheFolder"


CacheFilesystem = Union[Dict[str, str], "CacheFilesystemTyped"]
"""
Cache filesystem.

WARNING: The required are not correctly taken in account,
See: https://github.com/camptocamp/jsonschema-gentypes/issues/6

WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""


class CacheFilesystemTyped(TypedDict, total=False):
    type: Literal["filesystem"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    folder: "CacheFolder"


CacheFolder = str
"""
Cache folder.

The root folder of the cache, default is ''

default: 
"""


CacheHost = List[str]
"""
Cache host.

The host used to build the HTTP URLs
"""


CacheHttpUrl = str
"""
Cache HTTP URL.

The HTTP URL %host will be replaces by one of the hosts
"""


CacheHttpUrls = List[str]
"""Cache HTTP URLs."""


CacheMbtiles = Union[Dict[str, str], "CacheMbtilesTyped"]
"""
Cache MBtiles.

WARNING: The required are not correctly taken in account,
See: https://github.com/camptocamp/jsonschema-gentypes/issues/6

WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""


class CacheMbtilesTyped(TypedDict, total=False):
    type: Literal["mbtiles"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    folder: "CacheFolder"


CacheS3 = Union[Dict[str, str], "CacheS3Typed"]
"""
Cache S3.

WARNING: The required are not correctly taken in account,
See: https://github.com/camptocamp/jsonschema-gentypes/issues/6

WARNING: Normally the types should be a mix of each other instead of Union.
See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
"""


class CacheS3Typed(TypedDict, total=False):
    type: Literal["s3"]
    wmtscapabilities_file: "CacheWmstCapabilitiesFile"
    http_url: "CacheHttpUrl"
    hosts: "CacheHost"
    http_urls: "CacheHttpUrls"
    tiles_url: str
    """
    Tiles URL.

    The template tiles URL on S3, the argument can be region, bucket and folder (default is 'http://s3-{region}.amazonaws.com/{bucket}/{folder}')
    """

    host: str
    """
    Host.

    The S3 host, default is 's3-eu-west-1.amazonaws.com'
    """

    bucket: str
    """
    Bucket.

    The S3 bucker name

    required
    """

    region: "AwsRegion"
    cache_control: str
    """
    Cache control.

    The Cache-Control used to store tiles on S3
    """

    folder: "CacheFolder"


CacheWmstCapabilitiesFile = str
"""
Cache WMST capabilities file.

The generated WMTS capabilities file name (by 'default 1.0.0/WMTSCapabilities.xml')
"""


class CloudfrontCost(TypedDict, total=False):
    """
    CloudFront cost.

    The CloudFront cost (main configuration)
    """

    get: Union[int, float]
    """
    CloudFront Get.

    The cost of get in $ per 10 000 requests (main configuration)

    default: 0.009
    """

    download: Union[int, float]
    """
    CloudFront Download.

    The cost of download in $ per Gio (main configuration)

    default: 0.12
    """


class Configuration(TypedDict, total=False):
    """TileCloud-chain configuration."""

    defaults: Dict[str, Any]
    """
    Defaults.

    Used to put YAML references
    """

    grids: Dict[str, "Grid"]
    r"""
    Grids.

    The WMTS grid definitions by grid name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids

    propertyNames:
      pattern: ^[a-zA-Z0-9_\-~\.]+$
    """

    caches: Dict[str, "Cache"]
    r"""
    Caches.

    The tiles caches definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches

    propertyNames:
      pattern: ^[a-zA-Z0-9_\-~\.]+$
    """

    layers: Dict[str, "Layer"]
    r"""
    Layers.

    The layers definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers

    propertyNames:
      pattern: ^[a-zA-Z0-9_\-~\.]+$
    """

    process: Dict[str, "ProcessCommand"]
    """
    Process.

    List of available commands by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#process
    """

    generation: "Generation"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    sqs: "Sqs"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    sns: "Sns"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    redis: "Redis"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    openlayers: "Openlayers"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    server: "Server"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    cost: "Cost"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    metadata: "Metadata"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    provider: "Provider"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    logging: "Logging"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    authentication: "Authentication"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """


class Contact(TypedDict, total=False):
    """
    Contact.

    The contact
    """

    name: str
    """Name."""

    position: str
    """Position."""

    info: "Info"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """


class Cost(TypedDict, total=False):
    """
    Cost.

    The configuration use to calculate the cast (unmaintained)
    """

    request_per_layers: int
    """
    Request per layers.

    Tile request per hours, default is 10 000 000

    default: 10000000
    """

    s3: "S3Cost"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    cloudfront: "CloudfrontCost"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    sqs: "SqsCost"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """


DEFAULT_CACHE_DEFAULT = "default"
"""Default value of the field path 'Generation default_cache'"""


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

    The port (main configuration), default is 5432

    default: 5432
    """

    dbname: str
    """
    Database.

    The database name (main configuration)

    required
    """

    table: str
    """
    Table.

    The table name (main configuration)

    required
    """

    user: str
    """
    User.

    The user name (main configuration)

    required
    """

    password: str
    """
    Password.

    The password (main configuration)

    required
    """


EXPIRATION_DEFAULT = 28800
"""Default value of the field path 'Redis expiration'"""


EXPIRES_DEFAULT = 8
"""Default value of the field path 'Server expires'"""


GEOMETRIES_REDIRECT_DEFAULT = False
"""Default value of the field path 'Server geoms_redirect'"""


GITHUB_ACCESS_DEFAULT = "pull"
"""Default value of the field path 'Authentication github_access_type'"""


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

    default_layers: List[str]
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

    The maximum number of consecutive errors (main configuration), default is 10

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

    Number of process used to generate the tiles (main configuration), default is 1

    default: 1
    """


GithubAccess = Union[Literal["push"], Literal["pull"], Literal["admin"]]
"""
GitHub access.

The kind of rights the user should have on the repository

default: pull
"""
GITHUBACCESS_PUSH: Literal["push"] = "push"
"""The values for the 'GitHub access' enum"""
GITHUBACCESS_PULL: Literal["pull"] = "pull"
"""The values for the 'GitHub access' enum"""
GITHUBACCESS_ADMIN: Literal["admin"] = "admin"
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

    resolutions: List[Union[int, float]]
    """
    Resolutions.

    The resolutions in pixel per meter

    required
    """

    bbox: List[Union[int, float]]
    """
    Bounding box.

    The bounding box in meter

    minLength: 4
    maxLength: 4

    required
    """

    srs: str
    """
    SRS.

    The projection reference

    pattern: ^EPSG:[0-9]+$

    required
    """

    proj4_literal: str
    """
    Proj4 literal.

    The Proj4 definition
    """

    unit: str
    """
    Unit.

    The projection unit, default is 'm'

    default: m
    """

    tile_size: int
    """
    Tile size.

    The tile size in pixel, default is 256

    default: 256
    """

    matrix_identifier: "MatrixIdentifier"


Headers = Dict[str, "_HeadersAdditionalproperties"]
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
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    address: "Address"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """


LAYER_META_BUFFER_DEFAULT = 128
"""Default value of the field path 'Layer WMS meta_buffer'"""


LAYER_META_DEFAULT = False
"""Default value of the field path 'Layer WMS meta'"""


LAYER_META_SIZE_DEFAULT = 5
"""Default value of the field path 'Layer WMS meta_size'"""


LAYER_PIXEL_BUFFER_DEFAULT = 0
"""Default value of the field path 'Layer WMS px_buffer'"""


Layer = Union["LayerWms", "LayerMapnik"]
"""
Layer.

The layer definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers
"""


LayerBoundingBox = List[Union[int, float]]
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

    tileonly_generation_time: Union[int, float]
    """
    tile only generation time.

    The time to generate a tile without meta-tile

    default: 40
    """

    tile_generation_time: Union[int, float]
    """
    tile generation time.

    The time to generate a tile from the meta-tile

    default: 30
    """

    metatile_generation_time: Union[int, float]
    """
    Meta tile generation time.

    The time to generate a meta-tile

    default: 30
    """

    tile_size: Union[int, float]
    """
    Cost tile size.

    The tile mean size in bytes

    default: 20
    """


LayerDimensionName = str
r"""
Layer dimension name.

The dimension name

pattern: ^(?!(?i)(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\-~\.]+$
"""


LayerDimensions = List["_LayerDimensionsItem"]
"""
layer dimensions.

The WMTS dimensions
"""


class LayerEmptyMetaTileDetection(TypedDict, total=False):
    """
    Layer empty meta-tile detection.

    The rules used to detect the empty meta-tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    size: int
    """
    Size.

    The meta-tile size

    required
    """

    hash: str
    """
    Hash.

    The meta-tile hash

    required
    """


class LayerEmptyTileDetection(TypedDict, total=False):
    """
    Layer empty tile detection.

    The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
    """

    size: int
    """
    Title.

    The tile size

    required
    """

    hash: str
    """
    Hash.

    The tile hash

    required
    """


LayerExtension = str
"""
Layer extension.

The layer extension
"""


LayerGeometries = List["_LayerGeometriesItem"]
"""
Layer geometries.

The geometries used to determine where we should create the tiles, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-geomsql
"""


LayerGrid = str
"""
Layer grid.

The used grid name
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

pattern: ^[a-zA-Z0-9]+$
"""


LayerLegendMime = str
r"""
Layer legend MIME.

The mime type used to store the generated legend

pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
"""


LayerLegends = List["_LayerLegendsItem"]
"""
Layer legends.

The provided legend
"""


class LayerMapnik(TypedDict, total=False):
    """Layer Mapnik."""

    type: Literal["mapnik"]
    title: "LayerTitle"
    grid: "LayerGrid"
    """
    required

    required
    """

    bbox: "LayerBoundingBox"
    min_resolution_seed: "LayerMinResolutionSeed"
    px_buffer: "LayerPixelBuffer"
    meta: "LayerMeta"
    meta_size: "LayerMetaSize"
    meta_buffer: "LayerMetaBuffer"
    layers: "LayerLayers"
    """required"""

    wmts_style: "LayerWmtsStyle"
    """
    required

    required
    """

    mime_type: "LayerMimeType"
    """
    required

    required
    """

    extension: "LayerExtension"
    """
    required

    required
    """

    dimensions: "LayerDimensions"
    legends: "LayerLegends"
    legend_mime: "LayerLegendMime"
    legend_extension: "LayerLegendExtension"
    pre_hash_post_process: "LayerPreHashPostProcess"
    post_process: "LayerPostProcess"
    geoms: "LayerGeometries"
    empty_tile_detection: "LayerEmptyTileDetection"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    empty_metatile_detection: "LayerEmptyMetaTileDetection"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    cost: "LayerCost"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    mapfile: str
    """
    MapFile.

    The Mapnik map file
    """

    data_buffer: int
    """
    Data buffer.

    The data buffer, default is 128
    """

    output_format: "OutputFormat"
    wms_url: str
    """
    WMS URL.

    A WMS fallback URL (deprecated)
    """

    resolution: int
    """
    Resolution.

    The resolution, default is 4
    """

    layers_fields: Dict[str, "_LayersFieldsAdditionalproperties"]
    """
    Layers fields.

    The Mapnik layers fields
    """

    drop_empty_utfgrid: bool
    """
    Drop empty UTFGrid.

    Drop if the tile is empty, default is False
    """


LayerMeta = bool
"""
Layer meta.

Use meta-tiles, default is False, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles

default: False
"""


LayerMetaBuffer = int
"""
Layer meta buffer.

The meta-tiles buffer in pixels, default is 128

default: 128
"""


LayerMetaSize = int
"""
Layer meta size.

The meta-tile size in tiles, default is 5

default: 5
"""


LayerMimeType = str
r"""
Layer MIME type.

The MIME type of the tiles

pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
"""


LayerMinResolutionSeed = Union[int, float]
"""
layer min resolution seed.

The minimum resolutions to pre-generate
"""


LayerPixelBuffer = int
"""
Layer pixel buffer.

The buffer in pixel used to calculate geometry intersection, default is 0

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


LayerTitle = str
"""
Layer title.

The title, use to generate the capabilities
"""


class LayerWms(TypedDict, total=False):
    """Layer WMS."""

    type: Literal["wms"]
    title: "LayerTitle"
    grid: "LayerGrid"
    """
    required

    required
    """

    bbox: "LayerBoundingBox"
    min_resolution_seed: "LayerMinResolutionSeed"
    px_buffer: "LayerPixelBuffer"
    meta: "LayerMeta"
    meta_size: "LayerMetaSize"
    meta_buffer: "LayerMetaBuffer"
    layers: "LayerLayers"
    """required"""

    wmts_style: "LayerWmtsStyle"
    """
    required

    required
    """

    mime_type: "LayerMimeType"
    """
    required

    required
    """

    extension: "LayerExtension"
    """
    required

    required
    """

    dimensions: "LayerDimensions"
    legends: "LayerLegends"
    legend_mime: "LayerLegendMime"
    legend_extension: "LayerLegendExtension"
    pre_hash_post_process: "LayerPreHashPostProcess"
    post_process: "LayerPostProcess"
    geoms: "LayerGeometries"
    empty_tile_detection: "LayerEmptyTileDetection"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    empty_metatile_detection: "LayerEmptyMetaTileDetection"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    cost: "LayerCost"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """

    url: str
    """
    URL.

    The WMS service URL

    required
    """

    generate_salt: bool
    """
    Generate salt.

    Should generate a salt to drop the cache, default is False
    """

    query_layers: str
    """
    Query layers.

    The layers use for query (To be used with the server)
    """

    info_formats: List[str]
    """
    Info formats.

    The query info format
    """

    params: Dict[str, "_ParametersAdditionalproperties"]
    """
    Parameters.

    Additional parameters to the WMS query (like dimension)
    """

    headers: "Headers"
    version: str
    """
    Version.

    The used WMS version (default is '1.1.1')
    """


LayerWmtsStyle = str
r"""
Layer WMTS style.

The WMTS style

pattern: ^[a-zA-Z0-9_\-\+~\.]+$
"""


class Logging(TypedDict, total=False):
    """
    Logging.

    The logging configuration to database, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#logging (main configuration)
    """

    database: "Database"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6

    required
    """


MAP_INITIAL_ZOOM_DEFAULT = 3
"""Default value of the field path 'OpenLayers zoom'"""


MATRIX_IDENTIFIER_DEFAULT = "zoom"
"""Default value of the field path 'Grid matrix_identifier'"""


MAX_CONSECUTIVE_ERRORS_DEFAULT = 10
"""Default value of the field path 'Generation maxconsecutive_errors'"""


MAX_ERRORS_AGE_DEFAULT = 86400
"""Default value of the field path 'Redis max_errors_age'"""


MAX_ERRORS_NUMBER_DEFAULT = 100
"""Default value of the field path 'Redis max_errors_nb'"""


MAX_RETRIES_DEFAULT = 5
"""Default value of the field path 'Redis max_retries'"""


META_TILE_GENERATION_TIME_DEFAULT = 30
"""Default value of the field path 'Layer cost metatile_generation_time'"""


MatrixIdentifier = Union[Literal["zoom"], Literal["resolution"]]
"""
Matrix identifier.

The identifier to use in the tiles URL, recommend to be resolution (default)

default: zoom
"""
MATRIXIDENTIFIER_ZOOM: Literal["zoom"] = "zoom"
"""The values for the 'Matrix identifier' enum"""
MATRIXIDENTIFIER_RESOLUTION: Literal["resolution"] = "resolution"
"""The values for the 'Matrix identifier' enum"""


class Metadata(TypedDict, total=False):
    """
    Metadata.

    The configuration of the WMTS capabilities metadata
    """

    title: str
    """
    Title.

    The title

    required
    """

    abstract: str
    """
    Abstract.

    The abstract
    """

    servicetype: str
    """
    Service type.

    The service type, default is 'OGC WMTS'

    default: OGC WMTS
    """

    keywords: List[str]
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
"""Default value of the field path 'Process command item need_out'"""


NUMBER_PROCESS_DEFAULT = 1
"""Default value of the field path 'Generation number_process'"""


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
    The proj4js definition.

    The proj4js definition, get it from https://epsg.io/

    default: +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs
    """

    center_x: Union[int, float]
    """
    Center x.

    The center easting

    default: 2600000
    """

    center_y: Union[int, float]
    """
    Center y.

    The center northing

    default: 1200000
    """

    zoom: Union[int, float]
    """
    Map initial zoom.

    The initial zoom

    default: 3
    """


OutputFormat = Union[Literal["png"], Literal["png256"], Literal["jpeg"], Literal["grid"]]
"""
Output format.

The Mapnik output format, default is 'png'
"""
OUTPUTFORMAT_PNG: Literal["png"] = "png"
"""The values for the 'Output format' enum"""
OUTPUTFORMAT_PNG256: Literal["png256"] = "png256"
"""The values for the 'Output format' enum"""
OUTPUTFORMAT_JPEG: Literal["jpeg"] = "jpeg"
"""The values for the 'Output format' enum"""
OUTPUTFORMAT_GRID: Literal["grid"] = "grid"
"""The values for the 'Output format' enum"""


PENDING_COUNT_DEFAULT = 10
"""Default value of the field path 'Redis pending_count'"""


PENDING_MAX_COUNT_DEFAULT = 10000
"""Default value of the field path 'Redis pending_max_count'"""


PENDING_TIMEOUT_DEFAULT = 300
"""Default value of the field path 'Redis pending_timeout'"""


PORT_DEFAULT = 5432
"""Default value of the field path 'Database port'"""


PREFIX_DEFAULT = "tilecloud_cache"
"""Default value of the field path 'Redis prefix'"""


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


ProcessCommand = List["_ProcessCommandItem"]
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
    """Name."""

    url: str
    """
    URL.

    The public URL
    """

    contact: "Contact"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """


QUEUE_DEFAULT = "tilecloud"
"""Default value of the field path 'Redis queue'"""


REQUEST_DEFAULT = 0.01
"""Default value of the field path 'SQS cost request'"""


REQUEST_PER_LAYERS_DEFAULT = 10000000
"""Default value of the field path 'Cost request_per_layers'"""


class Redis(TypedDict, total=False):
    """
    Redis.

    The Redis configuration (main configuration)
    """

    url: str
    """
    URL.

    The server URL (main configuration)

    pattern: ^redis://[^:]+:[^:]+$
    """

    sentinels: List["_SentinelsItem"]
    """
    Sentinels.

    The sentinels (main configuration)
    """

    connection_kwargs: Dict[str, Any]
    """The Redis connection arguments (main configuration)"""

    sentinel_kwargs: Dict[str, Any]
    """The Redis sentinel arguments (main configuration)"""

    service_name: str
    """
    Service name.

    The service name, default is 'mymaster' (main configuration)

    default: mymaster
    """

    socket_timeout: int
    """
    Socket timeout.

    The socket timeout (main configuration)
    """

    db: int
    """Database."""

    queue: str
    """
    Queue.

    The queue name (main configuration)

    default: tilecloud
    """

    timeout: int
    """
    Timeout.

    The timeout (main configuration), default is 5

    default: 5
    """

    pending_timeout: int
    """
    Pending timeout.

    The pending timeout (main configuration), default is 300

    default: 300
    """

    max_retries: int
    """
    Max retries.

    The max retries (main configuration), default is 5

    default: 5
    """

    max_errors_age: int
    """
    Max errors age.

    The max error age (main configuration), default is 86400 (1 day)

    default: 86400
    """

    max_errors_nb: int
    """
    Max errors number.

    The max error number (main configuration), default is 100

    default: 100
    """

    prefix: str
    """
    Prefix.

    The prefix (main configuration), default is 'tilecloud_cache'

    default: tilecloud_cache
    """

    expiration: int
    """
    Expiration.

    The meta-tile in queue expiration (main configuration), default is 28800 (8 hours)

    default: 28800
    """

    pending_count: int
    """
    Pending count.

    The pending count: the number of pending tiles get in one request (main configuration), default is 10

    default: 10
    """

    pending_max_count: int
    """
    Pending max count.

    The pending max count: the maximum number of pending tiles get in one pass (if not generating other tiles, every second) (main configuration), default is 10000

    default: 10000
    """


class S3Cost(TypedDict, total=False):
    """
    S3 cost.

    The S3 cost (main configuration)
    """

    storage: Union[int, float]
    """
    S3 Storage.

    The storage cost in $ / Gio / month (main configuration)

    default: 0.125
    """

    put: Union[int, float]
    """
    S3 Put.

    The cost of put in $ per 10 000 requests (main configuration)

    default: 0.01
    """

    get: Union[int, float]
    """
    S3 Get.

    The cost of get in $ per 10 000 requests (main configuration)

    default: 0.01
    """

    download: Union[int, float]
    """
    S3 Download.

    The cost of download in $ per Gio (main configuration)

    default: 0.12
    """


S3_DOWNLOAD_DEFAULT = 0.12
"""Default value of the field path 'S3 cost download'"""


S3_GET_DEFAULT = 0.01
"""Default value of the field path 'S3 cost get'"""


S3_PUT_DEFAULT = 0.01
"""Default value of the field path 'S3 cost put'"""


S3_STORAGE_DEFAULT = 0.125
"""Default value of the field path 'S3 cost storage'"""


SERVICE_NAME_DEFAULT = "mymaster"
"""Default value of the field path 'Redis service_name'"""


SERVICE_TYPE_DEFAULT = "OGC WMTS"
"""Default value of the field path 'Metadata servicetype'"""


SRS_DEFAULT = "EPSG:2056"
"""Default value of the field path 'OpenLayers srs'"""


STATIC_PATH_DEFAULT = "static"
"""Default value of the field path 'Server static_path'"""


SentinelHost = str
"""
Sentinel host.

The sentinel host name (main configuration)
"""


SentinelPort = Union[str, int]
"""
Sentinel port.

The sentinel port (main configuration)
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

    layers: List[str]
    """
    WMS Layers.

    Layers available in the server, default is all layers
    """

    geoms_redirect: bool
    """
    Geometries redirect.

    Take care on the geometries, default is False

    default: False
    """

    static_allow_extension: List[str]
    """
    Static allow extension.

    The allowed extension of static files, defaults to [jpeg, png, xml, js, html, css]
    """

    wmts_path: str
    """
    WMTS path.

    The sub-path for the WMTS (main configuration), default is 'wmts'

    default: wmts
    """

    static_path: str
    """
    Static path.

    The sub-path for the static files (main configuration), default is 'static'

    default: static
    """

    admin_path: str
    """
    Admin path.

    The sub-path for the admin (main configuration), default is 'admin'

    default: admin
    """

    expires: int
    """
    Expires.

    The browser cache expiration, default is 8 (hours)

    default: 8
    """

    predefined_commands: List["_PredefinedCommandsItem"]
    """
    Predefined commands.

    The predefined commands used to generate the tiles
    """

    allowed_commands: List[str]
    """
    Allowed commands.

    The allowed commands (main configuration)
    """

    allowed_arguments: List[str]
    """
    Allowed arguments.

    The allowed arguments (main configuration)
    """


class Sns(TypedDict, total=False):
    """
    SNS.

    The Simple Notification Service configuration, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sns
    """

    topic: str
    """
    Topic.

    The topic

    required
    """

    region: "AwsRegion"


class Sqs(TypedDict, total=False):
    """
    SQS.

    The Simple Queue Service configuration
    """

    queue: str
    """
    Queue.

    The queue name, default is 'tilecloud'
    """

    region: "AwsRegion"


class SqsCost(TypedDict, total=False):
    """
    SQS cost.

    The SQS cost, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sqs (main configuration)
    """

    request: Union[int, float]
    """
    Request.

    The cost of request in $ per 1 000 000 requests (main configuration)

    default: 0.01
    """


THE_PROJ4JS_DEFINITION_DEFAULT = "+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs"
"""Default value of the field path 'OpenLayers proj4js_def'"""


TILE_GENERATION_TIME_DEFAULT = 30
"""Default value of the field path 'Layer cost tile_generation_time'"""


TILE_ONLY_GENERATION_TIME_DEFAULT = 40
"""Default value of the field path 'Layer cost tileonly_generation_time'"""


TILE_SIZE_DEFAULT = 256
"""Default value of the field path 'Grid tile_size'"""


TIMEOUT_DEFAULT = 5
"""Default value of the field path 'Redis timeout'"""


UNIT_DEFAULT = "m"
"""Default value of the field path 'Grid unit'"""


WMTS_PATH_DEFAULT = "wmts"
"""Default value of the field path 'Server wmts_path'"""


_GenerateItem = str
r"""pattern: ^[a-zA-Z0-9_\-\+~\.]+$"""


_HeadersAdditionalproperties = str
"""The header value"""


_LAYER_MAPNIK_LAYERS_DEFAULT = "__all__"
"""Default value of the field path 'Layer Mapnik layers'"""


_LAYER_MAPNIK_META_BUFFER_DEFAULT = 0
"""Default value of the field path 'Layer Mapnik meta_buffer'"""


_LAYER_MAPNIK_META_SIZE_DEFAULT = 1
"""Default value of the field path 'Layer Mapnik meta_size'"""


_LAYER_WMS_META_BUFFER_DEFAULT = 128
"""Default value of the field path 'Layer WMS meta_buffer'"""


_LAYER_WMS_META_SIZE_DEFAULT = 5
"""Default value of the field path 'Layer WMS meta_size'"""


class _LayerDimensionsItem(TypedDict, total=False):
    name: "LayerDimensionName"
    """required"""

    generate: List["_GenerateItem"]
    """
    Generate.

    The values that should be generate

    required
    """

    values: List["_ValuesItem"]
    """
    Values.

    The values present in the capabilities

    required
    """

    default: str
    r"""
    Default.

    The default value present in the capabilities

    pattern: ^[a-zA-Z0-9_\-\+~\.]+$

    required
    """


class _LayerGeometriesItem(TypedDict, total=False):
    connection: str
    """
    Connection.

    The PostgreSQL connection string

    required
    """

    sql: str
    """
    SQL.

    The SQL query that get the geometry in geom e.g. 'the_geom AS geom FROM my_table'

    required
    """

    min_resolution: Union[int, float]
    """
    Min resolution.

    The min resolution where the query is valid
    """

    max_resolution: Union[int, float]
    """
    Max resolution.

    The max resolution where the query is valid
    """


class _LayerLegendsItem(TypedDict, total=False):
    mime_type: str
    r"""
    MIME type.

    The mime type used in the WMS request

    pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$

    required
    """

    href: str
    """
    Href.

    The URL of the legend image

    required
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


_LayersFieldsAdditionalproperties = List[str]
"""The Mapnik layer fields"""


_ParametersAdditionalproperties = str
"""The parameter value"""


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
    cmd: str
    """
    Command.

    The shell command, available parameters: %(in)s, %(out)s, %(args)s, %(x)s, %(y)s, %(z)s.

    required
    """

    need_out: bool
    """
    Need out.

    The command will generate an output in a file, default is False

    default: False
    """

    arg: "Argument"
    """
    WARNING: The required are not correctly taken in account,
    See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
    """


_SentinelsItem = Tuple["SentinelHost", "SentinelPort"]
"""
A sentinel (main configuration)

additionalItems: False
"""


_ValuesItem = str
r"""pattern: ^[a-zA-Z0-9_\-\+~\.]+$"""
