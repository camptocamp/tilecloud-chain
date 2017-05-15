FROM camptocamp/postgres:latest

LABEL maintainer "stephane.brunner@camptocamp.com"

ENV POSTGRES_USER www-data
ENV POSTGRES_DB tests

COPY *.sql /docker-entrypoint-initdb.d
