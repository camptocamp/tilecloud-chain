# TileCloud Chain

The goal of TileCloud Chain is to provide tools around tile generation on a chain like:

Source: WMS, Mapnik.

Optionally using an SQS queue, AWS host, SNS topic.

Destination in WMTS layout, on S3, on Berkeley DB (`bsddb`), on MBTiles, or on local filesystem.

Features:

-   Generate tiles.
-   Drop empty tiles.
-   Drop tiles outside a geometry or a bbox.
-   Use MetaTiles.
-   Generate the legend images.
-   Generate GetCapabilities.
-   Generate OpenLayers example page.
-   Generate the Apache configuration.
-   Obtain the hash of an empty tile.
-   In the future, measure tile generation speed.
-   Calculate cost and generation time.
-   In the future, manage the AWS hosts that generate tiles.
-   Delete empty tiles.
-   Copy files between caches.
-   Be able to use an SQS queue to dispatch the generation.
-   Post processing the generated tiles.
-   ...

Legacy features:

-   bsddb support
-   sqlite (mbtiles) support
-   mapnik support (should be updated for Python3)
-   mapcache (replaced by internal mapcache)

## Get it

### With Docker

```bash
# Login to docker hub
docker login
docker pull camptocamp/tilecloud-chain

# Initialize the project
docker run -ti \
     --volume .:/project \
     camptocamp/tilecloud-chain \
     pcreate -s tilecloud_chain .

# Run the commands
DOCKER_ADRS=`ifconfig docker0 | head -n 2 | tail -n 1 | awk -F : '{print $2}' | awk '{print $1}'`
docker run -ti \
     --volume .:/project \
     --add-host=db:${DOCKER_ADRS} \
     --add-host=mapserver:${DOCKER_ADRS} \
     --env=USER_NAME=`whoami` \
     --env=USER_ID=`id -u` \
     --env=GROUP_ID=`id -g` \
     --env=UMASK=`umask` \
     camptocamp/tilecloud-chain \
     run <a command>
```

To share the home folder you should add the arguments:

```bash
--volume=${HOME}:${HOME} \
--env=HOME=${HOME} \
```

The image also contains some tools needed to render OSM data like: `fonts-dejavu`, `node-carto`.

### With pip

Requirements:

    pg_config and a build environment.

Install:

    pip install tilecloud-chain
    pcreate -s tilecloud_chain .

Edit your layers configuration in `./tilegeneration/config.yaml`.

[Default configuration
file](https://github.com/camptocamp/tilecloud-chain/blob/master/tilecloud_chain/scaffolds/create/tilegeneration/config.yaml.mako_tmpl).

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

```
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
