# `mbsync-watcher`

Small daemon used to listen to for IDLE events for `mbsync` command.

When installing, please run:

    pip install --user mbsync-watcher

This will install the `mbsync_watcher` command. Which can be run like:

    mbsync_watcher <channel-or-group>

where <channel-or-group> is the name of a channel or group in your
`~/.mbsyncrc` file.
Installing `mbsync-watcher` will install a user-class systemd service. To
start:

    systemctl --user daemon-reload
    systemctl --user start mbsync-watcher.service

To enable on startup:

    systemctl --user enable mbsync-watcher.service

The `~/.config/mbsync_watcher/config.yaml` file also allows you to specify
post-sync hooks.
