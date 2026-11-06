#!/bin/sh
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The entrypoint of the directory of test (US-1150). At the first start, on empty volumes, it makes
# the configuration of slapd by slapadd -n0 — the schemas core, cosine and inetorgperson, a base
# mdb of suffix dc=waterfall,dc=test, its administrator cn=admin,dc=waterfall,dc=test, whose
# password, a development value, comes from WATERFALL_DIRECTORY_ADMIN_PASSWORD —, then loads the
# seed, WATERFALL_DIRECTORY_SEED, by slapadd -n1, which gives each entry its entryUUID. Then, and at
# every later start, it runs slapd in the foreground on ldap:/// without TLS, as openldap. A later
# start finds the configuration and loads nothing: the person keeps her entryUUID, and Keycloak,
# which keeps the first, her account.
#
# The configuration is made aside and copied into its volume once the seed is loaded, its
# cn=config.ldif last. Before the seed is loaded, a marker is laid in the volume of the data, and
# removed only once the configuration is copied: a first start interrupted midway leaves the marker
# and no configuration, so the data left there were never served — Keycloak has read no entryUUID
# from them — and are emptied, the seed loaded again. Without configuration and without marker, the
# volume of the data is emptied only if it is empty already. Data without marker and without
# configuration are a directory that has served — its volume of configuration is lost, and seeded
# again it would give her people other entryUUIDs, and Keycloak other accounts —: the script
# refuses, and says the remedy. The volumes the image of osixia made, on a workstation of before,
# hold both: slapd starts on them as they are. A marker left beside a configuration — a stop
# between the copy and the removal — is removed at the start, before slapd runs: were the volume of
# the configuration lost later, it would else license emptying data that served.
set -eu

CONFIG=/etc/ldap/slapd.d
DATA=/var/lib/ldap
SEED=${WATERFALL_DIRECTORY_SEED:-/seed/directory.ldif}
SUFFIX=dc=waterfall,dc=test
MARKER=$DATA/.seeding

configure() {
    if [ -e "$MARKER" ]; then
        # A first start interrupted before the copy of the configuration: slapd never served them.
        echo "openldap: the seeding of $DATA was interrupted; emptying $DATA and seeding again" >&2
    elif [ -n "$(ls -A "$DATA")" ]; then
        echo "openldap: $DATA holds data that served, and $CONFIG no configuration;" >&2
        echo "openldap: refusing to seed again, which would give its people other entryUUIDs." >&2
        echo "openldap: Drop the data: make service-down WATERFALL_RESET_DATA=yes." >&2
        exit 1
    fi
    rm -rf "${DATA:?}"/* "${DATA:?}"/.[!.]* "${DATA:?}"/..?*
    touch "$MARKER"
    password=${WATERFALL_DIRECTORY_ADMIN_PASSWORD:?export WATERFALL_DIRECTORY_ADMIN_PASSWORD}
    # The password goes to slappasswd by a pipe, never a command line.
    hash=$(printf '%s' "$password" | slappasswd -T /dev/stdin)
    staging=$(mktemp -d)
    slapadd -n0 -F "$staging" <<EOF
dn: cn=config
objectClass: olcGlobal
cn: config
olcPidFile: /run/slapd/slapd.pid

dn: cn=module{0},cn=config
objectClass: olcModuleList
cn: module{0}
olcModulePath: /usr/lib/ldap
olcModuleLoad: back_mdb

dn: cn=schema,cn=config
objectClass: olcSchemaConfig
cn: schema

include: file:///etc/ldap/schema/core.ldif

include: file:///etc/ldap/schema/cosine.ldif

include: file:///etc/ldap/schema/inetorgperson.ldif

dn: olcDatabase={-1}frontend,cn=config
objectClass: olcDatabaseConfig
objectClass: olcFrontendConfig
olcDatabase: {-1}frontend

dn: olcDatabase={0}config,cn=config
objectClass: olcDatabaseConfig
olcDatabase: {0}config

dn: olcDatabase={1}mdb,cn=config
objectClass: olcDatabaseConfig
objectClass: olcMdbConfig
olcDatabase: {1}mdb
olcDbDirectory: $DATA
olcSuffix: $SUFFIX
olcRootDN: cn=admin,$SUFFIX
olcRootPW: $hash
olcDbIndex: objectClass eq
olcDbIndex: uid eq
olcDbIndex: entryUUID eq
olcAccess: {0}to attrs=userPassword by self write by anonymous auth by * none
olcAccess: {1}to * by self read by * none
EOF
    slapadd -n1 -F "$staging" -l "$SEED"
    rm -rf "$CONFIG/cn=config"
    cp -R "$staging/cn=config" "$CONFIG/"
    cp "$staging/cn=config.ldif" "$CONFIG/"
    rm -f "$MARKER"
    rm -rf "$staging"
}

if [ ! -e "$CONFIG/cn=config.ldif" ]; then
    configure
else
    # A stop between the copy of the configuration and the removal of the marker leaves both.
    rm -f "$MARKER"
fi
# At every start: the files are openldap's whoever wrote them — slapadd, as root, or the image of
# before, under another user.
chown -R openldap:openldap "$CONFIG" "$DATA"

exec slapd -d none -h ldap:/// -u openldap -g openldap -F "$CONFIG"
