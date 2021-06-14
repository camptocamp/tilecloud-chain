"""
Automatically generated file from a JSON schema.
"""


from typing import Any, Dict, List, Literal, Tuple, TypedDict, Union

# Address
#
# The address
Address = TypedDict(
    "Address",
    {
        # Delivery
        #
        # The delivery
        "delivery": str,
        # City
        #
        # The city
        "city": str,
        # Area
        #
        # The area
        "area": str,
        # Postal code
        #
        # The postal code
        "postal_code": int,
        # Country
        #
        # The country
        "country": str,
        # Email
        #
        # The email
        "email": str,
    },
    total=False,
)


# Apache
#
# Configuration used to generate the Apache configuration (deprecated)
Apache = TypedDict(
    "Apache",
    {
        # default: /tiles
        "location": str,
        # default: apache/tiles.conf
        "config_file": str,
        # default: 8
        "expires": int,
        "headers": "Headers",
    },
    total=False,
)


# Argument
#
# Used to build the %(args)
Argument = TypedDict(
    "Argument",
    {
        # Properties
        #
        # The arguments used by default
        "default": str,
        # Verbose
        #
        # The arguments used on verbose mode
        "verbose": str,
        # Debug
        #
        # The arguments used on debug mode
        "debug": str,
        # Quiet
        #
        # The arguments used on quiet mode
        "quiet": str,
    },
    total=False,
)


# AWS region
#
# The region, default to 'eu-west-1'
#
# pattern: ^(eu|us|ap|sa)-(north|south|east|west|central)(east|west)?-[1-3]$
# default: eu-west-1
AwsRegion = str


# Cache
#
# The tiles cache definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches
Cache = Union["CacheFilesystem", "CacheS3", "CacheMbtiles", "CacheBsddb"]


# Cache BSDDB
#
# WARNING: The required are not correctly taken in account,
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
#
# WARNING: the Normally the types should be mised each other instead of Union.
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
CacheBsddb = Union[Dict[str, str], "CacheBsddbTyped"]


CacheBsddbTyped = TypedDict(
    "CacheBsddbTyped",
    {
        "type": Literal["bsddb"],
        "wmtscapabilities_file": "CacheWmstCapabilitiesFile",
        "http_url": "CacheHttpUrl",
        "hosts": "CacheHost",
        "http_urls": "CacheHttpUrls",
        "folder": "CacheFolder",
    },
    total=False,
)


# Cache filesystem
#
# WARNING: The required are not correctly taken in account,
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
#
# WARNING: the Normally the types should be mised each other instead of Union.
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
CacheFilesystem = Union[Dict[str, str], "CacheFilesystemTyped"]


CacheFilesystemTyped = TypedDict(
    "CacheFilesystemTyped",
    {
        "type": Literal["filesystem"],
        "wmtscapabilities_file": "CacheWmstCapabilitiesFile",
        "http_url": "CacheHttpUrl",
        "hosts": "CacheHost",
        "http_urls": "CacheHttpUrls",
        "folder": "CacheFolder",
    },
    total=False,
)


# Cache folder
#
# The root folder of the cache, default to ''
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
# WARNING: the Normally the types should be mised each other instead of Union.
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
CacheMbtiles = Union[Dict[str, str], "CacheMbtilesTyped"]


CacheMbtilesTyped = TypedDict(
    "CacheMbtilesTyped",
    {
        "type": Literal["mbtiles"],
        "wmtscapabilities_file": "CacheWmstCapabilitiesFile",
        "http_url": "CacheHttpUrl",
        "hosts": "CacheHost",
        "http_urls": "CacheHttpUrls",
        "folder": "CacheFolder",
    },
    total=False,
)


# Cache S3
#
# WARNING: The required are not correctly taken in account,
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
#
# WARNING: the Normally the types should be mised each other instead of Union.
# See: https://github.com/camptocamp/jsonschema-gentypes/issues/7
CacheS3 = Union[Dict[str, str], "CacheS3Typed"]


