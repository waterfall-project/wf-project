#!/usr/bin/env bash
# Régénère waterfall-spec.md depuis les sources Word et draw.io,
# et montre ce qui a changé depuis la génération précédente.
set -euo pipefail

cd "$(dirname "$0")"
sortie="waterfall-spec.md"
precedent=".build/waterfall-spec.precedent.md"

mkdir -p .build
[[ -f "$sortie" ]] && cp "$sortie" "$precedent"

python3 tools/build.py "$@"

if [[ -f "$precedent" ]]; then
  if diff -q "$precedent" "$sortie" >/dev/null; then
    echo "  = inchangé depuis la génération précédente"
  else
    ajouts=$(diff "$precedent" "$sortie" | grep -c '^>' || true)
    retraits=$(diff "$precedent" "$sortie" | grep -c '^<' || true)
    echo "  ~ ${ajouts} ligne(s) ajoutée(s), ${retraits} retirée(s) — détail : diff $precedent $sortie"
  fi
fi
