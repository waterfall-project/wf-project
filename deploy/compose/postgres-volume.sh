#!/bin/sh
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# Refuses the volume of PostgreSQL when it holds the data of another major version than the one
# the platform runs (US-1130): `postgres-volume.sh <remedy> [<directory>]`, the directory
# /var/lib/postgresql by default, where the volume is mounted, read-only. The platform does not take
# the data of another major over, and says what to do instead: the remedy, which Compose passes.
#
# Two layouts are refused. A PG_VERSION at the root of the volume is the data of an image 17 or
# older, which kept them at /var/lib/postgresql/data, where the volume was mounted then. A
# <major>/docker/PG_VERSION whose major is not EXPECTED is the layout of the images since 18, of
# another version: an image 19 would find 18/docker and make an empty 19/docker beside it, without
# a word. An empty volume, or one of EXPECTED, passes silently.
set -eu

EXPECTED=18

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
	echo "usage: postgres-volume.sh <remedy> [<directory>]" >&2
	exit 2
fi
remedy=$1
volume=${2:-/var/lib/postgresql}

# The version the data say they are of — "unknown" when the file is empty or cannot be read, the
# refusal being owed all the same —, the remedy, and the refusal.
refuse() {
	found=$(cat "$1" 2>/dev/null) || found=
	found=${found:-"unknown (PG_VERSION is empty or unreadable)"}
	echo "The volume of PostgreSQL holds the data of PostgreSQL $found, at $1;" \
		"the platform runs PostgreSQL $EXPECTED and does not take them over. $remedy" >&2
	exit 1
}

if [ -e "$volume/PG_VERSION" ]; then
	refuse "$volume/PG_VERSION"
fi
for data in "$volume"/*/docker; do
	if [ -e "$data/PG_VERSION" ] && [ "$data" != "$volume/$EXPECTED/docker" ]; then
		refuse "$data/PG_VERSION"
	fi
done
