FROM camptocamp/c2cwsgiutils:2
MAINTAINER Stéphane Brunner <stephane.brunner@camptocamp.com>

RUN \
  apt-get update && \
  apt-get install --assume-yes --no-install-recommends \
    ca-certificates \
    libmapnik-dev \
    mapnik-utils \
    gdal-bin \
    libdb-dev \
    fonts-dejavu \
    node-carto \
    osm2pgsql \
    curl \
    unzip && \
  cd /tmp && \
  mkdir /fonts && \
  mkdir /project && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/*

COPY requirements.txt /app/

RUN \
  cd /app && \
  pip install --no-cache-dir -r requirements.txt

ENV TILEGENERATION_CONFIGFILE=tilegeneration/config.yaml \
    C2CWSGI_LOG_LEVEL=WARN \
    TILECLOUD_LOG_LEVEL=INFO \
    TILECLOUD_CHAIN_LOG_LEVEL=INFO \
    GUNICORN_PARAMS="-b :80 --worker-class gthread --threads 1 --workers 5"

EXPOSE 80

WORKDIR /project

COPY . /app/

RUN \
  cd /app && \
  pip install --editable=. && \
  mv docker/run /usr/bin/
