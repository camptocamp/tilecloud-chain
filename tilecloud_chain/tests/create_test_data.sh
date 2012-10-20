createdb -E UTF8 -T template0 tests
psql -d tests -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql
psql -d tests -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql
#psql -d tests -c "CREATE EXTENSION postgis"
psql -d tests -c "ALTER USER postgres WITH PASSWORD 'postgres';"

psql -d tests -c "CREATE SCHEMA tests;"

psql -d tests -c "CREATE TABLE tests.point (gid serial Primary KEY);"
psql -d tests -c "SELECT AddGeometryColumn('tests', 'point','the_geom',21781,'POINT',2);"

psql -d tests -c "CREATE TABLE tests.line (gid serial Primary KEY);"
psql -d tests -c "SELECT AddGeometryColumn('tests', 'line','the_geom',21781,'LINESTRING',2);"

psql -d tests -c "CREATE TABLE tests.polygon (gid serial Primary KEY);"
psql -d tests -c "SELECT AddGeometryColumn('tests', 'polygon','the_geom',21781,'POLYGON',2);"


psql -d tests -c "INSERT INTO tests.point VALUES (0, ST_GeomFromText('POINT (600000 200000)', 21781));"
psql -d tests -c "INSERT INTO tests.point VALUES (1, ST_GeomFromText('POINT (350000 150000)', 21781));"

psql -d tests -c "INSERT INTO tests.line VALUES (0, ST_GeomFromText('LINESTRING (600000 200000,350000 150000)', 21781));"

psql -d tests -c "INSERT INTO tests.polygon VALUES (0, ST_GeomFromText('POLYGON ((600000 200000,600000 150000,350000 150000, 350000 200000, 600000 200000))', 21781));"
