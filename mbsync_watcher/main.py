#!/usr/bin/env python

import argparse
import asyncio
import logging
import os
from queue import Queue
import signal
import ssl
import subprocess
import sys
import shlex
from threading import Thread
import time

from imapclient import IMAPClient

from .parse_mbsyncrc import Mbsyncrc
from .config import Config


MBSYNCRC_PATH = os.path.expanduser("~/.mbsyncrc")

LOGGER_NAMESPACE = "mbsync-watcher"

config = Config()


def watch(mbsyncrc, channel, queue):
    store = mbsyncrc.stores[mbsyncrc.channels[channel]["master"]]
    account = mbsyncrc.accounts[store["account"]]

    ssl_context = ssl.create_default_context()
    if account["ssl"]:
        imap_client = IMAPClient(host=account["host"], ssl=True)
    else:
        imap_client = IMAPClient(host=account["host"], ssl=False)
        imap_client.starttls(ssl_context)

    assert imap_client.has_capability("IDLE")
    imap_client.login(account["user"], account["password"])
    imap_client.select_folder("INBOX")
    imap_client.idle()

    last_connected = time.monotonic()

    while True:
        now = time.monotonic()
        if now - last_connected >= 13 * 60:
            imap_client.idle_done()
            imap_client.idle()
            last_connected = now

        responses = imap_client.idle_check(timeout=13 * 60)
        print("idle msgs for {}: {}".format(channel, responses), flush=True)
        if any("EXISTS" in r[1].decode() for r in responses):
            print("idle alarm queued for {}".format(channel), flush=True)
            queue.put_nowait(("idle", time.time()))


def sync(channel, queue):
    logger = logging.getLogger(LOGGER_NAMESPACE)
    while True:
        while True:
            signal_type, timestamp = queue.get()
            print("got {} alarm for {}".format(signal_type, channel), flush=True)

            if queue.empty():
                break

        print("starting mbsync for {}".format(channel), flush=True)
        proc = subprocess.run(["mbsync", channel], capture_output=True)

        if proc.returncode != 0:
            print("ERROR: {}".format(channel))
            print("== stdout ==")
            print(proc.stdout)
            print("== stderr ==")
            print(proc.stderr)
        else:
            logger.info("synced {}".format(channel))

        for hook in config.post_sync_hooks():
            proc = subprocess.run(shlex.split(hook), capture_output=True)
            if proc.returncode != 0:
                print("ERROR: [hook {}] {}".format(hook, channel))
                print("== stdout ==")
                print(proc.stdout)
                print("== stderr ==")
                print(proc.stderr)
            else:
                # print("Ran {}".format(hook))
                pass


def timer(queues):
    while True:
        for queue in queues:
            queue.put_nowait(("timer", time.time()))

        time.sleep(config.check_interval())


def main():
    logger = logging.getLogger(LOGGER_NAMESPACE)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[{}] %(asctime)s %(message)s".format(LOGGER_NAMESPACE))
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    parser = argparse.ArgumentParser(
        description="Watch mailboxes using IDLE and sync with mbsync."
    )
    parser.add_argument(
        "names", metavar="name", nargs="+", help="names of channels or groups to sync"
    )

    args = parser.parse_args()
    mbsyncrc = Mbsyncrc(MBSYNCRC_PATH)

    channels = []
    for name in args.names:
        if name in mbsyncrc.groups:
            channels.extend(mbsyncrc.groups[name]["channels"])
        elif name in mbsyncrc.channels:
            channels.append(name)
        else:
            raise Exception("Could not find mention of {} in mbsyncrc".format(name))

    queues = []
    for channel in channels:
        queue = Queue()
        Thread(target=watch, args=(mbsyncrc, channel, queue)).start()
        Thread(target=sync, args=(channel, queue)).start()
        queues.append(queue)
    timer_thread = Thread(target=timer, args=(queues,))
    timer_thread.start()
    timer_thread.join()


if __name__ == "__main__":
    main()
