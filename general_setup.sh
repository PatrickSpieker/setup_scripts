#!/bin/zsh

# need to mark this script as executable with: chmod 755 ./setup.sh
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install neovim
brew install tmux
brew install fzf
brew install ack # like grep but better????
brew install ruby
sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs \
       https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'

cp ./vim_config ~/.vimrc
# nvim setup
if [ -d "/Users/patrickspieker/.config/nvim" ] 
then
else
  mkdir ~/.config/nvim
fi
cp ./vim_config ~/.config/nvim/init.vim
cp ./tmux_config ~/.tmux.conf
cp ./zsh_config ~/.zshrc
source ~/.zshrc

