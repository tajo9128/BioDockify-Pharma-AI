#!/usr/bin/python
import sys
import os
import logging
import subprocess
import time

# Gracefully handle missing supervisor package
try:
    from supervisor.childutils import listener  # type: ignore
    HAS_SUPERVISOR = True
except ImportError:
    HAS_SUPERVISOR = False


def main(args):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format='%(asctime)s %(levelname)s %(filename)s: %(message)s')
    logger = logging.getLogger("supervisord-watchdog")
    debug_mode = True if 'DEBUG' in os.environ else False

    if not HAS_SUPERVISOR:
        logger.warning("supervisor package not installed — listener disabled (non-critical)")
        # Keep process alive so supervisord doesn't retry endlessly
        while True:
            time.sleep(3600)

    while True:
        logger.info("Listening for events...")
        headers, body = listener.wait(sys.stdin, sys.stdout)
        body = dict([pair.split(":") for pair in body.split(" ")])

        logger.debug("Headers: %r", repr(headers))
        logger.debug("Body: %r", repr(body))
        logger.debug("Args: %r", repr(args))

        if debug_mode:
            continue

        try:
            if headers["eventname"] == "PROCESS_STATE_FATAL":
                logger.info("Process entered FATAL state...")
                if not args or body["processname"] in args:
                    logger.error("Killing off supervisord instance ...")
                    _ = subprocess.call(["/bin/kill", "-15", "1"], stdout=sys.stderr)
                    logger.info("Sent TERM signal to init process")
                    time.sleep(5)
                    logger.critical("Why am I still alive? Send KILL to all processes...")
                    _ = subprocess.call(["/bin/kill", "-9", "-1"], stdout=sys.stderr)
        except Exception as e:
            logger.critical("Unexpected Exception: %s", str(e))
            listener.fail(sys.stdout)
            exit(1)
        else:
            listener.ok(sys.stdout)


if __name__ == '__main__':
    main(sys.argv[1:])
