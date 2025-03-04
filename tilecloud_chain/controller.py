"""Generate the contextual file like the legends."""

import asyncio
import logging
import math
import os
import pkgutil
import sys
import time
from argparse import ArgumentParser
from copy import copy
from hashlib import sha1
from io import BytesIO, StringIO
from math import exp, log
from pathlib import Path
from typing import IO, Literal, cast
from urllib.parse import urlencode, urljoin

import botocore.exceptions
import PIL.ImageFile
import requests
import ruamel.yaml
import tilecloud.store.redis
import tilecloud.store.s3
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import ContentSettings
from bottle import jinja2_template
from PIL import Image
from prometheus_client import Summary
from tilecloud.lib.PIL_ import FORMAT_BY_CONTENT_TYPE

import tilecloud_chain.configuration
from tilecloud_chain import (
    DatedConfig,
    TileGeneration,
    add_common_options,
    configuration,
    get_azure_container_client,
    get_queue_store,
    get_tile_matrix_identifier,
)

_LOGGER = logging.getLogger(__name__)
_GET_STATUS_SUMMARY = Summary("tilecloud_chain_get_status", "Number of get_stats", ["type", "queue"])


def main(args: list[str] | None = None, out: IO[str] | None = None) -> None:
    """Generate the contextual file like the legends."""
    asyncio.run(_async_main(args, out))


async def _async_main(args: list[str] | None = None, out: IO[str] | None = None) -> None:
    """Generate the contextual file like the legends."""
    try:
        parser = ArgumentParser(
            description="Used to generate the contextual file like the capabilities, the legends, "
            "the OpenLayers example",
            prog=args[0] if args else sys.argv[0],
        )
        add_common_options(parser, tile_pyramid=False, no_geom=False, default_config_file=True)
        parser.add_argument(
            "--status",
            default=False,
            action="store_true",
            help="Display the SQS queue status and exit",
        )
        parser.add_argument(
            "--legends",
            "--generate-legend-images",
            default=False,
            action="store_true",
            dest="legends",
            help="Generate the legend images",
        )
        parser.add_argument(
            "--dump-config",
            default=False,
            action="store_true",
            help="Dump the used config with default values and exit",
        )

        options = parser.parse_args(args[1:] if args else sys.argv[1:])
        gene = TileGeneration(options.config, options, layer_name=options.layer, out=out)
        assert gene.config_file
        config = gene.get_config(gene.config_file)

        if options.status:
            await status(gene)
            sys.exit(0)

        if options.cache is None:
            options.cache = config.config["generation"].get(
                "default_cache",
                configuration.DEFAULT_CACHE_DEFAULT,
            )

        if options.dump_config:
            _validate_generate_wmts_capabilities(
                config.config["caches"][options.cache],
                options.cache,
                exit_=True,
            )
            yaml = ruamel.yaml.YAML()
            yaml_out = StringIO()
            yaml.dump(config.config, yaml_out)
            print(yaml_out.getvalue())
            sys.exit(0)

        if options.legends:
            _generate_legend_images(gene, out)

    except SystemExit:
        raise
    except:  # pylint: disable=bare-except
        _LOGGER.exception("Exit with exception")
        if os.environ.get("TESTS", "false").lower() == "true":
            raise
        sys.exit(1)


def _send(data: bytes | str, path: str, mime_type: str, cache: tilecloud_chain.configuration.Cache) -> None:
    if cache["type"] == "s3":
        cache_s3 = cast(tilecloud_chain.configuration.CacheS3, cache)
        client = tilecloud.store.s3.get_client(cache_s3.get("host"))
        key_name = Path(cache["folder"]) / path
        bucket = cache_s3["bucket"]
        client.put_object(
            ACL="public-read",
            Body=data,
            Key=str(key_name),
            Bucket=bucket,
            ContentEncoding="utf-8",
            ContentType=mime_type,
        )
    if cache["type"] == "azure":
        cache_azure = cast(tilecloud_chain.configuration.CacheAzure, cache)
        key_name = Path(cache["folder"]) / path
        container = get_azure_container_client(cache_azure["container"])
        blob = container.get_blob_client(str(key_name))
        blob.upload_blob(data, overwrite=True)

        blob.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(
                content_type=mime_type,
                content_encoding="utf-8",
                cache_control=cache_azure["cache_control"],
            ),
        )
    else:
        if isinstance(data, str):
            data = data.encode("utf-8")

        folder = Path(cache["folder"] or "")
        filename = folder / path
        filename.parent.mkdir(parents=True, exist_ok=True)
        with filename.open("wb") as f:
            f.write(data)


