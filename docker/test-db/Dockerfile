FROM camptocamp/postgis:latest

ENV POSTGRES_USER www-data
ENV POSTGRES_DB tests

COPY *.sql /docker-entrypoint-initdb.d
