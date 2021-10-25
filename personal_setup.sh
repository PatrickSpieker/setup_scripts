#!/bin/zsh

echo "Running setup general..."
./general_setup.sh
echo "Done running setup general; now running personal specific settings..."
git config --global user.email "patrick@patrickspieker.com"
git config --global user.name "patrick"

cp ./zsh_config ~/.zshrc
source ~/.zshrc
echo "Done!"