CacheS3Typed = TypedDict(
    "CacheS3Typed",
    {
        "type": Literal["s3"],
        "wmtscapabilities_file": "CacheWmstCapabilitiesFile",
        "http_url": "CacheHttpUrl",
        "hosts": "CacheHost",
        "http_urls": "CacheHttpUrls",
        # Tiles URL
        #
        # The template tiles URL on S3, the argument can be region, bucket and folder (default is 'http://s3-{region}.amazonaws.com/{bucket}/{folder}')
        "tiles_url": str,
        # Host
        #
        # The S3 host, default to 's3-eu-west-1.amazonaws.com'
        #
        # default: s3-eu-west-1.amazonaws.com
        "host": str,
        # Bucket
        #
        # The S3 bucker name
        #
        # required
        "bucket": str,
        "region": "AwsRegion",
        # Cache control
        #
        # The Cache-Control used to store tiles on S3
        "cache_control": str,
        "folder": "CacheFolder",
    },
    total=False,
)


# Cache WMST capabilities file
#
# The generated WMTS capabilities file name (by 'default 1.0.0/WMTSCapabilities.xml')
CacheWmstCapabilitiesFile = str


# CloudFront cost
#
# The CloudFront cost
CloudfrontCost = TypedDict(
    "CloudfrontCost",
    {
        # Get
        #
        # The cost of get in $ per 10 000 requests
        #
        # default: 0.009
        "get": Union[int, float],
        # Download
        #
        # The cost of download in $ per Gio
        #
        # default: 0.12
        "download": Union[int, float],
    },
    total=False,
)


# TileCloud-chain configuration
Configuration = TypedDict(
    "Configuration",
    {
        # Defaults
        #
        # Used to put YAML references
        "defaults": Dict[str, Any],
        # Grids
        #
        # The WMTS grid definitions by grid name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids
        #
        # propertyNames:
        #   pattern: ^[a-zA-Z0-9_\-~\.]+$
        #
        # required
        "grids": Dict[str, "Grid"],
        # Caches
        #
        # The tiles caches definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-caches
        #
        # propertyNames:
        #   pattern: ^[a-zA-Z0-9_\-~\.]+$
        #
        # required
        "caches": Dict[str, "Cache"],
        # Layers
        #
        # The layers definitions by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-layers
        #
        # propertyNames:
        #   pattern: ^[a-zA-Z0-9_\-~\.]+$
        #
        # required
        "layers": Dict[str, "Layer"],
        # Process
        #
        # List of available commands by name, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#process
        "process": Dict[str, "ProcessCommand"],
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "generation": "Generation",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "sqs": "Sqs",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "sns": "Sns",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "redis": "Redis",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "apache": "Apache",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "mapcache": "Mapcache",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "openlayers": "Openlayers",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "server": "Server",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "cost": "Cost",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "metadata": "Metadata",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "provider": "Provider",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "logging": "Logging",
    },
    total=False,
)


# Contact
#
# The contact
Contact = TypedDict(
    "Contact",
    {
        # Name
        "name": str,
        # Position
        "position": str,
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "info": "Info",
    },
    total=False,
)


# Cost
#
# The configuration use to calculate the cast (unmaintained)
Cost = TypedDict(
    "Cost",
    {
        # Request per layers
        #
        # Tile request per hours, default to 10 000 000
        #
        # default: 10000000
        "request_per_layers": int,
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "s3": "S3Cost",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "cloudfront": "CloudfrontCost",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "sqs": "SqsCost",
    },
    total=False,
)


# Database
#
# The database
Database = TypedDict(
    "Database",
    {
        # Host
        #
        # The host
        "host": str,
        # Port
        #
        # The port, default is 5432
        #
        # default: 5432
        "port": int,
        # Database
        #
        # The database name
        #
        # required
        "dbname": str,
        # Table
        #
        # The table name
        #
        # required
        "table": str,
        # User
        #
        # The user name
        #
        # required
        "user": str,
        # Password
        #
        # The password
        #
        # required
        "password": str,
    },
    total=False,
)


