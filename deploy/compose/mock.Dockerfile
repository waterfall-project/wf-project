# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The fake back of the public demonstration (compose.demo.yaml): Prism, at the version the Makefile
# pins (PRISM_VERSION), installed once in the image rather than fetched by npx at every start. The
# contract it serves, waterfall.mock.json, is mounted, never baked in. Same base image as the front,
# pinned by digest.
# Docker Hub, unless the chain gives the registry of its mirror (docs/dev/README.md, « The chain »).
ARG WATERFALL_MIRROR=
FROM ${WATERFALL_MIRROR}node:26-alpine@sha256:c6ad9e9c1d80f6eb607c26b4b0a132ff7a2344fad1c78ea3baa2a7d4c8de6d94

ARG PRISM_VERSION
RUN test -n "$PRISM_VERSION" \
    && npm install --global --no-audit --no-fund "@stoplight/prism-cli@${PRISM_VERSION}" \
    && npm cache clean --force

USER 1000:1000
EXPOSE 4010
CMD ["prism", "mock", "/contract/waterfall.mock.json", "--host", "0.0.0.0", "--port", "4010"]
