# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The images of the front, one stage each:
# - `development`: `next dev`, started by the development Compose against the address of an API —
#   the fake back first (US-0030), the real service from EP-03;
# - `production`, the last stage, built when none is named: the front built by `next build`,
#   served by Node alone from the standalone output of Next, which the chain publishes (US-0430).
#   The addresses of the API, of Keycloak and of Redis, and the secret of the client of the front,
#   are read from the environment of the container, never while building (WF-SEC-0010): the
#   server checks them as it starts and stops naming the one that is missing (#825,
#   `src/instrumentation.ts`). `next build` does write keys of its own into its output, and so into
#   the image: the key of the closures of the server actions (`encryptionKey`,
#   `.next/server/server-reference-manifest.*`) and those of the draft mode (`previewMode*`,
#   `.next/prerender-manifest.json`), which whoever pulls the image reads. Next compares
#   `previewModeId` with the cookie `__prerender_bypass` and the header `x-prerender-revalidate` at
#   every request to a prerendered page, and no variable replaces it when Node runs: with it,
#   anyone may pass the cache by and have the prerendered pages made anew. That is of no matter as
#   long as no prerendered page holds anything but what is public, which `make prerendered-front`
#   holds. The key of the server actions protects nothing as long as the front has no closure for
#   Next to encrypt — no server action written inline in a function, no `"use cache"` —, and that
#   of the draft mode would let anyone enter it if the front had one — it has no `draftMode` and no
#   router of pages —, which `src/next-config.test.ts` holds. The key of the server actions is
#   set at start by `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY`, which Next reads before the one of the
#   build, and without which the server does not start (#825).
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
# (`next.config.ts`). No variable of the platform, nor any key, is set here: the keys the build
# writes are its own, said above.
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
