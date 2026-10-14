#!/bin/bash
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The service keycloak-realm (#955): applies the realm of the installation at its start, by the
# command it is given — apply-realm, or what a platform adds to it —, then stays, and applies it
# again whenever the service of the restoration asks, over the database of Keycloak it has just
# restored: the clients, their secrets and the addresses of the front come back to those of the
# installation, the accounts and their passwords stay those of the backup.
#
# A request is a file <name>.request in WATERFALL_REALM_REQUESTS, a folder this service shares with
# the service of the restoration alone; the answer, <name>.done or <name>.failed. The administrator
# of the realm master being then that of the backup, the realm is applied as a temporary
# administrator that kc.sh bootstrap-admin makes here, in a container of its own — the server's
# holds the port of management —, on the database of Keycloak (KC_DB_URL, KC_DB_USERNAME,
# KC_DB_PASSWORD), the image built for --optimized (#991). The administrator of master, KEYCLOAK_USER,
# gets back the password of the installation, KEYCLOAK_PASSWORD, and the temporary one is removed.
# Its secret is drawn here, and goes to its commands by their environment, never a command line.
set -eu

REQUESTS=${WATERFALL_REALM_REQUESTS:?set WATERFALL_REALM_REQUESTS}
SERVER=${KEYCLOAK_URL:?set KEYCLOAK_URL}
ADMINISTRATOR=${KEYCLOAK_USER:?set KEYCLOAK_USER}
APPLIED=/tmp/realm-applied
KC=/opt/keycloak/bin/kc.sh
KCADM=/opt/keycloak/bin/kcadm.sh

drawn() {
    od -An -tx1 -N"$1" /dev/urandom | tr -d ' \n'
}

# Applies the realm again as a temporary administrator, then removes it; answers the request $1.
reapply() {
    local name=$1 client secret config id outcome=failed
    shift
    client="waterfall-realm-$(drawn 6)"
    secret=$(drawn 32)
    config=$(mktemp)
    if TEMPORARY_ID=$client TEMPORARY_SECRET=$secret "$KC" bootstrap-admin service --optimized \
            --no-prompt --client-id:env=TEMPORARY_ID --client-secret:env=TEMPORARY_SECRET \
        && env -u KEYCLOAK_USER -u KEYCLOAK_PASSWORD KEYCLOAK_GRANTTYPE=client_credentials \
            KEYCLOAK_CLIENTID="$client" KEYCLOAK_CLIENTSECRET="$secret" "$@" \
        && KC_CLI_CLIENT_SECRET=$secret "$KCADM" config credentials --config "$config" \
            --server "$SERVER" --realm master --client "$client" \
        && KC_CLI_PASSWORD=$KEYCLOAK_PASSWORD "$KCADM" set-password --config "$config" \
            --target-realm master --username "$ADMINISTRATOR"
    then
        outcome="done"
    fi
    id=$("$KCADM" get clients --config "$config" --target-realm master -q "clientId=$client" \
        --fields id --format csv --noquotes 2>/dev/null || true)
    if [ -z "$id" ] || ! "$KCADM" delete "clients/$id" --config "$config" --target-realm master
    then
        echo "realm-service: the temporary administrator $client is not removed" >&2
        outcome=failed
    fi
    rm -f "$config"
    : > "$REQUESTS/$name.$outcome"
    echo "realm-service: $outcome ($name)" >&2
}

rm -f "$APPLIED"
"$@"
touch "$APPLIED"
while :; do
    for request in "$REQUESTS"/*.request; do
        [ -e "$request" ] || continue
        name=$(basename "$request" .request)
        rm -f "$request"
        echo "realm-service: the realm is applied again ($name)" >&2
        reapply "$name" "$@"
    done
    sleep 1
done