async def _get(path: str, cache: tilecloud_chain.configuration.Cache) -> bytes | None:
    if cache["type"] == "s3":
        cache_s3 = cast(tilecloud_chain.configuration.CacheS3, cache)
        client = tilecloud.store.s3.get_client(cache_s3.get("host"))
        key_name = Path(cache["folder"]) / path
        bucket = cache_s3["bucket"]
        try:
            response = client.get_object(Bucket=bucket, Key=str(key_name))
            return cast(bytes, response["Body"].read())
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise
    if cache["type"] == "azure":
        cache_azure = cast(tilecloud_chain.configuration.CacheAzure, cache)
        key_name = Path(cache["folder"]) / path
        try:
            blob = get_azure_container_client(container=cache_azure["container"]).get_blob_client(
                blob=str(key_name),
            )
            return await (await blob.download_blob()).readall()
        except ResourceNotFoundError:
            return None
    else:
        cache_filesystem = cast(tilecloud_chain.configuration.CacheFilesystem, cache)
        p = Path(cache_filesystem["folder"]) / path
        if not p.is_file():
            return None
        return p.read_bytes()


def _validate_generate_wmts_capabilities(
    cache: tilecloud_chain.configuration.Cache,
    cache_name: str,
    exit_: bool,
) -> bool:
    if "http_url" not in cache and "http_urls" not in cache:
        _LOGGER.error(
            "The attribute 'http_url' or 'http_urls' is required in the object cache[%s].",
            cache_name,
        )
        if exit_:
            sys.exit(1)
        return False
    return True


async def get_wmts_capabilities(
    gene: TileGeneration,
    cache_name: str,
    exit_: bool = False,
    config: DatedConfig | None = None,
) -> str | None:
    """Get the WMTS capabilities for a configuration file."""
    start = time.perf_counter()
    if config is None:
        assert gene.config_file
        config = gene.get_config(gene.config_file)

    cache = config.config["caches"][cache_name]
    if _validate_generate_wmts_capabilities(cache, cache_name, exit_):
        server = gene.get_main_config().config.get("server")

        base_urls = _get_base_urls(cache)
        await _fill_legend(gene, cache, server, base_urls, config=config)

        data = pkgutil.get_data("tilecloud_chain", "wmts_get_capabilities.jinja")
        assert data
        _LOGGER.debug("Get WMTS capabilities in %s", time.perf_counter() - start)
        return cast(
            str,
            jinja2_template(
                data.decode("utf-8"),
                layers=config.config.get("layers", {}),
                layer_legends=gene.layer_legends,
                grids=config.config["grids"],
                getcapabilities=urljoin(  # type: ignore[type-var]
                    base_urls[0],
                    (
                        server.get("wmts_path", "wmts") + "/1.0.0/WMTSCapabilities.xml"
                        if server is not None
                        else cache.get("wmtscapabilities_file", "1.0.0/WMTSCapabilities.xml")
                    ),
                ),
                base_urls=base_urls,
                base_url_postfix=(server.get("wmts_path", "wmts") + "/") if server is not None else "",
                get_tile_matrix_identifier=get_tile_matrix_identifier,
                server=server is not None,
                has_metadata="metadata" in config.config,
                metadata=config.config.get("metadata"),
                has_provider="provider" in config.config,
                provider=config.config.get("provider"),
                enumerate=enumerate,
                ceil=math.ceil,
                int=int,
                sorted=sorted,
                configuration=configuration,
            ),
        )
    return None


def _get_base_urls(cache: tilecloud_chain.configuration.Cache) -> list[str]:
    base_urls = []
    if "http_url" in cache:
        if "hosts" in cache:
            cc = copy(cache)
            for host in cache["hosts"]:
                cc["host"] = host  # type: ignore[typeddict-unknown-key]
                base_urls.append(cache["http_url"] % cc)
        else:
            base_urls = [cache["http_url"] % cache]
    if "http_urls" in cache:
        base_urls = [url % cache for url in cache["http_urls"]]
    return [url + "/" if url[-1] != "/" else url for url in base_urls]


