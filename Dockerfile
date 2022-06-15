# Base of all section, install the apt packages
FROM osgeo/gdal:ubuntu-small-3.5.0 as base-all
LABEL maintainer Camptocamp "info@camptocamp.com"
SHELL ["/bin/bash", "-o", "pipefail", "-cux"]

RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    apt-get update \
    && apt-get upgrade --assume-yes \
    && apt-get install --assume-yes --no-install-recommends \
        libmapnik3.0 mapnik-utils \
        libdb5.3 \
        fonts-dejavu \
        node-carto \
        optipng jpegoptim \
        postgresql-client-12 net-tools iputils-ping \
        python3-pip \
    && python3 -m pip install --disable-pip-version-check --upgrade pip

# Used to convert the locked packages by poetry to pip requirements format
# We don't directly use `poetry install` because it force to use a virtual environment.
FROM base-all as poetry

# Install Poetry
WORKDIR /tmp
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache \
    python3 -m pip install --disable-pip-version-check --requirement=requirements.txt

# Do the conversion
COPY poetry.lock pyproject.toml ./
RUN poetry export --output=requirements.txt \
    && poetry export --dev --output=requirements-dev.txt

# Base, the biggest thing is to install the Python packages
FROM base-all as base

RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    --mount=type=cache,target=/root/.cache \
    --mount=type=bind,from=poetry,source=/tmp,target=/poetry \
    DEV_PACKAGES="python3.8-dev build-essential libgeos-dev libmapnik-dev libpq-dev \
  build-essential python3-dev" \
    && apt-get update \
    && apt-get install --assume-yes --no-install-recommends ${DEV_PACKAGES} \
    && python3 -m pip install --disable-pip-version-check --no-deps --requirement=/poetry/requirements.txt \
    && python3 -m compileall /usr/local/lib/python3.8 /usr/lib/python3.8 \
    && strip /usr/local/lib/python3.8/dist-packages/shapely/*/*.so \
    && apt-get remove --purge --autoremove --yes ${DEV_PACKAGES} binutils

# From c2cwsgiutils

CMD ["gunicorn", "--paste=/app/production.ini"]

ENV TERM=linux \
    LANG=C.UTF-8 \
    LOG_TYPE=console \
    DEVELOPMENT=0 \
    PKG_CONFIG_ALLOW_SYSTEM_LIBS=OHYESPLEASE

ENV C2C_SECRET= \
    C2C_BASE_PATH=/c2c \
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
    TILECLOUD_CHAIN_LOG_LEVEL=INFO \
    TILECLOUD_LOG_LEVEL=INFO \
    C2CWSGIUTILS_LOG_LEVEL=WARN \
    GUNICORN_LOG_LEVEL=WARN \
    GUNICORN_ACCESS_LOG_LEVEL=INFO \
    SQL_LOG_LEVEL=WARN \
    OTHER_LOG_LEVEL=WARN \
    VISIBLE_ENTRY_POINT=/ \
    TILE_NB_THREAD=2 \
    METATILE_NB_THREAD=25 \
    SERVER_NB_THREAD=10 \
    TILE_QUEUE_SIZE=2 \
    TILE_CHUNK_SIZE=1 \
    TILE_SERVER_LOGLEVEL=quiet \
    TILE_MAPCACHE_LOGLEVEL=verbose \
    DEVLOPEMENT=0

EXPOSE 8080

WORKDIR /app/

# The final part
FROM base as runner

COPY . /app/
RUN --mount=type=cache,target=/root/.cache \
    sed --in-place 's/enable = true # disable on Docker/enable = false/g' pyproject.toml \
    && python3 -m pip install --disable-pip-version-check --no-deps --editable=. \
    && mv docker/run /usr/bin/ \
    && python3 -m compileall -q /app/tilecloud_chain

# Do the lint, used by the tests
FROM base as tests

RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,from=poetry,source=/tmp,target=/poetry \
    python3 -m pip install --disable-pip-version-check --no-deps --requirement=/poetry/requirements-dev.txt

COPY . /app/
RUN --mount=type=cache,target=/root/.cache \
    sed --in-place 's/enable = true # disable on Docker/enable = false/g' pyproject.toml \
    && python3 -m pip install --disable-pip-version-check --no-deps --editable=.

ENV TILEGENERATION_MAIN_CONFIGFILE=

# Set runner as final
FROM runner
