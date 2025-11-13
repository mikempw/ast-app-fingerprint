#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-up}"

if [[ "$MODE" == "down" ]]; then
  docker compose down -v
  exit 0
fi

if [[ "$MODE" == "rebuild" ]]; then
  docker compose build --no-cache
fi

if [[ "$MODE" == "llm" ]]; then
  USE_LLM=1 docker compose --profile ollama up -d --build
else
  USE_LLM=0 docker compose up -d --build
fi

if [[ "$MODE" == "test" ]]; then
  curl -s http://localhost:8089/classify -H 'Content-Type: application/json' --data-binary @sample/sample_requests.json | jq .
fi
