# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The image `waterfall`, which the chain publishes (US-0430) and the service platform builds: the
# API (`waterfall-api`, the default command), the worker (`waterfall-worker`), its schedule
# (`waterfall-worker enqueue <kind>`), the migrations (`waterfall-migrate`) and the service of the
# restoration (`waterfall-restore`) are commands of one distribution, so one image runs them all
# (WF-ARC-0010). No secret is in it (WF-SEC-0010): each
# command reads its settings from the environment of the container, and stops naming the one that
# lacks. The base image is pinned by digest: a tag can be moved, a digest cannot. It is Debian's
# trixie; the client of PostgreSQL comes from the repository of the PostgreSQL project (PGDG), in
# the major version of the server of the platform, 16 (#982).
# Docker Hub, unless the chain gives the registry of its mirror (docs/dev/README.md, « The chain »).
ARG WATERFALL_MIRROR=
FROM ${WATERFALL_MIRROR}python:3.14-slim-trixie@sha256:930e1abba7c4e8f96ed93e8012c35d174d7732752731bbd5e8e757d7ec6f3966 AS python

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# The environment of the distribution, without its development dependencies, the package installed
# in it rather than linked to its sources, on the Python of the base image. uv stays in this stage.
FROM python AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

RUN pip install --no-cache-dir uv==0.13.7
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# The environment alone: neither the sources nor uv. Its files belong to root, and the commands run
# as an unprivileged user, who can change none of them. The API listens on every interface of the
# container, where the default, made for a workstation, is the loopback alone.
FROM python AS production

ENV PATH="/app/.venv/bin:${PATH}" \
    WATERFALL_HOST=0.0.0.0

# pg_dump and pg_restore, with which the worker backs up the two databases and verifies the archive
# (WF-ADM-0150), and the service of the restoration restores them (WF-ADM-0160): the client of the
# major version of the server, 18, the latest of its minor releases, from the repository of
# PostgreSQL. The client follows the server, neither Debian's nor a newer one: a pg_restore newer
# than the server sets what the server does not know — pg_restore 17 set transaction_timeout, which
# a server 16 refused —, and no restoration would end (#982). The key of the repository is pinned
# by its digest, and it is kept in this directory, never downloaded: a build that fetched it from
# www.postgresql.org failed when that site did not answer (#2981). Its fingerprint is
# B97B 0AFC AA1A 47F0 44F2 44A0 7FCC 7D46 ACCC 4CF8. The two sources of apt, deb.debian.org and
# apt.postgresql.org, are tried again five times; one that still does not answer fails the build at
# this step, naming it (apt says the address it could not reach), and the layer that results is read
# from the cache of the chain (images.yml, make build-cache) wherever this file has not changed.
COPY --chmod=0644 pgdg.asc /usr/share/keyrings/pgdg.asc
RUN echo "0144068502a1eddd2a0280ede10ef607d1ec592ce819940991203941564e8e76  /usr/share/keyrings/pgdg.asc" > /tmp/pgdg.sha256 \
    && sha256sum --check --strict /tmp/pgdg.sha256 \
    && rm /tmp/pgdg.sha256 \
    && echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries \
    && echo "deb [signed-by=/usr/share/keyrings/pgdg.asc] https://apt.postgresql.org/pub/repos/apt trixie-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install --yes --no-install-recommends "postgresql-client-18=18.*" \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/.venv /app/.venv
USER 1000:1000

EXPOSE 8000
CMD ["waterfall-api"]
