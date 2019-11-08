FROM camptocamp/c2cwsgiutils:3-full
MAINTAINER Stéphane Brunner <stephane.brunner@camptocamp.com>

COPY requirements.txt /app/
RUN \
  DEV_PACKAGES="python3.7-dev build-essential libgeos-dev libmapnik-dev libdb-dev" && \
  apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get install --assume-yes --no-install-recommends \
    ca-certificates \
    libmapnik3.0 \
    mapnik-utils \
    gdal-bin \
    libdb5.3 \
    fonts-dejavu \
    node-carto \
    curl \
    optipng \
    ${DEV_PACKAGES} && \
  cd /app && \
  python3 -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt && \
  mkdir /fonts && \
  mkdir /project && \
  apt remove --purge --autoremove --yes ${DEV_PACKAGES} binutils && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/* && \
  python3 -m compileall -q

ENV TILEGENERATION_CONFIGFILE=/etc/tilegeneration/config.yaml \
    C2CWSGI_LOG_LEVEL=WARN \
    TILECLOUD_LOG_LEVEL=INFO \
    OTHER_LOG_LEVEL=WARN \
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
