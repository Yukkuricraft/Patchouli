#!/usr/bin/env bash
DIR=$(cd `dirname $0` && pwd)

function log {
    echo ">> $@"
}

if [[ ! -e "venv/bin/python3" ]]; then
    log "venv not detected. Creating new virtualenv."
    python3 -m venv venv
else
    log "venv was detected."
fi
echo

if ! grep "$DIR/venv/bin/python3" git-patchy > /dev/null; then
    log "git-patchy detected as not sourcing virtualenv. Adding relpath shebang."
    ESCAPED_DIR=$(sed 's/\//\\\//g' <<< $DIR)
    sed -i "1s/^/#!${ESCAPED_DIR}\/venv\/bin\/python3\n/" git-patchy
else
    log "git-patchy already shebangs the venv."
fi
echo

log "Checking virtualenv pip packages."
venv/bin/pip3 install -r "$DIR/requirements.txt"
echo

if [[ ! -e "/usr/bin/git-patchy" ]]; then
    log "git-patchy not symlinked in /usr/bin/. Creating symlink with sudo."
    sudo ln -s "$DIR/git-patchy" "/usr/bin/git-patchy"
else
    log "git-patchy was already symlinked to /usr/bin."
fi
