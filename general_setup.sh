#!/bin/zsh

# need to mark this script as executable with: chmod 755 ./setup.sh
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install neovim
brew install tmux
brew install fzf

cp ./vim_config ~/.vimrc
# nvim setup
if [ -d "/Users/patrickspieker/.config/nvim" ] 
then
else
  mkdir ~/.config/nvim
fi
cp ./vim_config ~/.config/nvim/init.vim

cp ./zsh_config ~/.zshrc
cp ./tmux_config ~/.tmux.conf
source ~/.zshrc
