FROM ubuntu:16.04
MAINTAINER Stéphane Brunner <stephane.brunner@camptocamp.com>

RUN \
  apt-get update && \
  apt-get install --assume-yes --no-install-recommends wget ca-certificates python python-mapnik mapnik-utils gdal-bin libpq5 libgeos-c1v5 fonts-dejavu node-carto osm2pgsql curl unzip gcc python-dev libpq-dev libgeos-dev libmapnik-dev && \
  cd /tmp && \
  wget https://bootstrap.pypa.io/get-pip.py && \
  python get-pip.py && \
  mkdir /fonts && \
  mkdir /project

COPY requirements.txt /src/

RUN \
  cd /src && \
  pip install -r requirements.txt && \
  apt-get remove --assume-yes --purge gcc python-dev libpq-dev libgeos-dev libmapnik-dev wget && \
  apt-get autoremove --assume-yes && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/*

COPY . /src/

RUN \
  cd /src && \
  pip install -e . && \
  mv docker/run /usr/bin/

WORKDIR /project
