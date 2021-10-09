#!/bin/zsh

# need to mark this script as executable with: chmod 755 ./setup.sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install neovim
brew install tmux



git config --global user.email "patrick@patrickspieker.com"
git config --global user.name "patrick"

cp ./vim_config ~/.vimrc
mkdir ~/.config/nvim
cp ./vim_config ~/.config/nvim/init.vim
cp ./zsh_config ~/.zshrc
cp ./tmux_conf ~/.tmux.conf
source ~/.zshrc
