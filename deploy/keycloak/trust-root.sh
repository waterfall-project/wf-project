#!/bin/sh
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# Keycloak in TLS (US-2840), for apply-realm and realm-service, beside which it is: given the root
# of the authority of the platform, WATERFALL_TLS_AUTHORITY, the Java of keycloak-config-cli and of
# kcadm checks the certificate of Keycloak against it alone, by a store of trust made from it here —
# Java reads no root in PEM. Writes on its output what JAVA_TOOL_OPTIONS takes to read it; nothing
# when no root is given, or when JAVA_TOOL_OPTIONS names a store already — realm-service made it,
# then runs apply-realm, which does not make it again; the chart runs apply-realm alone, in the Job
# of its hooks, which makes it then.
#
# The store holds the root alone, no secret, and is protected by no password: neither its
# certificates encrypted nor its integrity sealed, so that Java reads it without one. keytool asks
# one all the same: drawn here, given by the environment of keytool alone, and forgotten. A root it
# cannot read stops it, saying so, and its caller with it.
set -eu

[ -n "${WATERFALL_TLS_AUTHORITY:-}" ] || exit 0
case "${JAVA_TOOL_OPTIONS:-}" in
    *-Djavax.net.ssl.trustStore=*) exit 0 ;;
esac
TRUST=${TMPDIR:-/tmp}/realm-trust.p12
rm -f "$TRUST"
if ! said=$(STORE_PASSWORD=$(od -An -tx1 -N16 /dev/urandom | tr -d ' \n') keytool \
        -J-Dkeystore.pkcs12.certProtectionAlgorithm=NONE -J-Dkeystore.pkcs12.macAlgorithm=NONE \
        -importcert -noprompt -alias platform -file "$WATERFALL_TLS_AUTHORITY" \
        -keystore "$TRUST" -storetype PKCS12 -storepass:env STORE_PASSWORD 2>&1); then
    printf '%s\n' "$said" >&2
    echo "trust-root: the root $WATERFALL_TLS_AUTHORITY cannot be read" >&2
    exit 1
fi
# The store read back without a password, as Java will (#4511): a keytool that ignores the two
# options — a JDK older than 17 — protects the root with the password drawn, and the store, read
# without it, holds no certificate; Java would then refuse Keycloak's without saying why.
if ! keytool -list -alias platform -keystore "$TRUST" -storetype PKCS12 \
        </dev/null >/dev/null 2>&1; then
    echo "trust-root: the store of trust $TRUST is not readable without a password: this keytool" \
        "ignores keystore.pkcs12.certProtectionAlgorithm and macAlgorithm (JDK 17 or later reads" \
        "them)" >&2
    exit 1
fi
printf ' -Djavax.net.ssl.trustStore=%s -Djavax.net.ssl.trustStoreType=PKCS12' "$TRUST"
