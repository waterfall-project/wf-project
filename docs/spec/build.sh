#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
# Regenerate waterfall-spec.md from the Word and draw.io sources, and show what
# changed since the previous generation.
set -euo pipefail

cd "$(dirname "$0")"
output="waterfall-spec.md"
previous=".build/waterfall-spec.previous.md"

mkdir -p .build
[[ -f "$output" ]] && cp "$output" "$previous"

python3 tools/build.py "$@"

if [[ -f "$previous" ]]; then
  if diff -q "$previous" "$output" >/dev/null; then
    echo "  = unchanged since the previous generation"
  else
    added=$(diff "$previous" "$output" | grep -c '^>' || true)
    removed=$(diff "$previous" "$output" | grep -c '^<' || true)
    echo "  ~ ${added} line(s) added, ${removed} removed — details: diff $previous $output"
  fi
fi
