# TileCloud-chain

The goal of TileCloud Chain is to provide tools around tile generation on a chain like:

Source: WMS, Mapnik.

Optionally using an SQS queue, AWS host, SNS topic.

Destination in WMTS layout, on S3, on Berkeley DB (`bsddb`), on MBTiles, or on local filesystem.

Features:

- Generate tiles.
- Drop empty tiles.
- Drop tiles outside a geometry or a bbox.
- Use MetaTiles.
- Generate the legend images.
- Generate GetCapabilities.
- Generate OpenLayers example page.
- Obtain the hash of an empty tile.
- In the future, measure tile generation speed.
- Calculate cost and generation time.
- In the future, manage the AWS hosts that generate tiles.
- Delete empty tiles.
- Copy files between caches.
- Be able to use an SQS queue to dispatch the generation.
- Post processing the generated tiles.
- ...

Legacy features:

- bsddb support
- sqlite (mbtiles) support
- mapnik support (should be updated for Python3)

## Screenshot

Screenshot of the admin page with queue stored on PostgreSQL:

![TileCloud Chain](./admin-screenshot.png)

## Get it

Create the config file `tilegeneration/config.yaml` see as [example](https://github.com/camptocamp/tilecloud-chain/blob/master/example/tilegeneration/config.yaml).

### Support

Only the latest release is supported and version &lt; 1.11 contains security issues.

## From sources

Build it:

```bash
make build
```

## Run prospector

```bash
make prospector
```

## Run the tests

To run the tests:

```bash
make tests
```

## Documentation

As documentation you can read the [USAGE.rst](https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst)
and the [configuration reference](https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/CONFIG.md).

## Contributing

Install the pre-commit hooks:

```bash
pip install pre-commit
pre-commit install --allow-missing-config
```
