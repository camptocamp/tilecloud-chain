FROM osgeo/gdal:ubuntu-small-3.3.3 as base
LABEL maintainer "info@camptocamp.org"

RUN \
  apt update && \
  DEBIAN_FRONTEND=noninteractive apt install --assume-yes --no-install-recommends \
  libmapnik3.0 \
  mapnik-utils \
  libdb5.3 \
  fonts-dejavu \
  node-carto \
  optipng \
  jpegoptim \
  postgresql-client-12 net-tools iputils-ping \
  python3-pip && \
  apt clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/*

COPY requirements.txt Pipfile Pipfile.lock /app/
RUN \
  DEV_PACKAGES="python3.8-dev build-essential libgeos-dev libmapnik-dev libpq-dev \
  build-essential python3-dev" && \
  apt update && \
  DEBIAN_FRONTEND=noninteractive apt install --assume-yes --no-install-recommends \
  ${DEV_PACKAGES} && \
  cd /app/ && \
  python3 -m pip install --disable-pip-version-check --no-cache-dir \
  --requirement=/app/requirements.txt && \
  pipenv sync --system --clear && \
  python3 -m compileall /usr/local/lib/python3.8 /usr/lib/python3.8 -q \
  -x '/usr/local/lib/python3.8/dist-packages/pipenv/' && \
  strip /usr/local/lib/python3.8/dist-packages/shapely/*/*.so && \
  apt remove --purge --autoremove --yes ${DEV_PACKAGES} binutils && \
  apt clean && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/*

# From c2cwsgiutils

CMD ["c2cwsgiutils-run"]

ENV TERM=linux \
  LANG=C.UTF-8 \
  LOG_TYPE=console \
  LOG_HOST=localhost \
  LOG_PORT=514 \
  SQL_LOG_LEVEL=WARN \
  GUNICORN_LOG_LEVEL=WARN \
  OTHER_LOG_LEVEL=WARN \
  DEVELOPMENT=0 \
  PKG_CONFIG_ALLOW_SYSTEM_LIBS=OHYESPLEASE

ENV C2C_BASE_PATH=/c2c \
  C2C_SECRET=c2crulez \
  C2CWSGIUTILS_CONFIG=/app/production.ini \
  C2C_REDIS_URL= \
  C2C_REDIS_SENTINELS= \
  C2C_REDIS_TIMEOUT=3 \
  C2C_REDIS_SERVICENAME=mymaster \
  C2C_REDIS_DB=0 \
  C2C_BROADCAST_PREFIX=broadcast_api_ \
  C2C_REQUEST_ID_HEADER= \
  C2C_REQUESTS_DEFAULT_TIMEOUT= \
  C2C_SQL_PROFILER_ENABLED=0 \
  C2C_PROFILER_PATH= \
  C2C_PROFILER_MODULES= \
  C2C_DEBUG_VIEW_ENABLED=0 \
  C2C_ENABLE_EXCEPTION_HANDLING=0

# End from c2cwsgiutils

ENV TILEGENERATION_CONFIGFILE=/etc/tilegeneration/config.yaml \
  TILEGENERATION_MAIN_CONFIGFILE=/etc/tilegeneration/config.yaml \
  TILEGENERATION_HOSTSFILE=/etc/tilegeneration/hosts.yaml \
  C2CWSGI_LOG_LEVEL=WARN \
  TILECLOUD_LOG_LEVEL=INFO \
  OTHER_LOG_LEVEL=WARN \
  TILECLOUD_CHAIN_LOG_LEVEL=INFO \
  VISIBLE_ENTRY_POINT=/tiles/ \
  TILE_NB_THREAD=2 \
  METATILE_NB_THREAD=25 \
  SERVER_NB_THREAD=10 \
  TILE_QUEUE_SIZE=2 \
  TILE_CHUNK_SIZE=1 \
  TILE_SERVER_LOGLEVEL=quiet \
  TILE_MAPCACHE_LOGLEVEL=verbose

EXPOSE 8080

WORKDIR /app/

FROM base as runner

COPY . /app/

RUN \
  python3 -m pip install --disable-pip-version-check --no-deps --no-cache-dir --editable=. && \
  mv docker/run /usr/bin/ && \
  python3 -m compileall -q /app/tilecloud_chain

WORKDIR /etc/tilegeneration/

FROM base as tests

RUN pipenv sync --dev --system --clear

COPY . /app/
RUN prospector --output-format=pylint
RUN python3 -m pip install --disable-pip-version-check --no-deps --no-cache-dir --editable=.

ENV TILEGENERATION_MAIN_CONFIGFILE=

FROM runner