# Generation
#
# The configuration used for the generation
Generation = TypedDict(
    "Generation",
    {
        # Default cache
        #
        # The default cache name to be used, default do 'default'
        #
        # default: default
        "default_cache": str,
        # Default layers
        #
        # The default layers to be generated
        "default_layers": List[str],
        # Log format
        #
        # The logging format, default to '%(levelname)s:%(name)s:%(funcName)s:%(message)s'
        #
        # default: %(levelname)s:%(name)s:%(funcName)s:%(message)s
        "log_format": str,
        # Authorised user
        #
        # The authorised user to generate the tiles (used to avoid permission issue on generated tiles)
        "authorised_user": str,
        # Max consecutive errors
        #
        # The maximum number of consecutive errors, default to 10
        #
        # default: 10
        "maxconsecutive_errors": int,
        # Error file
        #
        # File name generated with the tiles in error, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#tiles-error-file
        "error_file": str,
        # Number process
        #
        # Number of process used to generate the tiles, default to 1
        #
        # default: 1
        "number_process": int,
    },
    total=False,
)


# Grid
#
# The WMTS grid definition, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-grids
Grid = TypedDict(
    "Grid",
    {
        # Resolution scale
        #
        # The scale used to build a FreeTileGrid typically '2'
        "resolution_scale": int,
        # Resolutions
        #
        # The resolutions in pixel per meter
        #
        # required
        "resolutions": List[Union[int, float]],
        # Bounding box
        #
        # The bounding box in meter
        #
        # minLength: 4
        # maxLength: 4
        #
        # required
        "bbox": List[Union[int, float]],
        # SRS
        #
        # The projection reference
        #
        # pattern: ^EPSG:[0-9]+$
        #
        # required
        "srs": str,
        # Proj4 literal
        #
        # The Proj4 definition
        "proj4_literal": str,
        # Unit
        #
        # The projection unit, default to 'm'
        #
        # default: m
        "unit": str,
        # Tile size
        #
        # The tile size in pixel, default to 256
        #
        # default: 256
        "tile_size": int,
        "matrix_identifier": "MatrixIdentifier",
    },
    total=False,
)


# Headers
#
# The headers that we send to the WMS backend
Headers = Dict[str, "_HeadersAdditionalproperties"]


# Info
#
# The information
Info = TypedDict(
    "Info",
    {
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "phone": "Phone",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "address": "Address",
    },
    total=False,
)


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
# The rules used to calculate the cost (unmaintained)
LayerCost = TypedDict(
    "LayerCost",
    {
        # tile only generation time
        #
        # The time to generate a tile without meta-tile
        #
        # default: 40
        "tileonly_generation_time": Union[int, float],
        # tile generation time
        #
        # The time to generate a tile from the meta-tile
        #
        # default: 30
        "tile_generation_time": Union[int, float],
        # Meta tile generation time
        #
        # The time to generate a meta-tile
        #
        # default: 30
        "metatile_generation_time": Union[int, float],
        # Tile size
        #
        # The tile mean size in bytes
        #
        # default: 20
        "tile_size": Union[int, float],
    },
    total=False,
)


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
LayerEmptyMetaTileDetection = TypedDict(
    "LayerEmptyMetaTileDetection",
    {
        # Size
        #
        # The meta-tile size
        #
        # required
        "size": int,
        # Hash
        #
        # The meta-tile hash
        #
        # required
        "hash": str,
    },
    total=False,
)


