#!/usr/bin/env bash

set -euo pipefail
PWD="$(pwd)"

ps -ocommand= -p "${PPID}"

if ! scripts/check-secrets.sh; then
  echo "scripts/check-secrets.sh failed"
  exit 1
fi

echo ""
echo "check formatting ..."
echo ""

if ! make isort-check; then
  echo ""
  echo "isort-check failed"
  echo ""
  exit 1
fi

if ! make black-check; then
  echo ""
  echo "black-check failed"
  echo ""
  exit 1
fi

echo ""
