# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The directory of test that Keycloak federates on the service platform (WF-ADM-0180, US-1150):
# Debian's slapd, which Debian keeps secure, on its trixie, refreshed each month. The base image is
# pinned by the digest of its multi-architecture index: a tag can be moved, a digest cannot. slapd
# and its clients are pinned to their series, as the client of PostgreSQL of the image waterfall.
# The image holds no directory: the entrypoint makes it at the first start, in the volumes of the
# platform, and seeds it with the LDIF the platform mounts.
# Docker Hub, unless the chain gives the registry of its mirror (docs/dev/README.md, « The chain »).
ARG WATERFALL_MIRROR=
FROM ${WATERFALL_MIRROR}debian:trixie-slim@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4

# The package configures a directory of its own when it is installed; it is removed, so that the
# volumes start empty and the entrypoint makes the one of the platform. slapd writes its pid in
# /run/slapd, which belongs to its user.
# deb.debian.org is tried again five times; if it still does not answer, the build stops at this step,
# and apt says the address it could not reach. The layer is read from the cache of the chain
# (images.yml, make build-cache) wherever this file has not changed.
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        "slapd=2.6.*" "ldap-utils=2.6.*" \
    && rm -rf /var/lib/apt/lists/* /etc/ldap/slapd.d/* /var/lib/ldap/* \
    && install -d -o openldap -g openldap /run/slapd

COPY --chmod=0755 entrypoint.sh /usr/local/bin/entrypoint.sh

EXPOSE 389
# Starts as root to make the directory and give it to openldap, then runs slapd as openldap.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
