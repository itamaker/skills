#!/usr/bin/env bash
# Install an official Node.js 22 build for this skill only. cf needs Node 22.18+ built with TypeScript
# support, which some system packages (Debian/Ubuntu's nodejs) lack.
# Usage: install-node.sh
# Env:   NODE_DIST_MIRROR  where to download from (default https://nodejs.org/dist), e.g. a regional mirror
# It installs into ~/.local/share/remote-browser/.node with no sudo and changes nothing else; check-env.sh,
# deploy.sh and instances.sh then use it automatically. Undo with: rm -rf ~/.local/share/remote-browser/.node
# Exit:  0 = installed (or already there), 1 = failed, 4 = no official build for this machine
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/node-path.sh"

DIST="${NODE_DIST_MIRROR:-https://nodejs.org/dist}"
DIST="${DIST%/}/latest-v22.x"

if [[ -x "$NODE_HOME/bin/node" ]] && node_fits_cf "$NODE_HOME/bin/node"; then
  echo "node=installed ($("$NODE_HOME/bin/node" --version)) at $NODE_HOME (already there)"
  exit 0
fi

if ! PLATFORM="$(node_platform)"; then
  echo "There is no official Node.js build for $(uname -s) $(uname -m) here. Install Node.js 22.18+ with TypeScript support yourself (nodejs.org or nvm)." >&2
  exit 4
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to download Node.js." >&2
  exit 4
fi

# Work next to the destination, not in /tmp: that can be a small tmpfs, and the final move is then a rename.
mkdir -p "$(dirname "$NODE_HOME")"
TMP="$(mktemp -d "$(dirname "$NODE_HOME")/.node-install.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

curl -fsSL "$DIST/SHASUMS256.txt" -o "$TMP/SHASUMS256.txt"

# .tar.xz is about half the size of .tar.gz but needs xz to unpack.
EXT=tar.gz
if command -v xz >/dev/null 2>&1; then EXT=tar.xz; fi
FILE="$(grep -Eo "node-v[0-9]+\.[0-9]+\.[0-9]+-$PLATFORM\.$EXT" "$TMP/SHASUMS256.txt" | head -1 || true)"
if [[ -z "$FILE" && "$EXT" == tar.xz ]]; then
  EXT=tar.gz
  FILE="$(grep -Eo "node-v[0-9]+\.[0-9]+\.[0-9]+-$PLATFORM\.$EXT" "$TMP/SHASUMS256.txt" | head -1 || true)"
fi
if [[ -z "$FILE" ]]; then
  echo "No $PLATFORM build is listed in $DIST/SHASUMS256.txt." >&2
  exit 1
fi

echo "Downloading $FILE from $DIST ..."
curl -fsSL "$DIST/$FILE" -o "$TMP/$FILE"

EXPECTED="$(awk -v f="$FILE" '$2 == f { print $1 }' "$TMP/SHASUMS256.txt")"
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$TMP/$FILE" | cut -d' ' -f1)"
else
  ACTUAL="$(shasum -a 256 "$TMP/$FILE" | cut -d' ' -f1)"
fi
if [[ -z "$EXPECTED" || "$ACTUAL" != "$EXPECTED" ]]; then
  echo "Checksum mismatch for $FILE; nothing was installed." >&2
  exit 1
fi

tar -xf "$TMP/$FILE" -C "$TMP"
rm -rf "$NODE_HOME"
mv "$TMP/${FILE%.$EXT}" "$NODE_HOME"

if ! node_fits_cf "$NODE_HOME/bin/node"; then
  rm -rf "$NODE_HOME"
  echo "The downloaded Node.js does not support TypeScript either; nothing was installed." >&2
  exit 1
fi
echo "node=installed ($("$NODE_HOME/bin/node" --version)) at $NODE_HOME"
