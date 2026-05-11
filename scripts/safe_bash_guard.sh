#!/usr/bin/env bash
set -euo pipefail

command_text="${*:-}"

if [[ -z "${command_text}" ]]; then
  echo "Usage: scripts/safe_bash_guard.sh <command string>"
  exit 2
fi

dangerous_patterns=(
  "rm[[:space:]]+-rf[[:space:]]+/"
  "rm[[:space:]]+-rf[[:space:]]+\\."
  "git[[:space:]]+reset[[:space:]]+--hard"
  "git[[:space:]]+clean[[:space:]]+-fd"
  "git[[:space:]]+push[[:space:]].*--force"
  "drop[[:space:]]+database"
  "truncate[[:space:]]+table"
  "supabase[[:space:]]+db[[:space:]]+reset"
  "prisma[[:space:]]+migrate[[:space:]]+reset"
)

normalized="$(printf '%s' "${command_text}" | tr '[:upper:]' '[:lower:]')"

for pattern in "${dangerous_patterns[@]}"; do
  if [[ "${normalized}" =~ ${pattern} ]]; then
    echo "BLOCKED: command matches dangerous pattern: ${pattern}"
    echo "Manual confirmation is required before running this command."
    exit 1
  fi
done

echo "SAFE: no dangerous pattern detected"
