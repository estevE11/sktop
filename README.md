# Slurm-Top (sktop)

A TUI for managing Slurm jobs, built with Textual.

## Installation & Setup

Follow these steps to install and configure `sktop` to run as `sltop` from anywhere.

### 1. Create a Virtual Environment

It's recommended to run this tool in its own virtual environment to manage dependencies.

```bash
# Navigate to the project directory
cd /path/to/slurm-top/sktop

# Create a virtual environment named '.venv'
python3 -m venv .venv

# Activate the environment
source .venv/bin/activate
```

### 2. Install Dependencies

Install the required packages (primarily `textual`).

```bash
pip install -r requirements.txt
```

### 3. Make the Script Executable

Ensure the main script has execution permissions.

```bash
chmod +x sktop.py
```

### 4. Add to PATH (Run as `sltop`)

To run the tool as `sltop` from any directory, you have two main options:

#### Option A: Create a Wrapper Script in `~/.local/bin` (Recommended)

This method ensures the script always runs with the correct virtual environment python interpreter.

1.  Create a `bin` directory if it doesn't exist:
    ```bash
    mkdir -p ~/.local/bin
    ```

2.  Create a wrapper script named `sltop`:
    ```bash
    # Replace /path/to/slurm-top/sktop with the actual absolute path to your directory
    PROJECT_DIR="/home/usuaris/veu/roger.esteve.sanchez/slurm-top/sktop"
    
    cat <<EOF > ~/.local/bin/sltop
    #!/bin/bash
    source "$PROJECT_DIR/.venv/bin/activate"
    python "$PROJECT_DIR/sktop.py" "\$@"
    EOF
    ```

3.  Make the wrapper executable:
    ```bash
    chmod +x ~/.local/bin/sltop
    ```

4.  Ensure `~/.local/bin` is in your PATH. Add this to your shell config (`~/.bashrc` or `~/.zshrc`) if not already present:
    ```bash
    export PATH="$HOME/.local/bin:$PATH"
    ```
    Then run `source ~/.bashrc`.

#### Option B: Symlink (If not using a venv or if venv is activated globally)

If you installed dependencies globally or want to manage the environment differently:

```bash
ln -s /home/usuaris/veu/roger.esteve.sanchez/slurm-top/sktop/sktop.py ~/.local/bin/sltop
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
