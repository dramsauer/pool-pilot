#!/bin/sh
set -e

# chown is intentionally omitted — Docker for Mac bind mounts don't support
# ownership changes from inside the container. updateRemoteUserUID in
# devcontainer.json already matches UIDs.

# Ensure the vscode user's state directory exists and is writable.
# This is inside the container (not a bind mount), so chown works fine here.
sudo mkdir -p /home/vscode/.local/state
sudo chown vscode:vscode /home/vscode/.local /home/vscode/.local/state

echo "--- post-create: install opencode CLI ---"

# Detect libc to pick the correct native binary variant.
if ldd --version 2>&1 | head -1 | grep -qi musl; then
  variant="opencode-linux-arm64-musl"
else
  variant="opencode-linux-arm64"
fi

# Install the meta-package (provides the opencode command symlink).
npm install -g opencode-ai@latest 2>/dev/null || true

# Ensure the native binary was wired by postinstall; if not, do it manually.
NPMROOT=$(npm root -g)
BIN_DST="$NPMROOT/opencode-ai/bin/opencode.exe"
if [ ! -x "$BIN_DST" ]; then
  if [ ! -f "$NPMROOT/$variant/bin/opencode" ]; then
    npm install -g "$variant" 2>/dev/null || true
  fi
  mkdir -p "$(dirname "$BIN_DST")"
  cp "$NPMROOT/$variant/bin/opencode" "$BIN_DST"
  chmod 755 "$BIN_DST"
fi

command -v opencode >/dev/null 2>&1 && echo "  opencode: $(opencode --version)" || echo "  warning: opencode not in PATH"
echo "ok"

echo "--- post-create: skill dependencies ---"
[ -d /home/vscode/.config/opencode ] && (cd /home/vscode/.config/opencode && npm install) || true
[ -d /home/vscode/.opencode ]       && (cd /home/vscode/.opencode       && npm install) || true
echo "ok"
