#!/bin/bash
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'Only macOS is supported.' >&2; exit 1; }
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="$(brew --prefix python@3.12)/bin/python3.12"
[[ -x "$python_bin" ]] || { echo 'Install Homebrew python@3.12 first.' >&2; exit 1; }
[[ -x /Applications/calibre.app/Contents/MacOS/ebook-convert ]] || { echo 'Install Calibre in /Applications first.' >&2; exit 1; }
venv_dir="$HOME/.local/share/pdf-to-epub/venv"
"$python_bin" -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --require-hashes -r "$repo_dir/scripts/pdf_to_epub/requirements.lock"
mkdir -p "$HOME/.local/bin"
ln -sfn "$repo_dir/scripts/pdf-to-epub" "$HOME/.local/bin/pdf-to-epub"
echo 'Installed pdf-to-epub in ~/.local/bin.'