async def _legend_metadata(
    cache: tilecloud_chain.configuration.Cache,
    layer: tilecloud_chain.configuration.Layer,
    base_url: str,
    path: str,
) -> tilecloud_chain.Legend | None:
    img = await _get(path, cache)
    if img is not None:
        new_legend: tilecloud_chain.Legend = {
            "mime_type": layer["legend_mime"],
            "href": str(Path(base_url) / path),
        }
        try:
            with Image.open(BytesIO(img)) as pil_img:
                new_legend["width"] = pil_img.size[0]
                new_legend["height"] = pil_img.size[1]
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.warning(
                "Unable to read legend image '%s', with '%s'",
                path,
                repr(img),
                exc_info=True,
            )
        return new_legend
    return None


async def _fill_legend(
    gene: TileGeneration,
    cache: tilecloud_chain.configuration.Cache,
    server: tilecloud_chain.configuration.Server | None,
    base_urls: list[str],
    config: DatedConfig | None = None,
) -> None:
    if config is None:
        assert gene.config_file
        config = gene.get_config(gene.config_file)

    start = time.perf_counter()
    legend_image_tasks = {}
    for layer_name, layer in config.config.get("layers", {}).items():
        if "legend_mime" in layer and "legend_extension" in layer and layer_name not in gene.layer_legends:
            for zoom, resolution in enumerate(config.config["grids"][layer["grid"]]["resolutions"]):
                path = Path(
                    "1.0.0",
                    layer_name,
                    layer["wmts_style"],
                    f"legend{zoom}.{layer['legend_extension']}",
                )
                legend_image_tasks[
                    asyncio.create_task(
                        _legend_metadata(
                            cache,
                            layer,
                            str(Path(base_urls[0]) / (server.get("static_path", "static") if server else "")),
                            str(path),
                        ),
                    )
                ] = (layer_name, resolution)

    asyncio.gather(*legend_image_tasks.keys())
    legend_image_metadata: dict[str, dict[float, tilecloud_chain.Legend | None]] = {}
    for task, values in legend_image_tasks.items():
        layer_name, resolution = values
        try:
            legend_image_metadata.setdefault(layer_name, {})[resolution] = task.result()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _LOGGER.warning(
                "Unable to get legend image for layer '%s', resolution '%s': %s",
                layer_name,
                resolution,
                exc,
            )

    _LOGGER.debug("Get %i legend images in %s", len(legend_image_tasks), time.perf_counter() - start)

    for layer_name, layer in config.config.get("layers", {}).items():
        previous_legend: tilecloud_chain.Legend | None = None
        previous_resolution = None
        if "legend_mime" in layer and "legend_extension" in layer and layer_name not in gene.layer_legends:
            gene.layer_legends[layer_name] = []
            legends = gene.layer_legends[layer_name]
            for _, resolution in enumerate(config.config["grids"][layer["grid"]]["resolutions"]):
                new_legend = legend_image_metadata.get(layer_name, {}).get(resolution)

                if new_legend is not None:
                    legends.append(new_legend)
                    if previous_legend is not None:
                        assert previous_resolution is not None
                        middle_res = exp((log(previous_resolution) + log(resolution)) / 2)
                        previous_legend["min_resolution"] = middle_res
                        new_legend["max_resolution"] = middle_res
                    previous_legend = new_legend
                previous_resolution = resolution