# Layer empty tile detection
#
# The rules used to detect the empty tiles, use `generate-tiles --get-hash` to get what we can use, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-hash
LayerEmptyTileDetection = TypedDict(
    "LayerEmptyTileDetection",
    {
        # Title
        #
        # The tile size
        #
        # required
        "size": int,
        # Hash
        #
        # The tile hash
        #
        # required
        "hash": str,
    },
    total=False,
)


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
LayerMapnik = TypedDict(
    "LayerMapnik",
    {
        "type": Literal["mapnik"],
        "title": "LayerTitle",
        # required
        #
        # required
        "grid": "LayerGrid",
        "bbox": "LayerBoundingBox",
        "min_resolution_seed": "LayerMinResolutionSeed",
        "px_buffer": "LayerPixelBuffer",
        "meta": "LayerMeta",
        "meta_size": "LayerMetaSize",
        "meta_buffer": "LayerMetaBuffer",
        # required
        "layers": "LayerLayers",
        # required
        #
        # required
        "wmts_style": "LayerWmtsStyle",
        # required
        #
        # required
        "mime_type": "LayerMimeType",
        # required
        #
        # required
        "extension": "LayerExtension",
        "dimensions": "LayerDimensions",
        "legends": "LayerLegends",
        "legend_mime": "LayerLegendMime",
        "legend_extension": "LayerLegendExtension",
        "pre_hash_post_process": "LayerPreHashPostProcess",
        "post_process": "LayerPostProcess",
        "geoms": "LayerGeometries",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "empty_tile_detection": "LayerEmptyTileDetection",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "empty_metatile_detection": "LayerEmptyMetaTileDetection",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "cost": "LayerCost",
        # MapFile
        #
        # The Mapnik map file
        "mapfile": str,
        # Data buffer
        #
        # The data buffer, default to 128
        "data_buffer": int,
        "output_format": "OutputFormat",
        # WMS URL
        #
        # A WMS fallback URL (deprecated)
        "wms_url": str,
        # Resolution
        #
        # The resolution, default to 4
        "resolution": int,
        # Layers fields
        #
        # The Mapnik layers fields
        "layers_fields": Dict[str, "_LayersFieldsAdditionalproperties"],
        # Drop empty UTFGrid
        #
        # Drop if the tile is empty, default to False
        "drop_empty_utfgrid": bool,
    },
    total=False,
)


# Layer meta
#
# Used meta-tiles, default to False, see see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#meta-tiles
#
# default: False
LayerMeta = bool


# Layer meta buffer
#
# The meta-tiles buffer in pixels, default to 128
#
# default: 128
LayerMetaBuffer = int


# Layer meta size
#
# The meta-tile size in tiles, default to 5
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
# The buffer in pixel used to calculate geometry intersection, default to 0
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
LayerWms = TypedDict(
    "LayerWms",
    {
        "type": Literal["wms"],
        "title": "LayerTitle",
        # required
        #
        # required
        "grid": "LayerGrid",
        "bbox": "LayerBoundingBox",
        "min_resolution_seed": "LayerMinResolutionSeed",
        "px_buffer": "LayerPixelBuffer",
        "meta": "LayerMeta",
        "meta_size": "LayerMetaSize",
        "meta_buffer": "LayerMetaBuffer",
        # required
        "layers": "LayerLayers",
        # required
        #
        # required
        "wmts_style": "LayerWmtsStyle",
        # required
        #
        # required
        "mime_type": "LayerMimeType",
        # required
        #
        # required
        "extension": "LayerExtension",
        "dimensions": "LayerDimensions",
        "legends": "LayerLegends",
        "legend_mime": "LayerLegendMime",
        "legend_extension": "LayerLegendExtension",
        "pre_hash_post_process": "LayerPreHashPostProcess",
        "post_process": "LayerPostProcess",
        "geoms": "LayerGeometries",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "empty_tile_detection": "LayerEmptyTileDetection",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "empty_metatile_detection": "LayerEmptyMetaTileDetection",
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "cost": "LayerCost",
        # URL
        #
        # The WMS service URL
        #
        # required
        "url": str,
        # Generate salt
        #
        # Should generate a salt to drop the cache, default to False
        "generate_salt": bool,
        # Query layers
        #
        # The layers use for query (To be used with the server)
        "query_layers": str,
        # Info formats
        #
        # The query info format
        "info_formats": List[str],
        # Parameters
        #
        # Additional parameters to the WMS query (like dimension)
        "params": Dict[str, "_ParametersAdditionalproperties"],
        "headers": "Headers",
        # Version
        #
        # The used WMS version (default to '1.1.1')
        "version": str,
    },
    total=False,
)


