#!/usr/bin/python3
"""Supervisor event listener — dependency-free.

Implements the supervisor eventlistener protocol directly (stdin/stdout
handshake) instead of importing `supervisor.childutils`, which may not be
installed for the system python3. When a managed process enters the FATAL
state, we terminate supervisord (PID 1) so the container can be restarted
by the orchestrator (Docker auto-restart policy).
"""
import sys
import os
import logging
import subprocess
import time


def get_headers(line):
    """Parse a supervisor event header line into a dict.

    Line format: 'ver:3.0 server:supervisor serial:21 ... eventname:X len:NN'
    """
    headers = {}
    line = line.strip()
    for token in line.split():
        if ":" in token:
            k, v = token.split(":", 1)
            headers[k] = v
    return headers


def listener_wait(stdin, stdout):
    """Signal READY, then read the next event from supervisord."""
    stdout.write("READY\n")
    stdout.flush()
    line = stdin.readline()
    if not line:
        return None, ""
    headers = get_headers(line)
    length = int(headers.get("len", 0))
    body = stdin.read(length) if length > 0 else ""
    return headers, body


def listener_ok(stdout):
    stdout.write("RESULT 2\nOK")
    stdout.flush()


def listener_fail(stdout):
    stdout.write("RESULT 2\nFAIL")
    stdout.flush()


def main(args):
    logging.basicConfig(
        stream=sys.stderr, level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(filename)s: %(message)s",
    )
    logger = logging.getLogger("supervisord-watchdog")
    debug_mode = "DEBUG" in os.environ

    while True:
        try:
            headers, body = listener_wait(sys.stdin, sys.stdout)
            if headers is None:
                # stdin closed (supervisord shutting down) — exit cleanly
                return

            logger.debug("Headers: %r", headers)
            logger.debug("Body: %r", body)
            logger.debug("Args: %r", args)

            if debug_mode:
                continue

            if headers.get("eventname") == "PROCESS_STATE_FATAL":
                # Parse body: 'processname:X groupname:X from_state:X pid:NN'
                try:
                    fields = dict(
                        pair.split(":", 1) for pair in body.split(" ") if ":" in pair
                    )
                except Exception:
                    fields = {}

                processname = fields.get("processname", "")
                logger.info("Process entered FATAL state: %s", processname)

                if not args or processname in args:
                    logger.error(
                        "Killing off supervisord instance to trigger container restart..."
                    )
                    try:
                        subprocess.call(
                            ["/bin/kill", "-15", "1"], stdout=sys.stderr
                        )
                        logger.info("Sent TERM signal to init process")
                        time.sleep(5)
                        logger.critical(
                            "Still alive — sending KILL to all processes"
                        )
                        subprocess.call(
                            ["/bin/kill", "-9", "-1"], stdout=sys.stderr
                        )
                    except Exception as e:
                        logger.critical("Kill failed: %s", str(e))
            listener_ok(sys.stdout)
        except Exception as e:
            logger.critical("Unexpected exception: %s", str(e))
            try:
                listener_fail(sys.stdout)
            except Exception:
                pass
            # Do not exit — keep the listener alive for subsequent events


if __name__ == "__main__":
    main(sys.argv[1:])
