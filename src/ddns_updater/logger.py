"""Root logger configuration for the DDNS updater application.

Provides ``setup_root_logger`` which configures the root logger with
stdout and optionally file handlers. Call once at application startup;
all modules then use ``logging.getLogger(__name__)`` directly.

Environment variables:
    DDNS_LOG_DIR: Directory for log files. Defaults to
        ``/var/log/ddns_updater``. Set to ``/dev/null`` to disable
        file logging.
    DDNS_LOG_LEVEL: Minimum log level. Defaults to ``INFO``.
"""

import os
import sys
import logging
import pathlib
from logging import handlers


def setup_root_logger() -> logging.Logger:
    """Configure and return the root application logger.

    Sets up the root logger with a stdout stream handler. File logging
    is controlled by the ``DDNS_LOG_DIR`` environment variable.

    :returns: The configured root logger instance.
    :rtype: logging.Logger
    """

    level = os.environ.get("DDNS_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, level, logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(level=log_level)

    formatter = logging.Formatter('%(asctime)s | %(name)s - %(levelname)s | %(message)s')

    # stdout handler (always)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # file handler (configurable via DDNS_LOG_DIR)
    log_dir = os.environ.get("DDNS_LOG_DIR", "/var/log/ddns_updater")
    if log_dir and log_dir != "/dev/null":
        log_path = pathlib.Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        log_file = log_path / "ddns_updater.log"
        file_handler = handlers.TimedRotatingFileHandler(
            filename=log_file, backupCount=20,
            when="midnight", interval=1)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