# Layer WMTS style
#
# The WMTS style
#
# pattern: ^[a-zA-Z0-9_\-\+~\.]+$
LayerWmtsStyle = str


# Logging
#
# The logging configuration to database, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#logging
Logging = TypedDict(
    "Logging",
    {
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        #
        # required
        "database": "Database",
    },
    total=False,
)


# MapCache
#
# Configuration used to generate the mapcache configuration (deprecated)
Mapcache = TypedDict(
    "Mapcache",
    {
        # default: apache/mapcache.xml
        "config_file": str,
        # default: localhost
        "memcache_host": str,
        # default: 11211
        "memcache_port": Union[Union[int, float], str],
        # default: /mapcache
        "location": str,
    },
    total=False,
)


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
Metadata = TypedDict(
    "Metadata",
    {
        # Title
        #
        # The title
        #
        # required
        "title": str,
        # Abstract
        #
        # The abstract
        "abstract": str,
        # Service type
        #
        # The service type, default is 'OGC WMTS'
        #
        # default: OGC WMTS
        "servicetype": str,
        # Keywords
        #
        # The keywords
        "keywords": List[str],
        # Fees
        #
        # The fees
        "fees": str,
        # Access constraints
        #
        # The access constraints
        "access_constraints": str,
    },
    total=False,
)


# OpenLayers
#
# Configuration used to generate the OpenLayers example page
Openlayers = TypedDict(
    "Openlayers",
    {
        # SRS
        #
        # The projection code
        #
        # pattern: ^EPSG:[0-9]+$
        # default: EPSG:2056
        "srs": str,
        # Center x
        #
        # The center easting
        #
        # default: 2600000
        "center_x": Union[int, float],
        # Center y
        #
        # The center northing
        #
        # default: 1200000
        "center_y": Union[int, float],
    },
    total=False,
)


# Output format
#
# The Mapnik output format, default to 'png'
OutputFormat = Union[Literal["png"], Literal["png256"], Literal["jpeg"], Literal["grid"]]
# The values for the enum
OUTPUTFORMAT_PNG: Literal["png"] = "png"
OUTPUTFORMAT_PNG256: Literal["png256"] = "png256"
OUTPUTFORMAT_JPEG: Literal["jpeg"] = "jpeg"
OUTPUTFORMAT_GRID: Literal["grid"] = "grid"


# Phone
#
# The phone
Phone = TypedDict(
    "Phone",
    {
        # Voice
        #
        # The voice number
        "voice": str,
        # Fax
        #
        # The fax number
        "fax": str,
    },
    total=False,
)


# Process command
#
# A command
ProcessCommand = List["_ProcessCommandItem"]


# Provider
#
# The provider
Provider = TypedDict(
    "Provider",
    {
        # Name
        "name": str,
        # URL
        #
        # The public URL
        "url": str,
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "contact": "Contact",
    },
    total=False,
)


