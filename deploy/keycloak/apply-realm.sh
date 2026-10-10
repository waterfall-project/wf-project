#!/bin/sh
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# Applies the realm files to the Keycloak that KEYCLOAK_URL designates, with keycloak-config-cli
# (#215): at each deployment, whether the files changed or not, so that a setting changed by
# hand in the console comes back to what the files say. The administrator signs in with
# KEYCLOAK_USER and KEYCLOAK_PASSWORD; the files take their secrets from `$(env:…)`.
#
# Only what the files declare is managed: the kinds of resources the console adds — the
# directory federated, the external providers and their mappers — are never removed, even by a
# file that declares some, so that the development files do not undo what an administrator added.
set -eu

exec java -jar /opt/keycloak-config-cli/keycloak-config-cli.jar \
    --keycloak.availability-check.enabled=true \
    --import.files.locations="${WATERFALL_REALM_FILES:-file:/opt/keycloak/realm/*.yaml}" \
    --import.cache.enabled=false \
    --import.var-substitution.enabled=true \
    --import.managed.component=no-delete \
    --import.managed.sub-component=no-delete \
    --import.managed.identity-provider=no-delete \
    --import.managed.identity-provider-mapper=no-delete \
    "$@"
