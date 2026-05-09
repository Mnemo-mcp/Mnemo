#!/bin/sh
set -e

REPO="nikhil1057/Mnemo"
INSTALL_DIR="${MNEMO_INSTALL_DIR:-/usr/local/bin}"

detect_platform() {
  OS="$(uname -s)"
  ARCH="$(uname -m)"

  case "$OS" in
    Darwin)
      case "$ARCH" in
        arm64) PLATFORM="darwin-arm64" ;;
        *)     PLATFORM="darwin-x64" ;;
      esac
      ;;
    Linux)
      PLATFORM="linux-x64"
      ;;
    *)
      echo "Unsupported OS: $OS" >&2
      exit 1
      ;;
  esac
}

get_latest_version() {
  if command -v curl >/dev/null 2>&1; then
    VERSION=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"//;s/".*//')
  elif command -v wget >/dev/null 2>&1; then
    VERSION=$(wget -qO- "https://api.github.com/repos/$REPO/releases/latest" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"//;s/".*//')
  else
    echo "Error: curl or wget required" >&2
    exit 1
  fi
}

download() {
  URL="https://github.com/$REPO/releases/download/$VERSION/mnemo-$PLATFORM"
  echo "Downloading mnemo $VERSION for $PLATFORM..."

  TMP=$(mktemp)
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$URL" -o "$TMP"
  else
    wget -qO "$TMP" "$URL"
  fi

  chmod +x "$TMP"

  if [ -w "$INSTALL_DIR" ]; then
    mv "$TMP" "$INSTALL_DIR/mnemo"
  else
    echo "Installing to $INSTALL_DIR (requires sudo)..."
    sudo mv "$TMP" "$INSTALL_DIR/mnemo"
  fi

  echo "✓ mnemo installed to $INSTALL_DIR/mnemo"
  echo "  Run: mnemo init"
}

detect_platform
get_latest_version
download
