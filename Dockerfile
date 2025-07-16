# Base of all section, install the apt packages
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.3 AS base-all
LABEL org.opencontainers.image.authors="Camptocamp <info@camptocamp.com>"

# Fail on error on pipe, see: https://github.com/hadolint/hadolint/wiki/DL4006.
# Treat unset variables as an error when substituting.
# Print commands and their arguments as they are executed.
SHELL ["/bin/bash", "-o", "pipefail", "-cux"]

RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    apt-get update \
    && apt-get upgrade --assume-yes \
    && apt-get install --assume-yes --no-install-recommends \
        python3-mapnik \
        libdb5.3 \
        fonts-dejavu \
        optipng jpegoptim pngquant \
        postgresql-client net-tools iputils-ping \
        python3-pip python3-venv \
    && python3 -m venv --system-site-packages /venv

ENV PATH=/venv/bin:$PATH

# Used to convert the locked packages by poetry to pip requirements format
# We don't directly use `poetry install` because it force to use a virtual environment.
FROM base-all AS poetry

# Install Poetry
WORKDIR /tmp
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache \
    python3 -m pip install --disable-pip-version-check --requirement=requirements.txt

# Do the conversion
COPY poetry.lock pyproject.toml ./
ENV POETRY_DYNAMIC_VERSIONING_BYPASS=0.0.0
RUN poetry export --output=requirements.txt \
    && poetry export --with=dev --output=requirements-dev.txt

# Base, the biggest thing is to install the Python packages
FROM base-all AS base

# hadolint ignore=SC2086
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    --mount=type=cache,target=/root/.cache \
    --mount=type=bind,from=poetry,source=/tmp,target=/poetry \
    DEV_PACKAGES="python3-dev build-essential libgeos-dev libpq-dev" \
    && apt-get update \
    && apt-get install --assume-yes --no-install-recommends ${DEV_PACKAGES} \
    && python3 -m pip install --disable-pip-version-check --no-deps --requirement=/poetry/requirements.txt \
    && python3 -m compileall /venv/lib/python* /usr/lib/python* \
    && strip /venv/lib/python*/site-packages/shapely/*.so \
    && apt-get remove --purge --autoremove --yes ${DEV_PACKAGES} binutils

# From c2cwsgiutils

CMD ["/venv/bin/pserve", "c2c:///app/application.ini"]

ENV LOG_TYPE=console \
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
    WAITRESS_LOG_LEVEL=INFO \
    WSGI_LOG_LEVEL=INFO \
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
    WAITRESS_THREADS=10 \
    PYRAMID_INCLUDES= \
    DEBUGTOOLBAR_HOSTS=

EXPOSE 8080

WORKDIR /app/

# The final part
FROM base AS runner

COPY . /app/
ARG VERSION=dev
ENV POETRY_DYNAMIC_VERSIONING_BYPASS=dev
RUN --mount=type=cache,target=/root/.cache \
    POETRY_DYNAMIC_VERSIONING_BYPASS=${VERSION} python3 -m pip install --disable-pip-version-check --no-deps --editable=. \
    && mv docker/run /usr/bin/ \
    && python3 -m compileall -q /app/tilecloud_chain

# Do the lint, used by the tests
FROM base AS tests

# Fail on error on pipe, see: https://github.com/hadolint/hadolint/wiki/DL4006.
# Treat unset variables as an error when substituting.
# Print commands and their arguments as they are executed.
SHELL ["/bin/bash", "-o", "pipefail", "-cux"]

RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    apt-get update \
    && apt-get install --assume-yes --no-install-recommends software-properties-common gpg-agent \
    && add-apt-repository ppa:savoury1/pipewire \
    && add-apt-repository ppa:savoury1/chromium \
    && apt-get install --assume-yes --no-install-recommends chromium-browser git curl gnupg
COPY .nvmrc /tmp
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    NODE_MAJOR="$(cat /tmp/.nvmrc)" \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && curl --silent https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor --output=/etc/apt/keyrings/nodesource.gpg \
    && apt-get update \
    && apt-get install --assume-yes --no-install-recommends "nodejs=${NODE_MAJOR}.*"
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install --include=dev --ignore-scripts
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,from=poetry,source=/tmp,target=/poetry \
    python3 -m pip install --disable-pip-version-check --no-deps --requirement=/poetry/requirements-dev.txt

COPY . ./
RUN --mount=type=cache,target=/root/.cache \
    POETRY_DYNAMIC_VERSIONING_BYPASS=0.0.0 python3 -m pip install --disable-pip-version-check --no-deps --editable=. \
    && python3 -m pip freeze > /requirements.txt

ENV TILEGENERATION_MAIN_CONFIGFILE=

# Set runner as final
FROM runner
