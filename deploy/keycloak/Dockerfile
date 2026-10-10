# syntax=docker/dockerfile:1
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The image of Keycloak for Waterfall (US-0350): Keycloak 26 built for PostgreSQL, under /auth,
# with the extension of Waterfall and its themes; the realm, and keycloak-config-cli to apply it.
# One image, two commands: Keycloak by default, `apply-realm` to apply the realm. No secret is in
# it (WF-SEC-0010): the database, the administrator and the secrets of the clients come at run
# time. Every image is pinned by the digest of its index; raise the version of Keycloak here and
# in extension/pom.xml together, and keycloak-config-cli with it.

# The extension, compiled and tested here: no JVM is asked of the workstation.
FROM maven:3.9.16-eclipse-temurin-21@sha256:99e61abcff91a9b1333463bd8451fb18495d6eba9250ac66a338b518f8278320 AS extension
WORKDIR /build
COPY extension/pom.xml ./
RUN --mount=type=cache,target=/root/.m2 mvn --batch-mode --quiet dependency:go-offline
COPY extension/src ./src
RUN --mount=type=cache,target=/root/.m2 mvn --batch-mode --quiet package

# keycloak-config-cli, built for this version of Keycloak; only its jar is taken.
FROM adorsys/keycloak-config-cli:6.5.1-26.5.5@sha256:0955d98c8a341898b7aa177477edf8a1e90569ae50bbe7598141c1270b773274 AS realm-applier

FROM keycloak/keycloak:26.5.7@sha256:45ae20191531eb608ddb0b775d012b40d3e4f942697f3214694887dd7c108d13
COPY --from=extension /build/target/waterfall-keycloak-extension.jar /opt/keycloak/providers/
COPY themes/ /opt/keycloak/themes/
# The options Keycloak fixes at build time: started with --optimized, it does not rebuild. Under
# /auth, where the front end of the platform serves it (EP-03, "Déploiement de démonstration").
RUN /opt/keycloak/bin/kc.sh build --db=postgres --health-enabled=true --http-relative-path=/auth
COPY --from=realm-applier /app/keycloak-config-cli.jar /opt/keycloak-config-cli/keycloak-config-cli.jar
COPY realm/ /opt/keycloak/realm/
COPY apply-realm.sh /opt/keycloak/bin/apply-realm
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
CMD ["start", "--optimized"]
