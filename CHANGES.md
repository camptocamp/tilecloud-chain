# Changelog

## Release 1.22

1. In the layer, the `legend_mime`, `legend_extension` and `legends` becomes deprecated,
   they are replaced by `legend.mime_type`, `legend.extension` and `legend.items`.

## Release 1.17

1. Change the validator and parser => duplicate key generate an error: on/off are no more considered as boolean.
2. The argument --layer is no more used when we use the parameter --tiles, we get the information from the
   tiles file.
3. Be able to mutualise the service.
4. Add Azure blob storage
5. Remove Apache and MapCache
6. Remove the `log_format` in the `generation` configuration, nor we use the logging configuration from the
   `development.ini` file.

## Release 1.16

1.  Change the config validator who is a little bit more strict.

## Release 1.4

1.  Add optional `metadata` section to the config file. See the scaffolds for example.

## Release 0.9

1.  Correct some error with slash.
2.  Better error handling.
3.  Be able to have one error file per layer.

## Release 0.8

1.  Correct some error with slash.
2.  Add `pre_hash_post_process` and `post_process`.
3.  Add copy command.

## Release 0.7

1.  Support of deferent geoms per layers, requires configuration changes, old version:

    > ```yaml
    > connection: user=www-data password=www-data dbname=<db> host=localhost
    > sql: <column> AS geom FROM <table>
    > ```
    >
    > to new version:
    >
    > ```yaml
    > connection: user=www-data password=www-data dbname=<db> host=localhost
    > geoms:
    >   - sql: <column> AS geom FROM <table>
    > ```
    >
    > More information in the **Configure geom/sql** chapter.

2.  Update from `optparse` to `argparse`, and some argument refactoring, use `--help` to see the new version.
3.  Add support of Blackbery DB (`bsddb`).
4.  The tile `server` is completely rewrite, now it support all cache, `REST` and `KVP` interface,
    `GetFeatureInfo` request, and it can be used as a pyramid view or as a `WSGI` server. More information in
    the **istribute the tiles** chapter.
5.  Add three strategy to bypass the proxy/cache: Use the headers `Cache-Control: no-cache, no-store`,
    `Pragma: no-cache` (default). Use localhost in the URL and the header `Host: <host_name>` (recommended).
    Add a `SALT` random argument (if the above don't work). More information in the **Proxy/cache issue**
    chapter.
6.  Improve the dimensions usage by adding it ti the WMS requests, And add a `--dimensions` argument of
    `generate_tiles` to change the dimensions values.
7.  Extract generate_cost and generate_amazon from generate_controler.
8.  Now we can creates legends, see the **Legends** chapter.
9.  Now the tiles generation display generation statistics at the ends.
10. The EC2 configuration is moved in a separate structure, see README for more information.

## Release 0.6

1.  Now the apache configuration can be generated with
    `.build/venv/bin/generate_controller --generate-apache-config`, it support `filesystem` `cache` and
    `MapCache`.
2.  Windows fixes.
3.  Use console rewrite (r) to log generated tiles coordinates.
4.  Now if no layers is specified in `generation:default_layers` we generate all layers by default.
5.  Now bbox to be floats.
6.  New `--get-bbox` option to get the bbox of a tile.
7.  Add coveralls support (<https://coveralls.io/r/camptocamp/tilecloud-chain>).
8.  Add an config option `generation:error_file` and a command option `--tiles` to store and regenerate
    errored tiles.

## Release 0.5

1.  SQS config change:

```yaml
layers:
  layer_name:
    sqs:
      # The region where the SQS queue is
      region: eu-west-1
      # The SQS queue name, it should already exists
      queue: the_name
```

2.  Add debug option (`--debug`), please use it to report issue.
3.  Now the `sql` request can return a set of geometries in a column names geom but the syntax change a little
    bit =&gt; `<column> AS geom FROM <table>`