# Redis
#
# The Redis configuration
Redis = TypedDict(
    "Redis",
    {
        # URL
        #
        # The server URL
        #
        # pattern: ^redis://[^:]+:[^:]+$
        "url": str,
        # Sentinels
        #
        # The sentinels
        "sentinels": List["_SentinelsItem"],
        # The Redis connection arguments
        "connection_kwargs": Dict[str, Any],
        # The Redis sentinel arguments
        "sentinel_kwargs": Dict[str, Any],
        # Service name
        #
        # The service name, default to 'mymaster'
        #
        # default: mymaster
        "service_name": str,
        # Socket timeout
        #
        # The socket timeout
        "socket_timeout": int,
        # Database
        "db": int,
        # Queue
        #
        # The queue name
        #
        # default: tilecloud
        "queue": str,
        # Timeout
        #
        # The timeout, default to 5
        #
        # default: 5
        "timeout": int,
        # Pending timeout
        #
        # The pending timeout, default to 300
        #
        # default: 300
        "pending_timeout": int,
        # Max retries
        #
        # The max retries, default to 5
        #
        # default: 5
        "max_retries": int,
        # Max errors age
        #
        # The max error age, default to 86400 (1 day)
        #
        # default: 86400
        "max_errors_age": int,
        # Max errors number
        #
        # The max error number, default to 100
        #
        # default: 100
        "max_errors_nb": int,
        # Prefix
        #
        # The prefix, default to 'tilecloud_cache'
        #
        # default: tilecloud_cache
        "prefix": str,
        # Expiration
        #
        # The meta-tile in queue expiration, default to 28800 (8 hours)
        #
        # default: 28800
        "expiration": int,
    },
    total=False,
)


# S3 cost
#
# The S3 cost
S3Cost = TypedDict(
    "S3Cost",
    {
        # Storage
        #
        # The storage cost in $ / Gio / month
        #
        # default: 0.125
        "storage": Union[int, float],
        # Put
        #
        # The cost of put in $ per 10 000 requests
        #
        # default: 0.01
        "put": Union[int, float],
        # Get
        #
        # The cost of get in $ per 10 000 requests
        #
        # default: 0.01
        "get": Union[int, float],
        # Download
        #
        # The cost of download in $ per Gio
        #
        # default: 0.12
        "download": Union[int, float],
    },
    total=False,
)


# Server
#
# Configuration used by the tile server, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#distribute-the-tiles
Server = TypedDict(
    "Server",
    {
        # Cache
        #
        # The used cache name
        "cache": str,
        # WMS Layers
        #
        # Layers available in the server, default to all layers
        "layers": List[str],
        # Geometries redirect
        #
        # Take care on the geometries, default to False
        #
        # default: False
        "geoms_redirect": bool,
        # Mapcache internal
        #
        # Use internal mapcache, default to False
        #
        # default: False
        "mapcache_internal": bool,
        # Mapcache base
        #
        # The base URL, default to 'http://localhost/' (deprecated)
        #
        # default: http://localhost/
        "mapcache_base": str,
        "mapcache_headers": "Headers",
        # Static allow extension
        #
        # The allowed extension of static files, defaults to [jpeg, png, xml, js, html, css]
        "static_allow_extension": List[str],
        # WMTS path
        #
        # The sub-path for the WMTS, default to 'wmts'
        #
        # default: wmts
        "wmts_path": str,
        # Static path
        #
        # The sub-path for the static files, default to 'static'
        #
        # default: static
        "static_path": str,
        # Admin path
        #
        # The sub-path for the admin, default to 'admin'
        #
        # default: admin
        "admin_path": str,
        # Expires
        #
        # The browser cache expiration, default to 8 (hours)
        #
        # default: 8
        "expires": int,
        # Predefined commands
        #
        # The predefined commands used to generate the tiles
        "predefined_commands": List["_PredefinedCommandsItem"],
        # Allowed commands
        #
        # The regular expression of authorised commands
        "allowed_commands": List[str],
    },
    total=False,
)


# SNS
#
# The Simple Notification Service configuration, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sns
Sns = TypedDict(
    "Sns",
    {
        # Topic
        #
        # The topic
        #
        # required
        "topic": str,
        "region": "AwsRegion",
    },
    total=False,
)


# SQS
#
# The Simple Queue Service configuration
Sqs = TypedDict(
    "Sqs",
    {
        # Queue
        #
        # The queue name, default to 'tilecloud'
        "queue": str,
        "region": "AwsRegion",
    },
    total=False,
)


