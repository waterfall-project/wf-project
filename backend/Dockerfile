# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The image of the back: the API, the worker and the migrations are three commands of one
# distribution, so one image runs all three (WF-ARC-0010). The production images, published by
# the chain, come with EP-13; this one serves the service platform of the developers.
# The base image is pinned by digest: a tag can be moved, a digest cannot.
FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

RUN pip install --no-cache-dir uv==0.11.32

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# An unprivileged user.
USER 1000:1000

EXPOSE 8000
CMD ["waterfall-api"]
