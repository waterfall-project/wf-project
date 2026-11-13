# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The work image of the end-to-end paths (US-1900): Playwright's image, which carries Chromium and
# its system packages, with what the paths need besides, so that no job of the chain downloads a
# package of Ubuntu (#2913) — make, the Python of the tools, pnpm, and the client of Docker, which
# the paths against the service read the log of the proxy and write into PostgreSQL with. The parts
# of e2e.yml run in it, and service.yml plays its paths in it, on the network of the runner. It is
# never built by a job that plays the paths: the chain finds it in the registry by the hash of this
# directory, or builds and publishes it once, before the paths (make e2e-image, wftools.e2eimage).
# Every source is pinned: the images by the digest of their index, the files by their hash, pnpm and
# its binary among them, and the Python of uv by its version, which uv checks by the hash it carries. A download
# that fails fails the build, which wftools.e2eimage tries again from the layers already built
# (#2530). The image is built for amd64 alone, the runners' and the workstations': the archives of
# Docker and of make are those of x86_64. No `syntax` line: the frontend of BuildKit that Docker carries reads `ADD --checksum`
# and `RUN --mount`, where a named one would be pulled from Docker Hub.

# Docker's client alone, from the static build of Docker, out of its archive.
FROM mcr.microsoft.com/playwright:v1.64.1-noble@sha256:7852dc5a7d72f5fe458a597d690f6c42fbc8e9e26ddfa95f8e6ef552558d9bbf AS docker-client
ADD --checksum=sha256:3fb5d1f13014c18cc54945bc177c58a9056a482dada031e17d12cf2e6922c973 \
    https://download.docker.com/linux/static/stable/x86_64/docker-29.9.3.tgz /docker.tgz
RUN tar --extract --gzip --file /docker.tgz --directory / docker/docker

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

COPY --from=docker-client /docker/docker /usr/local/bin/docker

# The Python of tools/.python-version, which tools/tests/test_e2eimage.py holds: the guard and
# slots.py run by python3 (Makefile, SLOTS), ahead of noble's 3.12 in the PATH.
# Its patch is pinned here, and uv, pinned by digest, checks the archive against the hash it carries
# for that version; uv tries a download again five times (#2530).
ENV UV_PYTHON_INSTALL_DIR=/opt/python
RUN --mount=from=uv,source=/uv,target=/usr/local/bin/uv \
    UV_HTTP_RETRIES=5 uv python install 3.14.10 \
    && ln -s "$(uv python find --managed-python 3.14.10)" /usr/local/bin/python3 \
    && python3 --version

# pnpm at the version `packageManager` names in frontend/package.json, which
# tools/tests/test_e2eimage.py holds: another one would download that one at its first command. Its
# two archives from npm's registry, checked by their hash: pnpm, which bundles its dependencies, and
# its binary for linux-x64, the one optional dependency it runs here — without it, pnpm would
# download it at its first command. npm installs them without the network.
ADD --checksum=sha256:6d776e285187f9e334d8826cc5a88e82e41606345f196a5a93f4403bd332553e \
    https://registry.npmjs.org/pnpm/-/pnpm-12.17.0.tgz /tmp/pnpm/pnpm.tgz
ADD --checksum=sha256:6c1c71d00f82765d8f7488df6d1a94533fd1ad5d47c86da41211b1da1093c9d4 \
    https://registry.npmjs.org/@pnpm/exe.linux-x64/-/exe.linux-x64-12.17.0.tgz /tmp/pnpm/exe.tgz
RUN npm install --global --offline /tmp/pnpm/pnpm.tgz /tmp/pnpm/exe.tgz && rm -r /tmp/pnpm \
    && pnpm --version
