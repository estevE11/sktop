# Slurm-Top (sktop)

A TUI for managing Slurm jobs, built with Textual.

## Quick Install

Install the latest release binary with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/estevE11/sktop/master/scripts/install.sh | bash
```

This will download the latest `sltop` binary to `~/.local/bin/` and make it ready to use. Make sure `~/.local/bin` is in your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add the line above to your `~/.bashrc` or `~/.zshrc` to make it permanent.

## Manual Installation

If you prefer to run from source, follow these steps:

### 1. Create a Virtual Environment

```bash
cd /path/to/slurm-top/sktop
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Make the Script Executable

```bash
chmod +x sktop.py
```

### 4. Add to PATH (Run as `sltop`)

#### Option A: Wrapper Script (Recommended)

```bash
mkdir -p ~/.local/bin

PROJECT_DIR="$(pwd)"

cat <<EOF > ~/.local/bin/sltop
#!/bin/bash
source "$PROJECT_DIR/.venv/bin/activate"
python "$PROJECT_DIR/sktop.py" "\$@"
EOF

chmod +x ~/.local/bin/sltop
```

Ensure `~/.local/bin` is in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

#### Option B: Symlink

```bash
ln -s "$(pwd)/sktop.py" ~/.local/bin/sltop
```

## Usage

Once installed, you can run the tool simply by typing:

```bash
sltop
```

### Options

-   `-r`, `--refresh`: Set refresh interval in seconds (default: 1.0).
-   `-u`, `--user`: Override the user to monitor (default: current user).

### Keybindings

-   **Up/Down/J/K**: Navigate list
-   **Space**: Toggle selection
-   **X**: Kill selected job(s)
-   **U**: View logs
-   **I**: Inspect job details
-   **R**: Refresh manually
-   **Q**: Quit
