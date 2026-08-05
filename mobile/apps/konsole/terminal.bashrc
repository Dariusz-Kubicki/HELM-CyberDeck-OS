# HELM Mobile Terminal preview.
# Load the user's normal interactive shell configuration first.
if [[ -r "$HOME/.bashrc" ]]; then
    source "$HOME/.bashrc"
fi

if [[ $- == *i* ]]; then
    PS1='\[\e[38;5;51m\]╭─[\[\e[38;5;117m\]HELM MOBILE\[\e[38;5;51m\]] \[\e[38;5;45m\]\u@\h \[\e[38;5;117m\]\w\[\e[0m\]\n\[\e[38;5;51m\]╰─› \[\e[0m\]'
fi
