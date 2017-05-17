# -*- coding: utf-8 -*-

import logging
import psycopg2
import time

logger = logging.getLogger(__name__)


class DatabaseLoggerCommon(object):  # pragma: no cover
    def __init__(self, config, daemon):
        db_params = config['database']
        while True:
            try:
                self.connection = psycopg2.connect(
                    dbname=db_params['dbname'],
                    host=db_params.get('host'),
                    port=db_params.get('port')
                )
                break
            except psycopg2.OperationalError as e:
                if daemon:
                    logger.warn("Failed connecting to the database. Will try again in 1s")
                    time.sleep(1)
                else:
                    exit("Cannot connect to the database: " + str(e))
        if '.' in db_params['table']:
            schema, table = db_params['table'].split('.')
        else:
            schema = 'public'
            table = db_params['table']

        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname=%s AND tablename=%s)",
                (schema, table)
            )
            schema = psycopg2.extensions.quote_ident(schema, self.connection)
            table = psycopg2.extensions.quote_ident(table, self.connection)

            if not cursor.fetchone()[0]:
                try:
                    cursor.execute(
                        'CREATE TABLE {}.{} ('
                        '  id BIGSERIAL PRIMARY KEY,'
                        '  layer CHARACTER VARYING(80) NOT NULL,'
                        '  run INTEGER NOT NULL,'
                        '  action CHARACTER VARYING(7) NOT NULL,'
                        '  tile TEXT NOT NULL,'
                        '  UNIQUE (layer, run, tile))'.format(schema, table)
                    )
                    self.connection.commit()
                except psycopg2.DatabaseError:
                    logging.error('Unable to create table %s.%s', schema, table, exc_info=1)
                    exit(1)
            else:
                try:
                    cursor.execute(
                        'INSERT INTO {}.{}(layer, run, action, tile) '
                        'VALUES (%s, %s, %s, %s)'.format(schema, table),
                        ('test_layer', -1, 'test', '-1x-1')
                    )
                except psycopg2.DatabaseError:
                    logging.error('Unable to insert logging data into %s.%s',
                                  schema, table, exc_info=1)
                    exit(1)
                finally:
                    self.connection.rollback()

        self.full_table = '{}.{}'.format(schema, table)


class DatabaseLoggerInit(DatabaseLoggerCommon):  # pragma: no cover
    def __init__(self, config, daemon):
        super(DatabaseLoggerInit, self).__init__(config, daemon)

        with self.connection.cursor() as cursor:
            cursor.execute('SELECT COALESCE(MAX(run), 0) + 1 FROM {}'.format(self.full_table))
            self.run, = cursor.fetchone()

    def __call__(self, tile):
        tile.metadata['run'] = self.run
        return tile


class DatabaseLogger(DatabaseLoggerCommon):  # pragma: no cover
    def __call__(self, tile):
        if tile is None:
            logger.warn("The tile is None")
            return None

        if tile.error:
            action = 'error'
        elif tile.data:
            action = 'create'
        else:
            action = 'delete'

        logger.warn("TEST: " + action)

        layer = tile.metadata.get('layer', '- No layer -')
        run = tile.metadata.get('run', -1)

        with self.connection.cursor() as cursor:
            try:
                cursor.execute(
                    'INSERT INTO {} (layer, run, action, tile)'
                    'VALUES (%(layer)s, %(run)s, %(action)s::varchar(7), %(tile)s)'
                    'RETURNING run'.format(self.full_table),
                    {'layer': layer, 'action': action, 'tile': str(tile.tilecoord), 'run': run}
                )
                self.run, = cursor.fetchone()
            except psycopg2.IntegrityError:
                self.connection.rollback()
                cursor.execute(
                    'UPDATE {} SET action = %(action)s '
                    'WHERE layer = %(layer)s AND run = %(run)s AND tile = %(tile)s'.format(self.full_table),
                    {'layer': layer, 'action': action, 'tile': str(tile.tilecoord), 'run': run}
                )

            self.connection.commit()

        return tile
