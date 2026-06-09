#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_env() {
  if [[ -z "${!1:-}" ]]; then
    echo "Missing required environment variable: $1" >&2
    exit 1
  fi
}

require_command mvn
require_command npm
require_command sonar-scanner

require_env SONAR_TOKEN
require_env SONAR_ORGANIZATION

cd "$ROOT_DIR"

echo "Building auth-service..."
(cd auth-service && mvn -B -DskipTests package)

echo "Building upload-service..."
(cd upload-service && mvn -B -DskipTests package)

echo "Building frontend..."
(cd frontend && npm ci && npm run build)

echo "Running SonarCloud scanner..."
sonar-scanner -Dsonar.organization="${SONAR_ORGANIZATION}"
