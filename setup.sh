#!/bin/bash

# This file exists both for literal development environment config purposes (to
# programmatically redo my setup) and also for human config purposes — to remind
# me how my setup works and document tips and tricks.
#
# NOTE: when you clone this repo, mark this script as executable first:
#   chmod 755 ./setup.sh
#
# First, you may need to create / add the new laptop SSH key with:
#   ssh-keygen -b 4096 -t rsa

# Resolve absolute path to this repo, regardless of where you run setup.sh from.
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"



# ===== XCODE COMMAND LINE TOOLS =====
# Needed for a bunch of random Homebrew things.
xcode-select --install



# ===== HOMEBREW =====
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"



# ===== BASH =====
# Upgrade from the ancient macOS-bundled bash to the latest Homebrew version.
brew install bash
brew info bash  # shows you the path of the installed bash executable

# For M1+: /opt/homebrew/bin/bash (symlink)
# For Intel: /usr/local/bin/bash
# Check the actual path with: readlink $(brew --prefix)/bin/bash
BREW_BASH="$(brew --prefix)/bin/bash"

# Add upgraded bash to the list of allowed shells (idempotent).
echo "Adding new bash to list of allowable shells..."
grep -qxF "$BREW_BASH" /etc/shells || echo "$BREW_BASH" | sudo tee -a /etc/shells > /dev/null

# Change the default shell only if it's not already set.
echo "Setting system shell to the new bash..."
[ "$SHELL" != "$BREW_BASH" ] && chsh -s "$BREW_BASH"

echo "$BASH_VERSION"  # should now be the new version

# Symlink bashrc and bash_profile into place.
# bash_profile_main just sources bashrc — all real config lives in bashrc.
ln -sfn "$REPO_DIR/bashrc_main" ~/.bashrc
ln -sfn "$REPO_DIR/bash_profile_main" ~/.bash_profile

echo "Finished configuring bash!"



# ===== RUST =====
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh



# ===== HOMEBREW PACKAGES =====
# Install everything from the Brewfile (idempotent — skips already-installed packages).
brew bundle --file="$REPO_DIR/Brewfile"



# ===== GIT =====
git config --global user.email "patrick@patrickspieker.com"
git config --global user.name "pspieker"



# ===== NEOVIM =====
# vim-plug is the plugin manager; install it, then open nvim and run :PlugInstall.
mkdir -p ~/.config/nvim

# Symlink the nvim config from this repo.
# Note: the full file path is required here (relative paths don't work for nvim init).
ln -sfn "$REPO_DIR/vimrc_main" ~/.config/nvim/init.vim

# Download vim-plug.
sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs \
       https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'



# ===== VS CODE =====
# VS Code should already be installed at this point.
# Symlink the settings file. (ln dest src — yes, the argument order feels backwards.)
ln -sfn "$REPO_DIR/vscode_settings.json" \
  ~/Library/Application\ Support/Code/User/settings.json

echo "Finished configuring VS Code!"



# ===== CURSOR =====
curl https://cursor.com/install -fsS | bash



# ===== CLAUDE (Claude Code) =====
# Sets up skills — the preferred way to extend Claude Code behavior.
# Note: ln -sfn on a directory requires the full absolute path.
mkdir -p ~/.claude
ln -sfn "$REPO_DIR/skills" ~/.claude/skills



# ===== CODEX =====
# reminder: codex skills are invoked with $skill_name, not /skill_name
mkdir -p ~/.codex
ln -sfn "$REPO_DIR/skills" ~/.codex/skills



# ===== XCODE BRIDGE MCP SERVER =====
if [ -d "$REPO_DIR/mcp-servers/xcode-bridge" ]; then
  pushd "$REPO_DIR/mcp-servers/xcode-bridge" || exit
  npm install && npx tsc
  popd || exit
fi



# ===== SWIFTBAR =====
# SwiftBar reads plugins from ~/.swiftbar/plugins.
mkdir -p ~/.swiftbar
ln -sfn "$REPO_DIR/swiftbar_plugins" ~/.swiftbar/plugins



# ===== KARABINER ELEMENTS =====
# Remap Caps Lock to Escape system-wide.
mkdir -p ~/.config/karabiner/assets/complex_modifications
cat > ~/.config/karabiner/assets/complex_modifications/caps_lock_to_escape.json <<'EOF'
{
  "title": "Patrick customizations",
  "rules": [
    {
      "description": "Caps Lock to Escape",
      "manipulators": [
        {
          "type": "basic",
          "from": {
            "key_code": "caps_lock",
            "modifiers": {
              "optional": [
                "any"
              ]
            }
          },
          "to": [
            {
              "key_code": "escape"
            }
          ]
        }
      ]
    }
  ]
}
EOF

# If karabiner.json already exists, merge the rule in (idempotent via jq upsert).
if [ -f ~/.config/karabiner/karabiner.json ]; then
  tmp_karabiner="$(mktemp)"
  jq --arg description "Caps Lock to Escape" --argjson rule '{
    "description": "Caps Lock to Escape",
    "manipulators": [
      {
        "type": "basic",
        "from": {
          "key_code": "caps_lock",
          "modifiers": {
            "optional": ["any"]
          }
        },
        "to": [
          {
            "key_code": "escape"
          }
        ]
      }
    ]
  }' '
    .profiles |= map(
      .complex_modifications = (.complex_modifications // {}) |
      .complex_modifications.rules = (
        ((.complex_modifications.rules // []) | map(select(.description != $description))) + [$rule]
      )
    )
  ' ~/.config/karabiner/karabiner.json > "$tmp_karabiner" && mv "$tmp_karabiner" ~/.config/karabiner/karabiner.json
fi



# ===== DONE =====
# Source the new config so changes take effect without opening a new shell.
# (This needs to be the last step since it runs everything in bash_profile.)
source ~/.bash_profile
echo "Done!"
