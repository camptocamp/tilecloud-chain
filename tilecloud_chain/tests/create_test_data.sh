createdb -E UTF8 -T template0 tests
psql -q -d tests -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql
psql -q -d tests -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql
#psql -q -d tests -c "CREATE EXTENSION postgis"
psql -q -d tests -c "ALTER USER postgres WITH PASSWORD 'postgres';"

psql -q -d tests -c "CREATE SCHEMA tests;"

psql -q -d tests -c "CREATE TABLE tests.point (gid serial Primary KEY, name varchar(10));"
psql -q -d tests -c "SELECT AddGeometryColumn('tests', 'point','the_geom',21781,'POINT',2);"

psql -q -d tests -c "CREATE TABLE tests.line (gid serial Primary KEY, name varchar(10));"
psql -q -d tests -c "SELECT AddGeometryColumn('tests', 'line','the_geom',21781,'LINESTRING',2);"

psql -q -d tests -c "CREATE TABLE tests.polygon (gid serial Primary KEY, name varchar(10));"
psql -q -d tests -c "SELECT AddGeometryColumn('tests', 'polygon','the_geom',21781,'POLYGON',2);"


psql -q -d tests -c "INSERT INTO tests.point VALUES (0, 'point1', ST_GeomFromText('POINT (600000 200000)', 21781));"
psql -q -d tests -c "INSERT INTO tests.point VALUES (1, 'point2', ST_GeomFromText('POINT (530000 150000)', 21781));"

psql -q -d tests -c "INSERT INTO tests.line VALUES (0, 'line1', ST_GeomFromText('LINESTRING (600000 200000,530000 150000)', 21781));"

psql -q -d tests -c "INSERT INTO tests.polygon VALUES (0, 'polygon1', ST_GeomFromText('POLYGON ((600000 200000,600000 150000,530000 150000, 530000 200000, 600000 200000))', 21781));"

createdb -E UTF8 -T template0 tests-deploy
psql -q -d tests-deploy -c "CREATE TABLE test (name varchar(10));"
psql -q -d tests-deploy -c "INSERT INTO test VALUES ('referance');"
