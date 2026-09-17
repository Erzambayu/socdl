#!/usr/bin/env bash
#
# socdl installer for Linux & macOS.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Erzambayu/socdl/main/install.sh | bash
#
# Options (env vars):
#   SOCDL_METHOD=binary|pip|auto   (default: auto)
#   SOCDL_VERSION=v0.1.0           (default: latest)
#   SOCDL_INSTALL_DIR=~/.local/bin (default)
#   SOCDL_NO_PATH=1                (skip PATH modification)
#
set -euo pipefail

REPO="Erzambayu/socdl"
BIN="socdl"
INSTALL_DIR="${SOCDL_INSTALL_DIR:-$HOME/.local/bin}"
METHOD="${SOCDL_METHOD:-auto}"
VERSION="${SOCDL_VERSION:-}"

# --- colors ---
if [ -t 1 ]; then
  C_MAG=$'\033[35m'; C_CYAN=$'\033[36m'; C_GRN=$'\033[32m'
  C_YLW=$'\033[33m'; C_RED=$'\033[31m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
else
  C_MAG=; C_CYAN=; C_GRN=; C_YLW=; C_RED=; C_DIM=; C_RST=
fi

info()  { printf "  %s\n" "$*"; }
ok()    { printf "  %s%s%s\n" "$C_GRN" "$*" "$C_RST"; }
warn()  { printf "  %s%s%s\n" "$C_YLW" "$*" "$C_RST"; }
err()   { printf "  %s%s%s\n" "$C_RED" "$*" "$C_RST" >&2; }

printf "\n%s  socdl installer%s\n" "$C_MAG" "$C_RST"
printf "%s  ---------------%s\n\n" "$C_MAG" "$C_RST"

# ---------------------------------------------------------------------------
# Detect OS/arch
# ---------------------------------------------------------------------------
uname_s="$(uname -s)"
uname_m="$(uname -m)"

case "$uname_s" in
  Linux)  os="linux" ;;
  Darwin) os="macos" ;;
  *)      err "Unsupported OS: $uname_s"; exit 1 ;;
esac

case "$uname_m" in
  x86_64|amd64) arch="x64" ;;
  aarch64|arm64) arch="arm64" ;;
  *) err "Unsupported arch: $uname_m"; exit 1 ;;
esac

info "Platform: ${os}-${arch}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }

latest_tag() {
  if have curl; then
    curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
      | grep -o '"tag_name": *"[^"]*"' | head -1 | sed 's/.*"\(v[^"]*\)"/\1/'
  elif have wget; then
    wget -qO- "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
      | grep -o '"tag_name": *"[^"]*"' | head -1 | sed 's/.*"\(v[^"]*\)"/\1/'
  fi
}

download() {
  url="$1"; dest="$2"
  if have curl; then
    curl -fsSL "$url" -o "$dest"
  elif have wget; then
    wget -qO "$dest" "$url"
  else
    err "Need curl or wget to download."; return 1
  fi
}

install_from_binary() {
  if [ "$os" != "linux" ]; then
    warn "No standalone binary for $os yet — using pip instead."
    return 1
  fi

  tag="$VERSION"
  [ -z "$tag" ] && tag="$(latest_tag)"
  if [ -z "$tag" ]; then
    warn "Could not determine latest release tag."
    return 1
  fi

  asset="socdl-linux-${arch}"
  url="https://github.com/$REPO/releases/download/$tag/$asset"
  info "Downloading $tag ($asset)..."

  mkdir -p "$INSTALL_DIR"
  dest="$INSTALL_DIR/$BIN"

  if ! download "$url" "$dest.tmp"; then
    warn "Download failed (asset may not exist for $arch)."
    rm -f "$dest.tmp"
    return 1
  fi

  chmod +x "$dest.tmp"
  mv -f "$dest.tmp" "$dest"
  ok "Installed binary to $dest"
  return 0
}

install_from_pip() {
  if have pipx; then
    info "Installing via pipx..."
    pipx install --force socdl && { ok "Installed via pipx."; return 0; }
  fi

  py=""
  for c in python3 python; do
    if have "$c"; then py="$c"; break; fi
  done
  if [ -z "$py" ]; then
    err "Python not found. Install Python 3.9+ first:"
    if [ "$os" = "macos" ]; then
      err "  brew install python"
    else
      err "  sudo apt install python3 python3-pip  # or your distro's equivalent"
    fi
    return 1
  fi

  info "Installing via pip ($py)..."
  if "$py" -m pip install --user --upgrade socdl 2>/dev/null; then
    ok "Installed via pip."
    return 0
  fi

  # PEP 668 (externally-managed) environments
  warn "pip install failed (maybe PEP 668). Retrying with --break-system-packages..."
  if "$py" -m pip install --user --break-system-packages --upgrade socdl; then
    ok "Installed via pip (break-system-packages)."
    return 0
  fi

  err "pip install failed."
  return 1
}

ensure_path() {
  [ "${SOCDL_NO_PATH:-}" = "1" ] && return 0
  case ":$PATH:" in
    *":$INSTALL_DIR:"*) return 0 ;;
  esac

  shell_rc=""
  case "${SHELL:-}" in
    */zsh)  shell_rc="$HOME/.zshrc" ;;
    */bash) shell_rc="$HOME/.bashrc" ;;
  esac
  [ -f "$HOME/.profile" ] && [ -z "$shell_rc" ] && shell_rc="$HOME/.profile"

  if [ -n "$shell_rc" ] && ! grep -qs "socdl installer" "$shell_rc"; then
    {
      echo ""
      echo "# added by socdl installer"
      echo "export PATH=\"$INSTALL_DIR:\$PATH\""
    } >> "$shell_rc"
    ok "Added $INSTALL_DIR to PATH in $shell_rc"
    warn "Run: source $shell_rc   (or open a new terminal)"
  else
    warn "Add this to your shell profile manually:"
    warn "  export PATH=\"$INSTALL_DIR:\$PATH\""
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
installed=0
case "$METHOD" in
  binary) install_from_binary && installed=1 ;;
  pip)    install_from_pip    && installed=1 ;;
  auto)
    if install_from_binary; then
      installed=1
      ensure_path
    else
      info "Falling back to pip..."
      install_from_pip && installed=1
    fi
    ;;
  *) err "Unknown SOCDL_METHOD=$METHOD"; exit 1 ;;
esac

if [ "$installed" -ne 1 ]; then
  err "Installation failed."
  exit 1
fi

printf "\n"
ok "socdl is ready!"
printf "\n"
printf "  Try it:\n"
printf "    %ssocdl --help%s\n" "$C_CYAN" "$C_RST"
printf "    %ssocdl https://youtu.be/XXXX%s\n" "$C_CYAN" "$C_RST"
printf "    %ssocdl watch      # auto-download anything you copy%s\n" "$C_CYAN" "$C_RST"
printf "\n"
printf "  Note: install ffmpeg for best YouTube quality:\n"
if [ "$os" = "macos" ]; then
  printf "    %sbrew install ffmpeg%s\n" "$C_CYAN" "$C_RST"
else
  printf "    %ssudo apt install ffmpeg%s\n" "$C_CYAN" "$C_RST"
fi
printf "\n"
