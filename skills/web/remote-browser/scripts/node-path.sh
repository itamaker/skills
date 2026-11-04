# Sourced by the other scripts, never run. cf loads cloudflare.config.ts with Node's built-in TypeScript
# support, which some system Node packages (Debian/Ubuntu's nodejs) are built without. install-node.sh
# puts an official build in NODE_HOME; when it is there, it goes first on PATH so the skill uses it.
# The folder starts with a dot so it can't collide with a deployment copy, whose name never does.

NODE_HOME="$HOME/.local/share/remote-browser/.node"

if [[ -x "$NODE_HOME/bin/node" ]]; then
  export PATH="$NODE_HOME/bin:$PATH"
fi

# node_fits_cf [node]: succeeds when that Node (default: the one on PATH) is 22.18+ with TypeScript support.
node_fits_cf() {
  "${1:-node}" -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit((a > 22 || (a === 22 && b >= 18)) && process.features.typescript ? 0 : 1)' 2>/dev/null
}

# node_platform: prints this machine's name in the Node.js download tree (linux-x64, darwin-arm64, ...),
# or fails when there is no official build for it.
node_platform() {
  local os arch
  case "$(uname -s)" in Linux) os=linux ;; Darwin) os=darwin ;; *) return 1 ;; esac
  case "$(uname -m)" in x86_64 | amd64) arch=x64 ;; aarch64 | arm64) arch=arm64 ;; *) return 1 ;; esac
  # The official Linux builds need glibc.
  if [[ "$os" == linux ]] && ldd --version 2>&1 | grep -qi musl; then return 1; fi
  echo "$os-$arch"
}
