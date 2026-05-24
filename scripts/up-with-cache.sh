#!/usr/bin/env bash
set -euo pipefail

previous_image="${PREVIOUS_BACKEND_IMAGE:-aiic-project-backend:latest}"

if docker image inspect "$previous_image" >/dev/null 2>&1; then
  echo "Using local backend image cache: $previous_image"
  exec docker compose -f docker-compose.yml -f docker-compose.local-cache.yml --progress plain up -d --build
fi

echo "No local backend image cache found; using cold full-stack build path."
exec docker compose --progress plain up -d --build