def _get_legend_image(
    layer_name: str,
    wms_layer: str,
    resolution: float,
    url: str,
    session: requests.Session,
    main_mime_type: str,
    out: IO[str] | None = None,
) -> PIL.ImageFile.ImageFile | None:
    _LOGGER.debug(
        "Get legend image for layer '%s'-'%s', resolution '%s': %s",
        layer_name,
        wms_layer,
        resolution,
        url,
    )
    try:
        response = session.get(url)
    except Exception as e:  # pylint: disable=broad-exception-caught
        if out is not None:
            print(
                "\n".join(
                    [
                        f"Unable to get legend image for layer '{layer_name}'-'{wms_layer}', resolution '{resolution}'",
                        url,
                        str(e),
                    ],
                ),
                file=out,
            )
        _LOGGER.debug(
            "Unable to get legend image for layer '%s'-'%s', resolution '%s'",
            layer_name,
            wms_layer,
            resolution,
            exc_info=True,
        )
        return None
    if response.status_code != 200:
        if out is not None:
            print(
                "\n".join(
                    [
                        f"Unable to get legend image for layer '{layer_name}'-'{wms_layer}', resolution '{resolution}'",
                        url,
                        f"status code: {response.status_code}: {response.reason}",
                        response.text,
                    ],
                ),
                file=out,
            )
        _LOGGER.debug(
            "Unable to get legend image for layer '%s'-'%s', resolution '%s': %s",
            layer_name,
            wms_layer,
            resolution,
            response.text,
        )
        return None
    if not response.headers["Content-Type"].startswith(main_mime_type):
        if out is not None:
            print(
                "\n".join(
                    [
                        f"Unable to get legend image for layer '{layer_name}'-'{wms_layer}', resolution '{resolution}'",
                        url,
                        f"Content-Type: {response.headers['Content-Type']}",
                        response.text,
                    ],
                ),
                file=out,
            )
        _LOGGER.debug(
            "Unable to get legend image for layer '%s'-'%s', resolution '%s', content-type: %s: %s",
            layer_name,
            wms_layer,
            resolution,
            response.headers["Content-Type"],
            response.text,
        )
        return None
    try:
        return Image.open(BytesIO(response.content))
    except Exception:  # pylint: disable=broad-exception-caught
        if out is not None:
            print(
                "\n".join(
                    [
                        f"Unable to read legend image for layer '{layer_name}'-'{wms_layer}', resolution '{resolution}'",
                        url,
                        response.text,
                    ],
                ),
                file=out,
            )
        _LOGGER.debug(
            "Unable to read legend image for layer '%s'-'%s', resolution '%s': %s",
            layer_name,
            wms_layer,
            resolution,
            response.text,
            exc_info=True,
        )
        return None


def _generate_legend_images(gene: TileGeneration, out: IO[str] | None = None) -> None:
    assert gene.config_file
    config = gene.get_config(gene.config_file)
    cache = config.config["caches"][gene.options.cache]

    for layer_name, layer in config.config.get("layers", {}).items():
        if "legend_mime" in layer and "legend_extension" in layer and layer["type"] == "wms":
            session = requests.session()
            session.headers.update(layer["headers"])
            previous_hash = None
            for zoom, resolution in enumerate(config.config["grids"][layer["grid"]]["resolutions"]):
                legends = []
                for wms_layer in layer.get("layers", "").split(","):
                    url = (
                        layer["url"]
                        + "?"
                        + urlencode(
                            {
                                "SERVICE": "WMS",
                                "VERSION": layer.get("version", "1.0.0"),
                                "REQUEST": "GetLegendGraphic",
                                "LAYER": wms_layer,
                                "FORMAT": layer["legend_mime"],
                                "TRANSPARENT": "TRUE" if layer["legend_mime"] == "image/png" else "FALSE",
                                "STYLE": layer["wmts_style"],
                                "SCALE": resolution / 0.00028,
                            },
                        )
                    )
                    legend_image = _get_legend_image(
                        layer_name,
                        wms_layer,
                        resolution,
                        url,
                        session,
                        layer["legend_mime"].split("/")[0],
                        out,
                    )
                    if legend_image is not None:
                        legends.append(legend_image)

                width = max(1, max(i.size[0] for i in legends) if legends else 0)
                height = max(1, sum(i.size[1] for i in legends) if legends else 0)
                image = Image.new("RGBA", (width, height))
                y = 0
                for i in legends:
                    image.paste(i, (0, y))
                    y += i.size[1]
                string_io = BytesIO()
                image.save(string_io, FORMAT_BY_CONTENT_TYPE[layer["legend_mime"]])
                result = string_io.getvalue()
                new_hash = sha1(result).hexdigest()  # nosec # noqa: S324
                if new_hash != previous_hash:
                    previous_hash = new_hash
                    _send(
                        result,
                        f"1.0.0/{layer_name}/{layer['wmts_style']}/legend{zoom}.{layer['legend_extension']}",
                        layer["legend_mime"],
                        cache,
                    )


async def status(gene: TileGeneration) -> None:
    """Print th tilegeneration status."""
    print("\n".join(await get_status(gene)))


async def get_status(gene: TileGeneration) -> list[str]:
    """Get the tile generation status."""
    config = gene.get_main_config()
    store = await get_queue_store(config, daemon=False)
    type_: Literal["redis", "sqs"] = "redis" if "redis" in config.config else "sqs"
    conf = config.config[type_]
    with _GET_STATUS_SUMMARY.labels(type_, conf.get("queue", configuration.REDIS_QUEUE_DEFAULT)).time():
        status_ = store.get_status()
    return [name + ": " + str(value) for name, value in status_.items()]
