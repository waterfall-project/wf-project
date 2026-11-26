# syntax=docker/dockerfile:1
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The image `keycloak`, which the chain publishes (US-0430) and the service platform builds
# (US-0350): Keycloak 26 built for PostgreSQL, under /auth, with the extension of Waterfall and its
# themes; the realm, and keycloak-config-cli to apply it. One image, three commands: Keycloak by
# default, `apply-realm` to apply the realm, and `realm-service`, which applies it, then stays and
# applies it again over a database the service of the restoration has restored (#955). No secret is in it (WF-SEC-0010): the database, the
# administrator and the secrets of the clients come at run time. What the development platform adds
# to the realm — its directory, its external provider, their test accounts — never enters it
# (.dockerignore). Every image is pinned by the digest of its index; raise the version of Keycloak
# here and in extension/pom.xml together, and keycloak-config-cli with it.

# The extension, compiled and tested here: no JVM is asked of the workstation. The JDK is 27, but
# the extension targets Java 21 (extension/pom.xml), the Java that runs Keycloak 26.8.2.
# Docker Hub, unless the chain gives the registry of its mirror (docs/dev/README.md, « The chain »).
ARG WATERFALL_MIRROR=
FROM ${WATERFALL_MIRROR}maven:3-eclipse-temurin-27@sha256:3175c44b207d6698aecb9bbb5bf285b5b4efcf7f567d6f65d88cd218276a6ab2 AS extension
WORKDIR /build
COPY extension/pom.xml ./
# Maven Central is asked here and nowhere else, once per content of extension/pom.xml. The local
# repository of Maven (/root/.m2) is a layer of the image, not a cache mount: a mount is never exported
# to the build cache of GitHub Actions (`mode=max` exports layers), so a fresh runner found it empty,
# while this layer came back CACHED, and `mvn package` downloaded everything again, with no retry, and
# took a 429 (#4790, runs 45722567147 and 45876627630). The layer is replayed only when pom.xml changes;
# the first run after such a change, after the merge of this change, or after the cache of GitHub
# Actions evicted the layer, is the one still exposed to Central. The price: locally, the repository
# is no longer kept from one pom.xml to the next, as the old cache mount kept it.
# Resolver 2 settings (Maven 3.10, native HTTP transport): connection twenty seconds, request sixty;
# a failed or refused (429, 502, 503, 504) request is retried six times, the pause growing from ten
# seconds to two minutes. The loop below starts the whole resolution again, three times at most, thirty
# seconds apart: in the queue, Central left a build hanging until Maven gave up, five minutes later
# (run 44885271614, 2026-11-21). A new attempt finds in the repository what the previous one downloaded.
# `dependency:go-offline` resolves the dependencies and the plugins of the lifecycle; the provider of
# surefire is only fetched when a test runs, hence the stub test, so that `package` below, offline,
# finds all it needs; the stub main class does the same for the compiler, which `src/main` empty would
# not run ("No sources to compile"). A missing artifact fails here, in the local build, not in the queue.
ENV MAVEN_OPTS="-Daether.transport.http.connectTimeout=20000 -Daether.transport.http.requestTimeout=60000 \
-Daether.transport.http.retryHandler.count=6 -Daether.transport.http.retryHandler.interval=10000 \
-Daether.transport.http.retryHandler.intervalMax=120000 \
-Daether.transport.http.retryHandler.serviceUnavailable=429,502,503,504"
RUN mkdir -p src/main/java src/test/java && \
    printf 'class WarmUp { }\n' > src/main/java/WarmUp.java && \
    printf 'class WarmUpTest { @org.junit.jupiter.api.Test void warmUp() { } }\n' > src/test/java/WarmUpTest.java && \
    for attempt in 1 2 3; do \
      mvn --batch-mode --quiet dependency:go-offline package && rm -rf src target && exit 0; \
      echo "Maven Central did not give the dependencies at attempt $attempt" >&2; \
      [ "$attempt" = 3 ] || sleep 30; \
    done; exit 1
COPY extension/src ./src
RUN mvn --batch-mode --quiet --offline package

# keycloak-config-cli, in the build nearest to this version of Keycloak it publishes (26.5.5, the last);
# only its jar is taken.
FROM ${WATERFALL_MIRROR}adorsys/keycloak-config-cli:6.5.1-26.5.5@sha256:0955d98c8a341898b7aa177477edf8a1e90569ae50bbe7598141c1270b773274 AS realm-applier

# Keycloak runs as its own unprivileged user, 1000, that of its image, said again at the end of the
# stage: the image never runs as root, whatever its base sets.
FROM ${WATERFALL_MIRROR}keycloak/keycloak:26.8.2-2@sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0 AS production
COPY --from=extension /build/target/waterfall-keycloak-extension.jar /opt/keycloak/providers/
COPY themes/ /opt/keycloak/themes/
# The options Keycloak fixes at build time: started with --optimized, it does not rebuild. Under
# /auth, where the front end of the platform serves it (EP-03, "Déploiement de démonstration").
RUN /opt/keycloak/bin/kc.sh build --db=postgres --health-enabled=true --http-relative-path=/auth
COPY --from=realm-applier /app/keycloak-config-cli.jar /opt/keycloak-config-cli/keycloak-config-cli.jar
COPY realm/ /opt/keycloak/realm/
COPY apply-realm.sh /opt/keycloak/bin/apply-realm
COPY realm-service.sh /opt/keycloak/bin/realm-service
COPY trust-root.sh /opt/keycloak/bin/trust-root.sh
USER 1000
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
CMD ["start", "--optimized"]
