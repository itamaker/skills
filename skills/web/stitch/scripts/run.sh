#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
node_bin="${NODE:-node}"

exec "$node_bin" "$script_dir/stitch.mjs" "$@"
