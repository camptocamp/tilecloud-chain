FROM camptocamp/c2cwsgiutils:3-full
MAINTAINER Stéphane Brunner <stephane.brunner@camptocamp.com>

COPY requirements.txt /app/
RUN \
  DEV_PACKAGES="python3.7-dev build-essential libgeos-dev" && \
  apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get install --assume-yes --no-install-recommends \
    ca-certificates \
    libmapnik-dev \
    mapnik-utils \
    gdal-bin \
    libdb-dev \
    fonts-dejavu \
    node-carto \
    osm2pgsql \
    curl \
    unzip \
    optipng \
    ${DEV_PACKAGES} && \
  cd /app && \
  pip install --disable-pip-version-check --no-cache-dir -r requirements.txt && \
  mkdir /fonts && \
  mkdir /project && \
  apt remove --purge --autoremove --yes ${DEV_PACKAGES} binutils && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/* && \
  python3 -m compileall -q

ENV TILEGENERATION_CONFIGFILE=/etc/tilegeneration/config.yaml \
    C2CWSGI_LOG_LEVEL=WARN \
    TILECLOUD_LOG_LEVEL=INFO \
    TILECLOUD_CHAIN_LOG_LEVEL=INFO \
    VISIBLE_ENTRY_POINT=/tiles/

EXPOSE 8080

WORKDIR /etc/tilegeneration/

COPY . /app/

RUN \
  cd /app && \
  pip install --editable=. && \
  mv docker/run /usr/bin/ && \
  python3 -m compileall -q /app/tilecloud_chain
