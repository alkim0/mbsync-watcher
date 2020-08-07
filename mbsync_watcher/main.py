#!/usr/bin/env python

import argparse
import asyncio
import logging
import os
import signal
import ssl
import sys
import shlex
import time

from aioimaplib import aioimaplib

from .parse_mbsyncrc import Mbsyncrc
from .config import Config


MBSYNCRC_PATH = os.path.expanduser("~/.mbsyncrc")

LOGGER_NAMESPACE = "mbsync-watcher"

config = Config()

# Monkey patching aioimaplib to support starttls
async def protocol_starttls(self, host, ssl_context=None):
    if "STARTTLS" not in self.capabilities:
        aioimaplib.Abort("server does not have STARTTLS capability")
    if hasattr(self, "_tls_established") and self._tls_established:
        aioimaplib.Abort("TLS session already established")

    response = await self.execute(
        aioimaplib.Command("STARTTLS", self.new_tag(), loop=self.loop)
    )
    if response.result != "OK":
        return response

    if ssl_context is None:
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    sock = self.transport.get_extra_info("socket")
    sock.setblocking(True)
    sock = ssl_context.wrap_socket(sock, server_hostname=host)
    # XXX: This is kind of a hack. It works since the transport interface
    # totally encapsulates this, but in the future it might break if people
    # change the internals of the base transport.
    sock.setblocking(False)
    self.transport._sock = sock
    self._tls_established = True

    await self.capability()

    return response


async def imap_starttls(self):
    return await asyncio.wait_for(self.protocol.starttls(self.host), self.timeout)


aioimaplib.IMAP4ClientProtocol.starttls = protocol_starttls
aioimaplib.IMAP4.starttls = imap_starttls


async def watch(mbsyncrc, channel, queue):
    store = mbsyncrc.stores[mbsyncrc.channels[channel]["master"]]
    account = mbsyncrc.accounts[store["account"]]

    while True:
        if account["ssl"]:
            imap_client = aioimaplib.IMAP4_SSL(host=account["host"])
        else:
            imap_client = aioimaplib.IMAP4(host=account["host"])

        await imap_client.wait_hello_from_server()
        assert "IDLE" in imap_client.protocol.capabilities

        if not account["ssl"]:
            await imap_client.starttls()
            # protocol = imap_client.protocol
            # await protocol.execute(
            #    aioimaplib.Command('STARTTLS', protocol.new_tag()))

        await imap_client.login(account["user"], account["password"])
        await imap_client.select()

        asyncio.ensure_future(imap_client.idle())
        while True:
            msgs = await imap_client.wait_server_push()
            if any("EXISTS" in msg for msg in msgs):
                queue.put_nowait(time.time())


async def sync(channel, queue):
    logger = logging.getLogger(LOGGER_NAMESPACE)
    while True:
        while True:
            timestamp = await queue.get()

            if queue.empty():
                break

        proc = await asyncio.create_subprocess_exec(
            "mbsync",
            channel,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            print("ERROR: {}".format(channel))
            print("== stdout ==")
            print(stdout)
            print("== stderr ==")
            print(stderr)
        else:
            logger.info("synced {}".format(channel))

        for hook in config.post_sync_hooks():
            proc = await asyncio.create_subprocess_exec(
                *shlex.split(hook),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                print("ERROR: [hook {}] {}".format(hook, channel))
                print("== stdout ==")
                print(stdout)
                print("== stderr ==")
                print(stderr)
            else:
                # print("Ran {}".format(hook))
                pass
                # proc = await asyncio.create_subprocess_exec(
                #    'pgrep', 'alot',
                #    stdout=asyncio.subprocess.PIPE,
                #    stderr=asyncio.subprocess.PIPE)
                # stdout, stderr = await proc.communicate()
                # for line in stdout.encode().split('\n'):
                #    pid = int(line.strip())
                #    os.kill(pid, signal.SIGUSR1)


async def timer(queues):
    while True:
        for queue in queues:
            queue.put_nowait(time.time())

        await asyncio.sleep(config.check_interval())


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

    loop = asyncio.get_event_loop()
    queues = []
    for channel in channels:
        queue = asyncio.Queue()
        loop.create_task(watch(mbsyncrc, channel, queue))
        loop.create_task(sync(channel, queue))
        queues.append(queue)
    loop.create_task(timer(queues))
    loop.run_forever()
    loop.close()


if __name__ == "__main__":
    main()
