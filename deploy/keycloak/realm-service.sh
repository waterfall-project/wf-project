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
# the service of the restoration alone; the answer, <name>.done or <name>.failed.
#
# Each time, at its start too, the realm is applied as a temporary administrator that kc.sh
# bootstrap-admin makes here, in a container of its own — the server's holds the port of
# management —, on the database of Keycloak (KC_DB_URL, KC_DB_USERNAME, KC_DB_PASSWORD), the image
# built for --optimized (#991): the administrator of the realm master may be that of a backup, its
# password not the installation's. Restarting keycloak, then keycloak-realm, thus always gives back
# the realm of the installation, a restoration interrupted included. The administrator of master,
# KEYCLOAK_USER, gets back the password of the installation, KEYCLOAK_PASSWORD; then every temporary
# administrator is removed, this one and any a run stopped midway left. Its secret is drawn here,
# and goes to its commands by their environment, never a command line.
set -eu

REQUESTS=${WATERFALL_REALM_REQUESTS:?set WATERFALL_REALM_REQUESTS}
SERVER=${KEYCLOAK_URL:?set KEYCLOAK_URL}
ADMINISTRATOR=${KEYCLOAK_USER:?set KEYCLOAK_USER}
APPLIED=/tmp/realm-applied
# Where kcadm keeps the session of the temporary administrator: removed after each application,
# at the start, and when the service stops.
CONFIG=/tmp/realm-service.kcadm
# What the identifier of a temporary administrator begins with.
TEMPORARY=waterfall-realm-
KC=/opt/keycloak/bin/kc.sh
KCADM=/opt/keycloak/bin/kcadm.sh

trap 'rm -f "$CONFIG"' EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

drawn() {
    od -An -tx1 -N"$1" /dev/urandom | tr -d ' \n'
}

# Removes from master every temporary administrator, as the one signed in to kcadm, $1: the others
# first, then itself, after which kcadm is refused.
remove_temporaries() {
    local own=$1 clients id client mine="" left=0
    clients=$("$KCADM" get clients --config "$CONFIG" --target-realm master \
        -q "clientId=$TEMPORARY" -q search=true --fields id,clientId --format csv --noquotes) \
        || return 1
    while IFS=, read -r id client; do
        case $client in
            "$own") mine=$id ;;
            "$TEMPORARY"*)
                "$KCADM" delete "clients/$id" --config "$CONFIG" --target-realm master || left=1
                ;;
        esac
    done <<< "$clients"
    [ -n "$mine" ] && "$KCADM" delete "clients/$mine" --config "$CONFIG" --target-realm master \
        || left=1
    return "$left"
}

# Applies the realm by the command "$@" as a temporary administrator, then removes it.
applied() {
    local client secret outcome=0
    client="$TEMPORARY$(drawn 6)"
    secret=$(drawn 32)
    rm -f "$CONFIG"
    if ! TEMPORARY_ID=$client TEMPORARY_SECRET=$secret "$KC" bootstrap-admin service --optimized \
            --no-prompt --client-id:env=TEMPORARY_ID --client-secret:env=TEMPORARY_SECRET
    then
        echo "realm-service: no temporary administrator is made" >&2
        return 1
    fi
    (
        unset KEYCLOAK_USER KEYCLOAK_PASSWORD
        export KEYCLOAK_GRANTTYPE=client_credentials KEYCLOAK_CLIENTID=$client \
            KEYCLOAK_CLIENTSECRET=$secret
        "$@"
    ) || outcome=1
    if KC_CLI_CLIENT_SECRET=$secret "$KCADM" config credentials --config "$CONFIG" \
            --server "$SERVER" --realm master --client "$client"
    then
        if [ "$outcome" = 0 ]; then
            KC_CLI_PASSWORD=$KEYCLOAK_PASSWORD "$KCADM" set-password --config "$CONFIG" \
                --target-realm master --username "$ADMINISTRATOR" || outcome=1
        fi
        remove_temporaries "$client" || {
            echo "realm-service: a temporary administrator is not removed" >&2
            outcome=1
        }
    else
        echo "realm-service: the temporary administrator $client is not removed" >&2
        outcome=1
    fi
    rm -f "$CONFIG"
    return "$outcome"
}

rm -f "$APPLIED" "$CONFIG"
if ! applied "$@"; then
    echo "realm-service: the realm is not applied" >&2
    exit 1
fi
touch "$APPLIED"
while :; do
    for request in "$REQUESTS"/*.request; do
        [ -e "$request" ] || continue
        name=$(basename "$request" .request)
        rm -f "$request"
        echo "realm-service: the realm is applied again ($name)" >&2
        outcome=failed
        if applied "$@"; then
            outcome="done"
        fi
        : > "$REQUESTS/$name.$outcome"
        echo "realm-service: $outcome ($name)" >&2
    done
    sleep 1
done
