#!/usr/bin/env python

"""
Parse mbsync's config file.

Limitations: Currently does not parse the Patterns for Channels and assumes we
want to perform IDLE with INBOX.
"""

import json
import os
import subprocess


class MbsyncrcError(Exception):
    pass


class Mbsyncrc(object):
    def __init__(self, config_path):
        self._config_path = config_path
        self.accounts = {}
        self.stores = {}
        self.channels = {}
        self.groups = {}

        self._parse()

    def _parse(self):
        with open(self._config_path) as f:
            self._lines = f.readlines()

        self._idx = 0
        while self._idx < len(self._lines):
            line = self._lines[self._idx].strip()

            if line.startswith("IMAPAccount"):
                self._parse_imap_account()
            elif line.startswith("IMAPStore"):
                self._parse_imap_store()
            elif line.startswith("Channel"):
                self._parse_channel()
            elif line.startswith("Group"):
                self._parse_group()
            else:
                # Other stuff we don't care about.
                self._idx += 1

    def _parse_imap_account(self):
        REQUIRED_FIELDS = ("host", "user", "password", "ssl")
        name = self._lines[self._idx].strip().split()[1]
        data = {"ssl": False}
        self.accounts[name] = data

        self._idx += 1
        while self._idx < len(self._lines):
            line = self._lines[self._idx].strip()

            if not line:
                self._idx += 1
                assert all(data[x] is not None for x in REQUIRED_FIELDS)
                return

            if line.startswith("Host"):
                data["host"] = line.split()[1]
            elif line.startswith("User"):
                data["user"] = line.split()[1]
            elif line.startswith("PassCmd"):
                data["password"] = (
                    subprocess.check_output(
                        line.split(maxsplit=1)[1].strip('"'), shell=True
                    )
                    .decode()
                    .strip()
                )
            elif line.startswith("Pass"):
                data["password"] = line.strip()[1]
            elif line.startswith("SSLType"):
                ssl_type = line.split()[1]
                assert ssl_type in ("STARTTLS", "IMAPS")
                data["ssl"] = ssl_type == "IMAPS"
            elif line.startswith("AuthMech"):
                data["auth"] = line.split()[1]
            else:
                raise MbsyncrcError(
                    "Unable to parse line {}: {}".format(self._idx + 1, line)
                )

            self._idx += 1

    def _parse_imap_store(self):
        REQUIRED_FIELDS = ("account",)
        name = self._lines[self._idx].strip().split()[1]
        data = {}
        self.stores[name] = data

        self._idx += 1
        while self._idx < len(self._lines):
            line = self._lines[self._idx].strip()

            if not line:
                self._idx += 1
                assert all(data[x] is not None for x in REQUIRED_FIELDS)
                return

            if line.startswith("Account"):
                data["account"] = line.split()[1]
            else:
                raise MbsyncrcError(
                    "Unable to parse line {}: {}".format(self._idx + 1, line)
                )

            self._idx += 1

    def _parse_channel(self):
        REQUIRED_FIELDS = ("master", "slave")
        name = self._lines[self._idx].strip().split()[1]
        data = {}
        self.channels[name] = data

        self._idx += 1
        while self._idx < len(self._lines):
            line = self._lines[self._idx].strip()

            if not line:
                self._idx += 1
                assert all(data[x] is not None for x in REQUIRED_FIELDS)
                return

            if line.startswith("Master"):
                data["master"] = line.split()[1].strip(":")
            elif line.startswith("Slave"):
                data["slave"] = line.split()[1].strip(":")
            elif line.startswith("Pattern"):
                # TODO: Add patterns for IDLE
                pass
            else:
                raise MbsyncrcError(
                    "Unable to parse line {}: {}".format(self._idx + 1, line)
                )

            self._idx += 1

    def _parse_group(self):
        REQUIRED_FIELDS = ("channels",)
        name = self._lines[self._idx].strip().split()[1]
        data = {"channels": []}
        self.groups[name] = data

        self._idx += 1
        while self._idx < len(self._lines):
            line = self._lines[self._idx].strip()

            if not line:
                self._idx += 1
                assert all(data[x] is not None for x in REQUIRED_FIELDS)
                return

            if line.startswith("Channel"):
                data["channels"].append(line.split()[1])
            else:
                raise MbsyncrcError(
                    "Unable to parse line {}: {}".format(self._idx + 1, line)
                )

            self._idx += 1