# SQS cost
#
# The SQS cost, see https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst#configure-sqs
SqsCost = TypedDict(
    "SqsCost",
    {
        # Request
        #
        # The cost of request in $ per 1 000 000 requests
        #
        # default: 0.01
        "request": Union[int, float],
    },
    total=False,
)


# The sentinel host name
_Base = str


# The sentinel port
_BaseGen439467 = Union[str, int]


# pattern: ^[a-zA-Z0-9_\-\+~\.]+$
_GenerateItem = str


# The header value
_HeadersAdditionalproperties = str


_LayerDimensionsItem = TypedDict(
    "_LayerDimensionsItem",
    {
        # required
        "name": "LayerDimensionName",
        # Generate
        #
        # The values that should be generate
        #
        # required
        "generate": List["_GenerateItem"],
        # Values
        #
        # The values present in the capabilities
        #
        # required
        "values": List["_ValuesItem"],
        # Default
        #
        # The default value present in the capabilities
        #
        # pattern: ^[a-zA-Z0-9_\-\+~\.]+$
        #
        # required
        "default": str,
    },
    total=False,
)


_LayerGeometriesItem = TypedDict(
    "_LayerGeometriesItem",
    {
        # Connection
        #
        # The PostgreSQL connection string
        #
        # required
        "connection": str,
        # SQL
        #
        # The SQL query that get the geometry in geom e.g. 'the_geom AS geom FROM my_table'
        #
        # required
        "sql": str,
        # Min resolution
        #
        # The min resolution where the query is valid
        "min_resolution": Union[int, float],
        # Max resolution
        #
        # The max resolution where the query is valid
        "max_resolution": Union[int, float],
    },
    total=False,
)


_LayerLegendsItem = TypedDict(
    "_LayerLegendsItem",
    {
        # MIME type
        #
        # The mime type used in the WMS request
        #
        # pattern: ^[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+/[a-zA-Z0-9!#$%^&\*_\-\+{}\|'.`~]+$
        #
        # required
        "mime_type": str,
        # Href
        #
        # The URL of the legend image
        #
        # required
        "href": str,
        # Width
        #
        # The width of the legend image
        "width": str,
        # Height
        #
        # The height of the legend image
        "height": str,
        # Min scale
        #
        # The max scale of the legend image
        "min_scale": str,
        # Max scale
        #
        # The max scale of the legend image
        "max_scale": str,
        # Min resolution
        #
        # The max resolution of the legend image
        "min_resolution": str,
        # Max resolution
        #
        # The max resolution of the legend image
        "max_resolution": str,
    },
    total=False,
)


# The Mapnik layer fields
_LayersFieldsAdditionalproperties = List[str]


# The parameter value
_ParametersAdditionalproperties = str


_PredefinedCommandsItem = TypedDict(
    "_PredefinedCommandsItem",
    {
        # Command
        #
        # The command to run
        "command": str,
        # Name
        #
        # The name used in the admin interface
        "name": str,
    },
    total=False,
)


_ProcessCommandItem = TypedDict(
    "_ProcessCommandItem",
    {
        # Command
        #
        # The shell command, available parameters: %(in)s, %(out)s, %(args)s, %(x)s, %(y)s, %(z)s.
        #
        # required
        "cmd": str,
        # Need out
        #
        # The command will generate an output in a file, default to False
        #
        # default: False
        "need_out": bool,
        # WARNING: The required are not correctly taken in account,
        # See: https://github.com/camptocamp/jsonschema-gentypes/issues/6
        "arg": "Argument",
    },
    total=False,
)


# A sentinel
#
# additionalItems: False
_SentinelsItem = Tuple["_Base", "_BaseGen439467"]


# pattern: ^[a-zA-Z0-9_\-\+~\.]+$
_ValuesItem = str
