#!/usr/bin/env python

import os

from setuptools import setup

setup(
    name="mbsync-watcher",
    version="0.1.0",
    packages=["mbsync_watcher"],
    description="Watch mailboxes using IDLE and sync with mbsync.",
    author="Albert Kim",
    author_email="alkim@alkim.org",
    install_requires=["pyyaml", "aioimaplib"],
    scripts=["bin/mbsync_watcher"],
    data_files=[
        (os.path.expanduser("~/.config/mbsync_watcher"), ["config.yaml"]),
        (os.path.expanduser("~/.config/systemd/user"), ["mbsync-watcher.service"]),
    ],
)
