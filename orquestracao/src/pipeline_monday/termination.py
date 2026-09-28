"""SIGTERM from the coordinator must unwind workers so durable locks are released."""

import signal


def _terminate(signum, frame):
    # SystemExit bypasses `except Exception` handlers but still runs finally/with blocks.
    raise SystemExit(128 + signum)


def install_termination_handler():
    signal.signal(signal.SIGTERM, _terminate)
