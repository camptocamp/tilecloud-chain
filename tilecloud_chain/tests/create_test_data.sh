#!/bin/bash -e

createdb -E UTF8 -T template0 tests-deploy
psql -q -d tests-deploy -c "CREATE TABLE test (name varchar(10));"
psql -q -d tests-deploy -c "INSERT INTO test VALUES ('referance');"
