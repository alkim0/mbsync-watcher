#!/usr/bin/env python

import os

from setuptools import setup
from setuptools.command.install import install
from pkg_resources import resource_string


class CustomInstallCommand(install):
    def run(self):
        install.run(self)
        config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

        if os.path.isdir(config_home):
            os.makedirs(os.path.join(config_home, "mbsync_watcher"), exist_ok=True)
            config_path = os.path.join(config_home, "mbsync_watcher", "config.yaml")
        else:
            config_path = os.path.expanduser("~/.mbsync_watcher.yaml")

        if not os.path.exists(config_path):
            with open(config_path, "wb") as f:
                f.write(resource_string("mbsync_watcher", "../config.yaml"))

        service_path = os.path.expanduser(
            "~/.config/systemd/user/mbsync-watcher.service"
        )
        if not os.path.exists(service_path):
            with open(service_path, "wb") as f:
                f.write(resource_string("mbsync_watcher", "../mbsync-watcher.service"))


setup(
    name="mbsync-watcher",
    version="0.1.2",
    packages=["mbsync_watcher"],
    description="Watch mailboxes using IDLE and sync with mbsync.",
    author="Albert Kim",
    author_email="alkim@alkim.org",
    install_requires=["pyyaml", "aioimaplib"],
    scripts=["bin/mbsync_watcher"],
    package_data={"": ["config.yaml", "mbsync-watcher.service"]},
    cmdclass={"install": CustomInstallCommand,},
)
