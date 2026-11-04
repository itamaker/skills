#!/usr/bin/env bash
# Manage locally recorded remote-browser deployments. Output is a tree.
# Usage: instances.sh list
#        instances.sh status <name>
#        instances.sh delete <name>     (irreversible: deletes the Worker from Cloudflare)
# Registry: ~/.config/remote-browser/instances/<name>/{config.json,token}
# Exit:  4 = bad input / unknown instance
set -euo pipefail

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/remote-browser"
REGISTRY="$CONFIG_DIR/instances"
CMD="${1:-}"
NAME="${2:-}"
source "$(dirname "${BASH_SOURCE[0]}")/node-path.sh"

field() { node -p "require('$REGISTRY/$1/config.json').$2"; }

require_instance() {
  if [[ ! "$NAME" =~ ^[a-z0-9][a-z0-9-]{0,62}$ || ! -f "$REGISTRY/$NAME/config.json" ]]; then
    echo "No recorded deployment named '$NAME'. Run: instances.sh list" >&2
    exit 4
  fi
}

# tree_children <indent> <label:value>... prints the entries with ├── / └── connectors.
tree_children() {
  local indent="$1"; shift
  local total=$# i=0 conn
  for line in "$@"; do
    i=$((i + 1))
    (( i == total )) && conn="└── " || conn="├── "
    echo "${indent}${conn}${line}"
  done
}

case "$CMD" in
  list)
    shopt -s nullglob
    names=()
    for d in "$REGISTRY"/*/; do
      [[ -f "$d/config.json" ]] && names+=("$(basename "$d")")
    done
    if (( ${#names[@]} == 0 )); then
      echo "remote-browser deployments (0)"
      echo "└── none recorded"
      exit 0
    fi
    echo "remote-browser deployments (${#names[@]})"
    i=0
    for n in "${names[@]}"; do
      i=$((i + 1))
      url="$(field "$n" url)"
      code="$(curl -s -o /dev/null -m 8 -w '%{http_code}' "$url/" || true)"
      [[ "$code" == "200" ]] && online="online" || online="not answering (HTTP $code)"
      if (( i == ${#names[@]} )); then branch="└── "; indent="    "; else branch="├── "; indent="│   "; fi
      echo "${branch}${n}"
      tree_children "$indent" "url: $url" "page: $online" "deployed: $(field "$n" deployedAt)"
    done
    ;;

  status)
    require_instance
    url="$(field "$NAME" url)"
    code="$(curl -s -o /dev/null -m 8 -w '%{http_code}' "$url/" || true)"
    # Token is read from the file and sent as a header; it is never printed.
    quota="$(curl -s -m 15 "$url/status" -H "Authorization: Bearer $(cat "$REGISTRY/$NAME/token")" \
      | node -e '
        let d = "";
        process.stdin.on("data", c => d += c).on("end", () => {
          try {
            const s = JSON.parse(d);
            if (!s.ok) { console.log("error=" + (s.ok === false ? s.error : "unauthorized, or the Worker predates /status (redeploy it)")); return; }
            console.log("used=" + s.usedBrowserTimeSeconds + "s of " + s.freeDailyLimitSeconds + "s (free plan)");
            console.log("sessions=" + s.activeSessions + " active / " + s.maxConcurrentSessions + " max");
            console.log("recovery=" + (s.estimatedRecovery || "not limited right now"));
          } catch { console.log("error=unexpected response; the Worker may predate /status, redeploy it"); }
        });')"
    echo "$NAME"
    echo "├── url: $url"
    echo "├── page: HTTP $code"
    echo "└── browser quota"
    if grep -q '^error=' <<<"$quota"; then
      tree_children "    " "unavailable: ${quota#error=}"
    else
      tree_children "    " \
        "used today: $(grep '^used=' <<<"$quota" | cut -d= -f2-)" \
        "sessions: $(grep '^sessions=' <<<"$quota" | cut -d= -f2-)" \
        "recovery: $(grep '^recovery=' <<<"$quota" | cut -d= -f2-)"
    fi
    ;;

  delete)
    require_instance
    dir="$(field "$NAME" dir)"
    # --force is required: without it a non-interactive cf prints "Aborted." and exits 0 without deleting.
    # Run from an empty scratch directory: cf reads the nearest cloudflare.config.ts (the deploy copy's needs
    # Node with TypeScript support, and an unrelated one could pick the account) and caches the account it
    # selects in the current directory.
    scratch="$(mktemp -d "${TMPDIR:-/tmp}/remote-browser.XXXXXX")"
    trap 'rm -rf "$scratch"' EXIT
    # An explicit check rather than set -e: bash 3.2 (macOS) does not exit when a subshell fails.
    if ! (cd "$scratch" && npx --yes cf@latest workers delete "$NAME" --force) >&2; then
      echo "Could not delete '$NAME' from Cloudflare; the local record was kept." >&2
      exit 1
    fi
    rm -rf "$REGISTRY/$NAME"
    copy="kept (not under ~/.local/share/remote-browser)"
    if [[ -d "$dir" && "$dir" == "$HOME/.local/share/remote-browser/"* ]]; then
      rm -rf "$dir"; copy="removed"
    fi
    echo "deleted $NAME"
    tree_children "" "Cloudflare Worker: deleted" "local record and token: removed" "deploy copy: $copy"
    ;;

  *)
    echo "Usage: instances.sh list | status <name> | delete <name>" >&2
    exit 4
    ;;
esac
