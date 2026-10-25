# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The fake back of the public demonstration (compose.demo.yaml): Prism, at the version the Makefile
# pins (PRISM_VERSION), installed once in the image rather than fetched by npx at every start. The
# contract it serves, waterfall.mock.json, is mounted, never baked in. Same base image as the front,
# pinned by digest.
FROM node:24-alpine@sha256:44fce696f38ba8c987c4db89954051000bbd05ffd8d8659ba15ed4a8602e937f

ARG PRISM_VERSION
RUN test -n "$PRISM_VERSION" \
    && npm install --global --no-audit --no-fund "@stoplight/prism-cli@${PRISM_VERSION}" \
    && npm cache clean --force

USER 1000:1000
EXPOSE 4010
CMD ["prism", "mock", "/contract/waterfall.mock.json", "--host", "0.0.0.0", "--port", "4010"]
