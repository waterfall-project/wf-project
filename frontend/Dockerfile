# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The images of the front, one stage each:
# - `development`: `next dev`, started by the development Compose against the address of an API —
#   the fake back first (US-0030), the real service from EP-03;
# - `production`, the last stage, built when none is named: the front built by `next build`,
#   served by Node alone from the standalone output of Next, which the chain publishes (US-0430).
#   No secret is in it (WF-SEC-0010): the addresses of the API, of Keycloak and of Redis, and the
#   secret of the client of the front, are read from the environment of the container when a
#   request needs them, never while building.
# The base image is pinned by digest: a tag can be moved, a digest cannot.
FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS node

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

# The tools and every dependency of the front, owned by the unprivileged user of the node image.
FROM node AS development

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable pnpm && chown 1000:1000 /app
USER 1000:1000

COPY --chown=1000:1000 package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY --chown=1000:1000 . .

EXPOSE 3000
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]

# The build of production, traced by Next into a server that needs only the modules it imports
# (`next.config.ts`). No variable of the platform is set here: no page reads one while built.
FROM development AS build

ENV WATERFALL_STANDALONE=1
RUN pnpm build

# The server alone, its static files beside it. The files belong to root and the server runs as
# the unprivileged user: it can write nothing but the cache of Next. It listens on every interface
# of the container — Docker sets HOSTNAME to the name of the container, which the standalone
# server would otherwise listen on alone.
FROM node AS production

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --from=build --chown=root:root /app/.next/standalone ./
COPY --from=build --chown=root:root /app/.next/static ./.next/static
COPY --from=build --chown=root:root /app/public ./public
RUN mkdir -p .next/cache && chown 1000:1000 .next/cache
USER 1000:1000

EXPOSE 3000
CMD ["node", "server.js"]
