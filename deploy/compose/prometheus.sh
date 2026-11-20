#!/bin/sh
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# Starts Prometheus under Compose (US-2880, WF-OBS-0030): writes the operating parameters of the
# environment in its configuration and in the rules of the alerts — the port of the metrics and the
# three thresholds —, then hands over to Prometheus, with the arguments it is given. A parameter that
# is not one stops the start, with 2, naming it: an alert at a threshold nobody chose is worse than
# none. Run at every start, so that a threshold changed in .env is the one evaluated.
#
# Usage: prometheus.sh [ARGUMENT…]. MODELS, the folder of prometheus.yml and prometheus-alerts.yml,
# /etc/waterfall by default; RENDERED, where they are written, /prometheus/waterfall by default;
# PROMETHEUS, what is started, /bin/prometheus by default.
set -eu

MODELS=${MODELS:-/etc/waterfall}
RENDERED=${RENDERED:-/prometheus/waterfall}
PROMETHEUS=${PROMETHEUS:-/bin/prometheus}

refuse() {
	echo "prometheus.sh: $1 must be $2: '$3'" >&2
	exit 2
}

# A whole number above zero; a ratio above 0, at most 1.
WHOLE='^[1-9][0-9]*$'
RATIO='^(0?\.[0-9]*[1-9][0-9]*|1(\.0*)?)$'

substitutions=""
for parameter in \
	"WATERFALL_METRICS_PORT:$WHOLE:a port, from 1 to 65535" \
	"WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS:$WHOLE:a whole number of seconds above zero" \
	"WATERFALL_ERROR_RATE_WINDOW_SECONDS:$WHOLE:a whole number of seconds above zero" \
	"WATERFALL_STORAGE_USAGE_THRESHOLD:$RATIO:a ratio above 0, at most 1" \
	"WATERFALL_ERROR_RATE_THRESHOLD:$RATIO:a ratio above 0, at most 1"; do
	name=${parameter%%:*}
	rest=${parameter#*:}
	pattern=${rest%%:*}
	meaning=${rest#*:}
	eval "value=\${$name-}"
	printf '%s\n' "$value" | grep -Eq "$pattern" || refuse "$name" "$meaning" "$value"
	if [ "$name" = WATERFALL_METRICS_PORT ] && [ "$value" -gt 65535 ]; then
		refuse "$name" "$meaning" "$value"
	fi
	# Digits and a point alone, checked above: nothing sed reads otherwise.
	substitutions="$substitutions;s|\${$name}|$value|g"
done

mkdir -p "$RENDERED"
sed -e "${substitutions#;}" "$MODELS/prometheus.yml" >"$RENDERED/prometheus.yml"
sed -e "${substitutions#;}" "$MODELS/prometheus-alerts.yml" >"$RENDERED/alerts.yml"

exec "$PROMETHEUS" --config.file="$RENDERED/prometheus.yml" "$@"
