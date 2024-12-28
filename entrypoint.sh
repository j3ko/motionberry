#!/bin/bash

USER_ID=${PUID:-0}
GROUP_ID=${PGID:-0}

if ! getent group video >/dev/null; then
    groupadd -r video
fi

if ! getent group appgroup >/dev/null; then
    groupadd -g "$GROUP_ID" appgroup
fi

if ! id -u appuser >/dev/null 2>&1; then
    useradd -m -u "$USER_ID" -g appgroup -G video appuser
fi

chown -R appuser:appgroup /motionberry

exec gosu appuser "$@"
