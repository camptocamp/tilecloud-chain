# TileCloud-chain

TileCloud Chain is a comprehensive toolset for managing tile generation workflows. It supports various source and destination formats, making it a versatile solution for map tile management.

## Sources

- Web Map Service (WMS)
- Mapnik rendering engine

## Destination Formats and Storage

- Web Map Tile Service (WMTS) layout
- Amazon S3 storage
- Azure Blob storage
- Local filesystem

## Key Features

- Tile generation with configurable parameters
- Automatic removal of empty tiles
- Geographic filtering (bbox and geometry-based)
- MetaTile support for efficient generation
- Legend image generation
- GetCapabilities document
- OpenLayers demo page
- Empty tile detection via hashing
- Cache synchronization
- Post-processing capabilities

## Legacy Support

Note: The following features are maintained for backward compatibility:

- Berkeley DB integration
- SQLite (MBTiles) support
- Mapnik rendering (Python 3 update pending)

## Visual Preview

The admin interface with PostgreSQL queue integration:

![TileCloud Chain Admin Interface](./admin-screenshot.png)

## Getting Started

Create a configuration file at `tilegeneration/config.yaml`.

Reference the [example configuration](https://github.com/camptocamp/tilecloud-chain/blob/master/example/tilegeneration/config.yaml).

## Support Policy

Only the latest release receives active support. Versions prior to 1.11 contain security vulnerabilities and should not be used.

## Development

### Building

```bash
make build
```

### Quality Assurance

```bash
make prospector
```

### Testing

```bash
make tests
```

## Generation Pipeline

The `generate-tiles` command supports four execution modes:

- `local`: generate tiles directly and store them in the target cache.
- `master`: prepare metatile jobs and push them to the queue store.
- `slave`: read jobs from the queue store, generate tiles, and store them.
- `--get-hash`: switch to hash mode to print metatile/tile hashes.

```mermaid
flowchart TD
    A["generate-tiles CLI"] --> B{"Mode"}

    B -->|local| L1["Build metatile stream"]
    B -->|master| M1["Build metatile stream"]
    B -->|slave| S1["Read metatiles from queue"]
    B -->|hash via --get-hash| H1["Build tile or metatile selection"]

    L1 --> C["Fetch source tile data"]
    M1 --> M2["Apply geom and local process filters"]
    S1 --> C
    H1 --> C

    C --> D["Split metatiles into tiles"]
    D --> E{"Hash handling"}

    E -->|hash mode| H2["Print hash values"]
    E -->|normal modes| F["Drop empty tiles/metatiles with configured hashes"]

    F --> G["Run post-process chain"]
    G --> I{"Mode output"}

    I -->|local| O1["Store tiles to cache (S3, local, etc.)"]
    I -->|slave| O2["Store tiles to cache and delete processed queue items"]
    I -->|master| O3["Push metatile jobs to queue (Redis, SQS, PostgreSQL)"]
    I -->|hash| O4["Console output only"]
```

## Documentation

- [Usage Guide](https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst)
- [Configuration Reference](https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/CONFIG.md)
- [Environment variables](https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/settings.py)

## Contributing

Set up pre-commit hooks:

```bash
pip install pre-commit
pre-commit install --allow-missing-config
```
