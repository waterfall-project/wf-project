#!/bin/sh
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only

# Creates each bucket of STORAGE_BUCKETS on the object storage at STORAGE_ADDRESS, unless it is
# there, by the CreateBucket of S3 signed with the key of the platform: the standard operation any
# storage serves. The key reaches curl by a file of its configuration, never by its command line.
set -eu

configuration=$(mktemp)
trap 'rm -f "$configuration"' EXIT
printf 'user = "%s:%s"\n' "$STORAGE_ACCESS_KEY" "$STORAGE_SECRET" > "$configuration"

for bucket in $STORAGE_BUCKETS; do
	status=$(curl --silent --output /dev/null --write-out '%{http_code}' \
		--config "$configuration" --aws-sigv4 "aws:amz:us-east-1:s3" \
		--request PUT "$STORAGE_ADDRESS/$bucket")
	case $status in
	200 | 409) echo "bucket $bucket: ready" ;;
	*)
		echo "bucket $bucket: refused ($status)" >&2
		exit 1
		;;
	esac
done
