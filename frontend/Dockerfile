# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# Development image of the front: `next dev`, started by the development Compose against
# the address of an API — the fake back first (US-0030), the real service from EP-03.
# The base image is pinned by digest: a tag can be moved, a digest cannot.
FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1

ENV NEXT_TELEMETRY_DISABLED=1 \
    COREPACK_ENABLE_DOWNLOAD_PROMPT=0

WORKDIR /app
RUN corepack enable pnpm && chown 1000:1000 /app
# The unprivileged user of the node image.
USER 1000:1000

COPY --chown=1000:1000 package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY --chown=1000:1000 . .

EXPOSE 3000
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]
