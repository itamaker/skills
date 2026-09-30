#!/usr/bin/env bash
# Report whether the tools needed to deploy the Worker are present.
# Prints key=value lines; exit 0 if everything is ready, 1 if something is missing.
# When something is missing, INSTALL_CMD is a suggested command (never run here); it is empty when
# there is none. A Node.js problem is fixed by install-node.sh, which needs no sudo. cf itself is not
# checked: npx fetches it for the login step and npm install puts a pinned copy in the Worker's folder.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/node-path.sh"

status=0
need_node=0
need_curl=0

if command -v node >/dev/null 2>&1; then
  # cf loads cloudflare.config.ts with Node's built-in TypeScript support: it needs Node 22.18+
  # built with that support, which distro packages such as Debian/Ubuntu's nodejs leave out.
  read -r major minor ts < <(node -p 'const [a, b] = process.versions.node.split("."); `${a} ${b} ${process.features.typescript ? "yes" : "no"}`')
  if (( major < 22 || (major == 22 && minor < 18) )); then
    echo "node=too_old ($(node --version), need 22.18+)"; status=1; need_node=1
  elif [[ "$ts" != "yes" ]]; then
    echo "node=no_typescript ($(node --version) is built without TypeScript support, which cf needs)"; status=1; need_node=1
  elif [[ "$(command -v node)" == "$NODE_HOME/"* ]]; then
    echo "node=ok ($(node --version), installed for this skill)"
  else
    echo "node=ok ($(node --version))"
  fi
else
  echo "node=missing"; status=1; need_node=1
fi

if command -v npm >/dev/null 2>&1; then echo "npm=ok ($(npm --version))"; else echo "npm=missing"; status=1; need_node=1; fi
if command -v curl >/dev/null 2>&1; then echo "curl=ok"; else echo "curl=missing"; status=1; need_curl=1; fi

if (( status != 0 )); then
  cmd=""
  if (( need_curl )); then
    # install-node.sh downloads with curl, so curl comes first; rerun the check afterwards.
    if command -v brew >/dev/null 2>&1; then cmd="brew install curl"
    elif command -v apt-get >/dev/null 2>&1; then cmd="sudo apt-get install -y curl"
    elif command -v dnf >/dev/null 2>&1; then cmd="sudo dnf install -y curl"
    elif command -v pacman >/dev/null 2>&1; then cmd="sudo pacman -S --needed curl"
    fi
  elif (( need_node )) && node_platform >/dev/null; then
    cmd="$SCRIPT_DIR/install-node.sh"
  fi
  echo "INSTALL_CMD=$cmd"
fi

exit $status
