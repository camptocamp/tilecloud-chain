FROM ubuntu:18.04

COPY test-db /docker-entrypoint-initdb.d
VOLUME /docker-entrypoint-initdb.d

COPY mapcache-docker /etc/mapcache
VOLUME /etc/mapcache

COPY mapfile-docker /etc/mapserver
VOLUME /etc/mapserver

CMD ['sleep', '3600']
