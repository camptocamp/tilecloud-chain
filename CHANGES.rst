Changelog
=========

-----------
Release 0.9
-----------

1. Correct some error with slash.

2. Better error handling.

3. Be able to have one error file per layer.

-----------
Release 0.8
-----------

1. Correct some error with slash.

2. Add ``pre_hash_post_process`` and ``post_process``.

3. Add copy command.

-----------
Release 0.7
-----------

1. Support of deferent geoms per layers, requires configuration changes, old version:

    .. code:: yaml

        connection: user=www-data password=www-data dbname=<db> host=localhost
        sql: <column> AS geom FROM <table>

    to new version:

    .. code:: yaml

        connection: user=www-data password=www-data dbname=<db> host=localhost
        geoms:
        -   sql: <column> AS geom FROM <table>

    More informations in the **Configure geom/sql** chapter.

2. Update from ``optparse`` to ``argparse``, and some argument refactoring, use ``--help`` to see the new version.

3. Add support of Blackbery DB (``bsddb``).

4. The tile ``server`` is completely rewrite, now it support all cache,
   ``REST`` and ``KVP`` interface, ``GetFeatureInfo`` request,
   and it can be used as a pyramid view or as a ``WSGI`` server.
   More informations in the **istribute the tiles** chapter.

5. Add three strategy to bypass the proxy/cache: Use the headers
   ``Cache-Control: no-cache, no-store``, ``Pragma: no-cache`` (default).
   Use localhost in the URL and the header ``Host: <host_name>`` (recommended).
   Add a ``SALT`` random argument (if the above don't work).
   More informations in the **Proxy/cache issue** chapter.

6. Improve the dimensions usage by adding it ti the WMS requests,
   And add a ``--dimensions`` argument of ``generate_tiles`` to change the dimensions values.

7. Extract generate_cost and generate_amazon from generate_controler.

8. Now we can creates legends, see the **Legends** chapter.

9. Now the tiles generation display generation statistics at the ends.

10. The EC2 configuration is moved in a separate structure, see README for more informations.


-----------
Release 0.6
-----------

1. Now the apache configuration can be generated with ``.build/venv/bin/generate_controller --generate-apache-config``,
   it support ``filesystem`` ``cache`` and ``MapCache``.

2. Windows fixes.

3. Use console rewrite (\r) to log generated tiles coordinates.

4. Now if no layers is specified in ``generation:default_layers`` we generate all layers by default.

5. Now bbox to be floats.

6. New ``--get-bbox`` option to get the bbox of a tile.

7. Add coveralls support (https://coveralls.io/r/camptocamp/tilecloud-chain).

8. Add an config option ``generation:error_file`` and a command option ``--tiles``
   to store and regenerate errored tiles.


-----------
Release 0.5
-----------

1. SQS config change:

.. code:: yaml

    layers:
        layer_name:
            sqs:
                # The region where the SQS queue is
                region: eu-west-1
                # The SQS queue name, it should already exists
                queue: the_name

2. Add debug option (``--debug``), please use it to report issue.

3. Now the ``sql`` request can return a set of geometries in a column names geom
   but the syntax change a little bit => ``<column> AS geom FROM <table>``
