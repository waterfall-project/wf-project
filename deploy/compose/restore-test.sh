#!/bin/sh
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# The test of a restoration under Compose (US-2930, WF-EXP-0060), which a planned task of the host
# runs once a month (docs/exploitation/test-de-restauration.md): it starts the ephemeral platform
# of compose.restore-test.yaml beside the production, waits for the test to end, writes what the
# test said, then removes the ephemeral platform with its volumes, whatever happened. Its status is
# the test's: 0 if it succeeded, another if it failed or could not run; the production inscribes
# the outcome all the same, as the status screen shows it.
#
# WATERFALL_PRODUCTION_PROJECT names the project of Compose of the production, waterfall unless set.
set -u
cd "$(dirname "$0")" || exit 1

# The password of the ephemeral platform, drawn at each test, which dies with it.
WATERFALL_RESTORE_TEST_PASSWORD=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
export WATERFALL_RESTORE_TEST_PASSWORD

compose() {
  docker compose --file compose.restore-test.yaml --profile restore-test "$@"
}

# Whatever happens — the test ends, fails, is interrupted (INT, TERM) — the ephemeral platform is
# removed with its volumes: it holds a copy not anonymised, and a restoration of the production.
remove() {
  compose down --volumes --remove-orphans
}
trap remove EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# A command Compose runs, in the background and waited for: the shell takes a signal at once, not
# once the command has ended, which `compose wait` would not do for hours.
run() {
  "$@" &
  waited=$!
  wait "$waited"
}

# What a test interrupted before left (its copy not anonymised, a volume whose roles have another
# password than the one drawn above) goes first: the test starts from nothing.
remove

# Keycloak and the API start once the test has restored their databases: up returns then, or as
# soon as the test stops before.
run compose up --detach --quiet-pull
run compose wait restore-test
status=$?
compose logs --no-color --no-log-prefix restore-test
exit "$status"
