# TileCloud Chain

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

## Get it

Create the config file `tilegeneration/config.yaml` see as [example](https://github.com/camptocamp/tilecloud-chain/blob/master/example/tilegeneration/config.yaml).

### Support

Only the latest release is supported and version &lt; 1.11 contains security issues.

## From sources

Build it:

```bash
git submodule update --recursive
python3 -m venv .build/venv
.build/venv/bin/pip install -r requirements.txt
.build/venv/bin/pip install -e .
.build/venv/bin/pip install -r dev-requirements.txt
```

## Run prospector

```bash
.build/venv/bin/prospector
```

## Run the tests

Setup your environment:

```bash
touch tilecloud_chain/OpenLayers.js
docker build --tag camptocamp/tilecloud-chain .
docker-compose -p tilecloud up
```

To run the tests:

```bash
docker-compose -p tilecloud exec test python setup.py nosetests --logging-filter=tilecloud,tilecloud_chain --attr '!'nopy3
```

## Documentation

As documentation you can read the `https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/USAGE.rst`.

## VSCode

You can add that in your workspace configuration to use the JSON schema:

```json
{
  "yaml.schemas": {
    "../tilecloud-chain/tilecloud_chain/schema.json": [
      "tilecloud-chain/tilecloud_chain/tests/tilegeneration/*.yaml"
    ]
  }
}
```
