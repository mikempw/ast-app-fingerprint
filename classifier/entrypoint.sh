#!/usr/bin/env sh
set -e

: "${RULES_PATH:=/rules_cache/generated/combined_rules.yaml}"

echo "[entrypoint] RULES_PATH=$RULES_PATH"
if [ ! -f "$RULES_PATH" ]; then
  echo "[entrypoint] waiting up to 60s for rules..."
  i=0
  while [ $i -lt 60 ]; do
    [ -f "$RULES_PATH" ] && break
    sleep 1
    i=$((i+1))
  done
fi

if [ ! -f "$RULES_PATH" ] || [ ! -s "$RULES_PATH" ]; then
  echo "[entrypoint] rules not found; falling back to /app/rules.yaml"
  export RULES_PATH="/app/rules.yaml"
fi

exec python /app/app.py
