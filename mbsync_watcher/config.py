import os

import yaml

CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

if os.path.isdir(CONFIG_HOME):
    os.makedirs(os.path.join(CONFIG_HOME, "mbsync_watcher"), exist_ok=True)
    CONFIG_PATH = os.path.join(CONFIG_HOME, "mbsync_watcher", "config.yaml")
else:
    CONFIG_PATH = os.path.expanduser("~/.mbsync_watcher.yaml")


class Config(object):
    def __init__(self):
        self.data = {}

        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                self.data = yaml.load(f)

    def post_sync_hooks(self):
        """
        Returns a list of the commands to run after a sync.
        """
        return self.data.get("post_sync_hooks", [])

    def check_interval(self):
        """
        Returns in the amount of time to wait between periodic checks in seconds.
        """
        return self.data.get("check_interval", 5 * 60)
