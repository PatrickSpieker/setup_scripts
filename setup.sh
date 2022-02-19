#!/bin/zsh

# This file exists both for literal config purposes (to programmically redo my setup)
# and also for intellectual purposes - to remind me how my setup works + tips and tricks

# HOMEBREW Installation 
# need to mark this script as executable with: chmod 755 ./setup.sh
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
# xcode-select --install # Apple's Command Line Tools - needed for a bunch of random Homebrew things 

# BASH INSTALLATION - changing shell to an upgraded version of bash 
brew install bash # just need the basics of shell - no customization beyond that (who needs color schemes?)
# should probably check if the above command worked ^^ ??? check with $? or something
echo "Adding new bash to list of allowable shells..."
echo "/usr/local/bin/bash" | sudo tee -a /etc/shells >> /dev/null # adding the upgraded bash to our shell options
echo "Making the system shell the new bash..."
chsh -s /usr/local/bin/bash # actually changing the shell now that the new bash is an option
echo "Finished configuing new bash!"


brew install tmux # for terminal multi-plexing
brew install fzf # file fuzzy finder - mostly used in the nvim context
brew install ruby # Old version of Ruby is usually the default, so want to upgrade
brew install ffmpeg # for extracting / dealing with audio files, converting, etc. 

#
# Configuring personal git things
git config --global user.email "patrick@patrickspieker.com"
git config --global user.name "pspieker"

# -------- VIM + NVIM config --------
#
# NEOVIM Installation
brew install neovim # for most text editing needs
# Softlinking the NVIM config in this folder to the correct file system location
# Note that the _entire_ file path is needed here - 
ln -s /Users/patrickspieker/Library/Mobile\ Documents/com~apple~CloudDocs/setup_scripts/vimrc_main ~/.config/nvim/init.vim
cp ./vim_config ~/.vimrc

if [ -d "/Users/patrickspieker/.config/nvim" ] 
then
else
  mkdir ~/.config/nvim
fi
sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs \
       https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'

# Soft linking up config files - so the "correct" locations will point to the files here, in the repo
ln -s ~/.config/nvim/init.vim ./vimrc_main
ln -s /Users/patrickspieker/Library/Mobile\ Documents/com~apple~CloudDocs/setup_scripts/bashrc_main ~/.bashrc
echo "source ~/.bashrc" > ~/.bash_profile
cp ./zsh_config ~/.zshrc
cp ./tmux_config ~/.tmux.conf
source ~/.zshrc

echo "Done!"
