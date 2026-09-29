#!/usr/bin/env bash
# Report whether the tools needed to deploy the Worker are present.
# Prints key=value lines; exit 0 if everything is ready, 1 if something is missing.
# When Node is missing or too old, INSTALL_CMD is a suggested command (never run here).

status=0

if command -v node >/dev/null 2>&1; then
  major="$(node -p 'process.versions.node.split(".")[0]')"
  if (( major >= 18 )); then echo "node=ok ($(node --version))"; else echo "node=too_old ($(node --version), need 18+)"; status=1; fi
else
  echo "node=missing"; status=1
fi

if command -v npm >/dev/null 2>&1; then echo "npm=ok ($(npm --version))"; else echo "npm=missing"; status=1; fi
if command -v curl >/dev/null 2>&1; then echo "curl=ok"; else echo "curl=missing"; status=1; fi

if (( status != 0 )); then
  if command -v brew >/dev/null 2>&1; then cmd="brew install node curl"
  elif command -v apt-get >/dev/null 2>&1; then cmd="sudo apt-get update && sudo apt-get install -y nodejs npm curl"
  elif command -v dnf >/dev/null 2>&1; then cmd="sudo dnf install -y nodejs npm curl"
  elif command -v pacman >/dev/null 2>&1; then cmd="sudo pacman -S --needed nodejs npm curl"
  else cmd=""
  fi
  echo "INSTALL_CMD=$cmd"
fi

exit $status
