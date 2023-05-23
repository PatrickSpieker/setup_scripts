#!/bin/bash

# This file exists both for literal development environment config purposes (to programmically redo my setup)
# and also for human config purposes :) - to remind me how my setup works + tips and tricks
#
# NOTE: 
# When you clone this repo, you need to mark this script as executable with: chmod 755 ./setup.sh

# ----- HOMEBREW Installation -----
# xcode-select --install # Apple's Command Line Tools - needed for a bunch of random Homebrew things 
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# ----- BASH INSTALLATION ----- 
# - changing shell to an upgraded version of bash 

# brew install bash # just need the basics of shell - no customization beyond that (who needs color schemes?)
# brew info bash # need this to get the path of the installed bash executable

# should probably check if the above command worked ^^ ??? check with $? or something
# For M1's for example, should be /opt/homebrew/bin/bash, which itself is a symlink
echo "Adding new bash to list of allowable shells..."
# echo "/path/to/bash" | sudo tee -a /etc/shells >> /dev/null # adding the upgraded bash to our shell options
echo "Making the system shell the new bash..."
chsh -s /usr/local/bin/bash # actually changing the shell now that the new bash is an option
echo $BASH_VERSION

# Soft linking the bashrc, then creating bash_profile such that it just references rc - all config should be in rc
ln -sf /Users/patrickspieker/Library/Mobile\ Documents/com~apple~CloudDocs/setup_scripts/bashrc_main ~/.bashrc
# Appending with >> as opposed to overwriting with >
echo "source ~/.bashrc" >> ~/.bash_profile
echo "Finished configuing new bash!"

# ----- INSTALLATION VIA HOMEBREW -----
# brew install fzf # file fuzzy finder - mostly used in the nvim context
# brew install ruby # Old version of Ruby is usually the default, so want to upgrade
# brew install ffmpeg # for extracting / dealing with audio files, converting, etc. 
# brew install ripgrep # best empirical backend for both fzf (filename searching) and ack (file content searching)
# brew install node
# brew install yt-dlp/taps/yt-dlp # faster version of youtube download
# brew install --cask emacs # thinking of trying this
# brew install watchman # for sorbet

# Configuring personal git things
git config --global user.email "patrick@patrickspieker.com"
git config --global user.name "pspieker"

# -------- VIM + NVIM config --------
#
# NEOVIM Installation
# brew install neovim # for most text editing needs

if [ -d "/Users/patrickspieker/.config/nvim" ] 
then
  echo "NVIM config directory already existed; continuing..."
else
  mkdir ~/.config/nvim
fi

# Softlinking the NVIM config in this folder to the correct file system location
# Note that the _entire_ file path is needed here - 
# (should set up a bash variable to store the path to this location)
ln -sf /Users/patrickspieker/Library/Mobile\ Documents/com~apple~CloudDocs/setup_scripts/vimrc_main ~/.config/nvim/init.vim
sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs \
       https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'
# -------- END VIM CONFIG --------
#
# -------- VSCODE Config ---------
# Soft linking the bashrc, then creating bash_profile such that it just references rc - all config should be in rc
ln -sf /Users/patrickspieker/Library/Mobile\ Documents/com~apple~CloudDocs/setup_scripts/vscode_settings \
  ~/Library/Application\ Support/Code/User/settings.json
# Appending with >> as opposed to overwriting with >
echo "Finished configuing VS Code!"
# -------- END VS CODE CONFIG ------

# this will - run the stuff in bash_profile, which sources bashrc, so this needs to be the last step. 
# This helps you avoid having to start a new shell to actually have these changes take effect. 
source ~/.bash_profile
echo "Done!"
