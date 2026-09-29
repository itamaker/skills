#!/usr/bin/env bash
# Deploy the remote-browser Worker under a chosen name.
# Usage: WORKER_TOKEN=<secret> deploy.sh <worker-name> [target-dir]
# Env:   FORCE=1    allow overwriting a Worker that already exists
#        DRY_RUN=1  copy, install and typecheck only; no secret upload, no deploy
# Exit:  2 = not logged in to Cloudflare, 3 = name already taken, 4 = bad input
set -euo pipefail

NAME="${1:-}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/remote-browser"

if [[ ! "$NAME" =~ ^[a-z0-9][a-z0-9-]{0,62}$ ]]; then
  echo "Invalid worker name '$NAME': use lowercase letters, digits and dashes (max 63 chars)." >&2
  exit 4
fi
if [[ -z "${WORKER_TOKEN:-}" ]]; then
  echo "WORKER_TOKEN is not set." >&2
  exit 4
fi
if [[ ${#WORKER_TOKEN} -lt 16 ]]; then
  echo "WORKER_TOKEN must be at least 16 characters." >&2
  exit 4
fi

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
if (( NODE_MAJOR < 18 )); then
  echo "Node.js 18 or newer is required (found major version $NODE_MAJOR)." >&2
  exit 4
fi

TARGET="${2:-$HOME/.local/share/remote-browser/$NAME}"
mkdir -p "$TARGET"
cp -R "$SKILL_DIR/template/." "$TARGET/"
sed -i "s/__WORKER_NAME__/$NAME/g" "$TARGET/wrangler.jsonc" "$TARGET/package.json"
cd "$TARGET"

npm install --no-audit --no-fund
npx wrangler types
npx tsc --noEmit

if [[ "${DRY_RUN:-}" == "1" ]]; then
  echo "DRY_RUN: typecheck passed in $TARGET; skipped deploy."
  exit 0
fi

if ! npx wrangler whoami 2>&1 | grep -q "You are logged in"; then
  echo "Not logged in to Cloudflare. Run: npx --yes wrangler@4 login" >&2
  exit 2
fi

if npx wrangler deployments list --name "$NAME" >/dev/null 2>&1 && [[ "${FORCE:-}" != "1" ]]; then
  echo "A Worker named '$NAME' already exists in this account. Pick another name, or set FORCE=1 to overwrite it." >&2
  exit 3
fi

printf '%s' "$WORKER_TOKEN" | npx wrangler secret put API_TOKEN
DEPLOY_OUT="$(npx wrangler deploy 2>&1)"
echo "$DEPLOY_OUT"

URL="$(grep -Eo 'https://[A-Za-z0-9.-]+\.workers\.dev' <<<"$DEPLOY_OUT" | head -1 || true)"
if [[ -z "$URL" ]]; then
  echo "Deployed, but no workers.dev URL was found in the output (workers.dev may be disabled)." >&2
  exit 1
fi

umask 077
INSTANCE_DIR="$CONFIG_DIR/instances/$NAME"
mkdir -p "$INSTANCE_DIR"
printf '{"name":"%s","url":"%s","dir":"%s","deployedAt":"%s"}\n' "$NAME" "$URL" "$TARGET" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$INSTANCE_DIR/config.json"
printf '%s' "$WORKER_TOKEN" > "$INSTANCE_DIR/token"
chmod 600 "$INSTANCE_DIR/token" "$INSTANCE_DIR/config.json"

echo "deployed $NAME"
echo "├── url: $URL"
echo "├── token file: $INSTANCE_DIR/token"
echo "└── source copy: $TARGET"
echo "WORKER_URL=$URL"
