# Base of all section, install the apt packages
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.13.1 AS base-all
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

CMD ["uvicorn", "tilecloud_chain.main:app", "--host=0.0.0.0", "--port=8080", "--log-config=/app/logging.yaml"]

EXPOSE 8080
ENV C2C__TOOLS__LOGGING__APPLICATION_MODULE=tilecloud_chain

# Do the lint, used by the tests
FROM base AS tests

# Fail on error on pipe, see: https://github.com/hadolint/hadolint/wiki/DL4006.
# Treat unset variables as an error when substituting.
# Print commands and their arguments as they are executed.
SHELL ["/bin/bash", "-o", "pipefail", "-cux"]

# Puppeteer downloaded Chrome crashes with the GDAL image LD_PRELOAD tcmalloc.
# Disable it in the tests stage where Node/Puppeteer is executed.
ENV LD_PRELOAD=

RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    apt-get update \
    && apt-get install --assume-yes --no-install-recommends software-properties-common gpg-agent \
    && add-apt-repository ppa:savoury1/pipewire \
    && apt-get install --assume-yes --no-install-recommends \
        git nodejs npm \
        libasound2t64 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcairo2 \
        libcups2 \
        libdrm2 \
        libgbm1 \
        libglib2.0-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        libxrender1 \
        libxss1 \
        libxtst6
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install --include=dev --ignore-scripts \
    && npm rebuild puppeteer

RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,from=poetry,source=/tmp,target=/poetry \
    python3 -m pip install --disable-pip-version-check --no-deps --requirement=/poetry/requirements-dev.txt

COPY . ./
RUN --mount=type=cache,target=/root/.cache \
    POETRY_DYNAMIC_VERSIONING_BYPASS=0.0.0 python3 -m pip install --disable-pip-version-check --no-deps --editable=. \
    && python3 -m pip freeze > /requirements.txt

# Set runner as final
FROM runner
