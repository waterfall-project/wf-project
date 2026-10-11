# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The image `waterfall`, which the chain publishes (US-0430) and the service platform builds: the
# API (`waterfall-api`, the default command), the worker (`waterfall-worker`), its schedule
# (`waterfall-worker enqueue <kind>`) and the migrations (`waterfall-migrate`) are commands of one
# distribution, so one image runs them all (WF-ARC-0010). No secret is in it (WF-SEC-0010): each
# command reads its settings from the environment of the container, and stops naming the one that
# lacks. The base image is pinned by digest: a tag can be moved, a digest cannot.
FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641 AS python

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

COPY --from=build /app/.venv /app/.venv
USER 1000:1000

EXPOSE 8000
CMD ["waterfall-api"]
