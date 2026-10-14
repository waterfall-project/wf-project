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
FROM python:3.13-slim-trixie@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f AS python

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# The environment of the distribution, without its development dependencies, the package installed
# in it rather than linked to its sources, on the Python of the base image. uv stays in this stage.
FROM python AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

RUN pip install --no-cache-dir uv==0.11.32
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
# major version of the server, 16, the latest of its minor releases. Not Debian's, 17: pg_restore 17
# sets transaction_timeout, which a server 16 refuses, and no restoration would end (#982). The key
# of the repository is pinned by its digest; its fingerprint is
# B97B 0AFC AA1A 47F0 44F2 44A0 7FCC 7D46 ACCC 4CF8.
RUN python -c "import urllib.request; urllib.request.urlretrieve('https://www.postgresql.org/media/keys/ACCC4CF8.asc', '/usr/share/keyrings/pgdg.asc')" \
    && echo "0144068502a1eddd2a0280ede10ef607d1ec592ce819940991203941564e8e76  /usr/share/keyrings/pgdg.asc" > /tmp/pgdg.sha256 \
    && sha256sum --check --strict /tmp/pgdg.sha256 \
    && rm /tmp/pgdg.sha256 \
    && echo "deb [signed-by=/usr/share/keyrings/pgdg.asc] https://apt.postgresql.org/pub/repos/apt trixie-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install --yes --no-install-recommends "postgresql-client-16=16.*" \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/.venv /app/.venv
USER 1000:1000

EXPOSE 8000
CMD ["waterfall-api"]
