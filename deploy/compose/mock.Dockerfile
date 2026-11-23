# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The fake back of the public demonstration (compose.demo.yaml): Prism, at the version the Makefile
# pins (PRISM_VERSION), installed once in the image rather than fetched by npx at every start. The
# contract it serves, waterfall.mock.json, is mounted, never baked in. Same base image as the front,
# pinned by digest.
# Docker Hub, unless the chain gives the registry of its mirror (docs/dev/README.md, « The chain »).
ARG WATERFALL_MIRROR=
FROM ${WATERFALL_MIRROR}node:26-alpine@sha256:6bd9ab43c0ec0190ca7b2d193906cb8b7edf6e7f4afa43ddeccd6452710bffb5

ARG PRISM_VERSION
RUN test -n "$PRISM_VERSION" \
    && npm install --global --no-audit --no-fund "@stoplight/prism-cli@${PRISM_VERSION}" \
    && npm cache clean --force

USER 1000:1000
EXPOSE 4010
CMD ["prism", "mock", "/contract/waterfall.mock.json", "--host", "0.0.0.0", "--port", "4010"]
