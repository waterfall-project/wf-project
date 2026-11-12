# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The work image of the end-to-end paths (US-1900): Playwright's image, which carries Chromium and
# its system packages, with what the paths need besides, so that no job of the chain downloads a
# package of Ubuntu (#2913) — make, the Python of the tools, the Node the front is built on, pnpm,
# and the client of Docker, which the paths against the service read the log of the proxy and write
# into PostgreSQL with. The parts
# of e2e.yml run in it, and service.yml plays its paths in it, on the network of the runner. It is
# never built by a job that plays the paths: the chain finds it in the registry by the hash of this
# directory, or builds and publishes it once, before the paths (make e2e-image, wftools.e2eimage).
# Every source is pinned: the images by the digest of their index, the files by their hash, pnpm by
# its version. No `syntax` line: the frontend of BuildKit that Docker carries reads `ADD --checksum`
# and `RUN --mount`, where a named one would be pulled from Docker Hub.

# What is downloaded, out of its archive: Docker's client alone, from the static build of Docker;
# Node, at the major the front is built on (ci.yml, front-build), where the image has Node 24.
FROM mcr.microsoft.com/playwright:v1.64.1-noble@sha256:7852dc5a7d72f5fe458a597d690f6c42fbc8e9e26ddfa95f8e6ef552558d9bbf AS downloads
ADD --checksum=sha256:3fb5d1f13014c18cc54945bc177c58a9056a482dada031e17d12cf2e6922c973 \
    https://download.docker.com/linux/static/stable/x86_64/docker-29.9.3.tgz /docker.tgz
RUN tar --extract --gzip --file /docker.tgz --directory / docker/docker
ADD --checksum=sha256:518674de2b621728a5e4486f5fb3b7d2900bb3cc4aa97969edaa463db99f9778 \
    https://nodejs.org/dist/v26.13.1/node-v26.13.1-linux-x64.tar.gz /node.tgz
RUN mkdir /node && tar --extract --gzip --file /node.tgz --directory /node --strip-components=1

# uv, which installs the Python of the tools and is left out of the image.
FROM ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 AS uv

# The tag follows the version of @playwright/test frontend/pnpm-lock.yaml resolves, which
# tools/tests/test_e2eimage.py holds: its browser is the one that version expects.
FROM mcr.microsoft.com/playwright:v1.64.1-noble@sha256:7852dc5a7d72f5fe458a597d690f6c42fbc8e9e26ddfa95f8e6ef552558d9bbf AS work
LABEL org.opencontainers.image.source="https://github.com/waterfall-project/wf-project"
LABEL org.opencontainers.image.description="The work image of the end-to-end paths of Waterfall"

# make, the package of noble, checked by its hash: it needs nothing but the C library.
ADD --checksum=sha256:1fe6a815b56c7b6e9ce4086a363f09444bbd0a0d30e230c453d0b78e44b57a99 \
    https://archive.ubuntu.com/ubuntu/pool/main/m/make-dfsg/make_4.3-4.1build2_amd64.deb /tmp/make.deb
RUN dpkg --install /tmp/make.deb && rm /tmp/make.deb && make --version

COPY --from=downloads /docker/docker /usr/local/bin/docker
# Node in /usr/local, ahead of the image's in the PATH; tools/tests/test_e2eimage.py holds its major.
COPY --from=downloads /node/bin/ /usr/local/bin/
COPY --from=downloads /node/lib/ /usr/local/lib/
RUN node --version

# The Python of tools/.python-version, which tools/tests/test_e2eimage.py holds: the guard and
# slots.py run by python3 (Makefile, SLOTS), ahead of noble's 3.12 in the PATH.
ENV UV_PYTHON_INSTALL_DIR=/opt/python
RUN --mount=from=uv,source=/uv,target=/usr/local/bin/uv \
    uv python install 3.14 \
    && ln -s "$(uv python find --managed-python 3.14)" /usr/local/bin/python3 \
    && python3 --version

# pnpm at the version `packageManager` names in frontend/package.json, which
# tools/tests/test_e2eimage.py holds: another one would download that one at its first command.
RUN npm install --global pnpm@12.17.0 && pnpm --version
