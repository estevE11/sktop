#!/bin/bash
# install.sh - A one-line installer for Slurm-Top (sltop)

set -e

# Change these to match your GitHub repository
GITHUB_USER="your-username" 
GITHUB_REPO="sktop"
BINARY_NAME="sltop"
INSTALL_DIR="$HOME/.local/bin"

# Ensure install directory exists
mkdir -p "$INSTALL_DIR"

echo "Downloading latest version of $BINARY_NAME..."

# Fetch the latest release asset URL from GitHub API
LATEST_URL=$(curl -s "https://api.github.com/repos/$GITHUB_USER/$GITHUB_REPO/releases/latest" | \
    grep "browser_download_url" | \
    grep "$BINARY_NAME" | \
    cut -d '"' -f 4)

if [ -z "$LATEST_URL" ]; then
    echo "Error: Could not find the latest release for $GITHUB_REPO."
    echo "Make sure you have created a release and uploaded the binary named '$BINARY_NAME'."
    exit 1
fi

echo "Downloading from: $LATEST_URL"
curl -L -o "$INSTALL_DIR/$BINARY_NAME" "$LATEST_URL"

chmod +x "$INSTALL_DIR/$BINARY_NAME"

echo "Successfully installed $BINARY_NAME to $INSTALL_DIR"

# Check if INSTALL_DIR is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "Warning: $INSTALL_DIR is not in your PATH."
    echo "Add the following line to your shell configuration (e.g. ~/.bashrc or ~/.zshrc):"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo "Run '$BINARY_NAME' to start!"
