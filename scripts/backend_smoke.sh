#!/usr/bin/env bash
  set -euo pipefail

  BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

  health_status=$(curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/health")
  models_status=$(curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/models")
  ask_status=$(curl -sS -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/ask" \
    -H "Content-Type: application/json" \
    -d '{"question":"Wie funktioniert das?"}')

  [[ "$health_status" == "200" ]]
  [[ "$models_status" == "200" ]]
  [[ "$ask_status" == "401" ]]

  echo "Backend smoke test passed"
  echo "/health: $health_status"
  echo "/models: $models_status"
  echo "/ask without authentication: $ask_status"