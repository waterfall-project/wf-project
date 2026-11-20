#!/bin/sh
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# Starts Alertmanager (US-2880, WF-OBS-0030): writes its configuration from the environment, then
# hands over to it, with the arguments it is given. Alertmanager notifies each alert of Prometheus by
# e-mail, through the mail server the environment names, WATERFALL_ALERT_SMTP_HOST; without one, it
# notifies nothing, and the alerts stay on the status screen and the dashboard. A value that is not
# what it must be stops the start, with 2, naming it: a notification sent to an address nobody chose
# is worse than none. Run at every start, so that a value changed in .env is the one used. The chart
# starts it the same way (templates/alertmanager.yaml).
#
# Usage: alertmanager.sh [ARGUMENT…]. RENDERED, where the configuration is written,
# /alertmanager/waterfall by default; ALERTMANAGER, what is started, /bin/alertmanager by default.
# The variables: WATERFALL_ALERT_SMTP_HOST (host:port of the server), WATERFALL_ALERT_SMTP_FROM,
# WATERFALL_ALERT_RECIPIENT, WATERFALL_ALERT_SMTP_REQUIRE_TLS (true by default), and, when the server
# asks to sign in, WATERFALL_ALERT_SMTP_USER and WATERFALL_ALERT_SMTP_PASSWORD.
set -eu

RENDERED=${RENDERED:-/alertmanager/waterfall}
ALERTMANAGER=${ALERTMANAGER:-/bin/alertmanager}

refuse() {
	echo "alertmanager.sh: $1 must be $2" >&2
	exit 2
}

# A value that matches a pattern, on one line: what a line of YAML in single quotes holds as it is.
check() {
	# grep reads line by line: a value of several lines, one of them valid, would pass it.
	case $2 in
	*'
'*) refuse "$1" "$4" ;;
	esac
	printf '%s\n' "$2" | grep -Eq "$3" || refuse "$1" "$4"
}

host=${WATERFALL_ALERT_SMTP_HOST:-}
sender=${WATERFALL_ALERT_SMTP_FROM:-}
recipient=${WATERFALL_ALERT_RECIPIENT:-}
tls=${WATERFALL_ALERT_SMTP_REQUIRE_TLS:-true}
user=${WATERFALL_ALERT_SMTP_USER:-}
password=${WATERFALL_ALERT_SMTP_PASSWORD:-}
address='^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+$'

mkdir -p "$RENDERED"
# A password of an earlier start, which this one may not use, is not left behind.
rm -f "$RENDERED/smtp-password"
umask 077
{
	cat <<'YAML'
route:
  receiver: operator
  group_by: [alertname, component]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
YAML
	if [ -z "$host" ]; then
		printf 'receivers:\n  - name: operator\n'
		echo "alertmanager.sh: no WATERFALL_ALERT_SMTP_HOST: no alert is notified" >&2
	else
		check WATERFALL_ALERT_SMTP_HOST "$host" \
			'^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?:[0-9]{1,5}$' \
			"the address and the port of a mail server, host:port"
		check WATERFALL_ALERT_SMTP_FROM "$sender" "$address" "an e-mail address"
		check WATERFALL_ALERT_RECIPIENT "$recipient" "$address" "an e-mail address"
		check WATERFALL_ALERT_SMTP_REQUIRE_TLS "$tls" '^(true|false)$' "true or false"
		printf "global:\n  smtp_smarthost: '%s'\n  smtp_from: '%s'\n  smtp_require_tls: %s\n" \
			"$host" "$sender" "$tls"
		if [ -n "$user" ]; then
			check WATERFALL_ALERT_SMTP_USER "$user" '^[A-Za-z0-9._%+@-]+$' \
				"letters, digits and . _ % + @ - alone"
			# The password is read from a file of its own, never written in the configuration.
			case $password in
			'') refuse WATERFALL_ALERT_SMTP_PASSWORD "set when WATERFALL_ALERT_SMTP_USER is" ;;
			*'
'*) refuse WATERFALL_ALERT_SMTP_PASSWORD "a single line" ;;
			esac
			printf '%s' "$password" >"$RENDERED/smtp-password"
			printf "  smtp_auth_username: '%s'\n  smtp_auth_password_file: %s\n" \
				"$user" "$RENDERED/smtp-password"
		fi
		printf "receivers:\n  - name: operator\n    email_configs:\n      - to: '%s'\n        send_resolved: true\n" \
			"$recipient"
	fi
} >"$RENDERED/alertmanager.yml"

exec "$ALERTMANAGER" --config.file="$RENDERED/alertmanager.yml" "$@"
