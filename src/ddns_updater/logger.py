"""Root logger configuration for the DDNS updater application.

Provides ``setup_root_logger`` which configures the root logger with
stdout, file, and systemd journal handlers. Call once at application
startup; all modules then use ``logging.getLogger(__name__)`` directly.
"""

import sys
import logging
import pathlib
import platform
from logging import handlers

if platform.system() == "Linux":
    try:
        from cysystemd import journal  # noqa
    except ImportError:
        journal = None


def setup_root_logger(level: int | str = logging.INFO) -> logging.Logger:
    """Configure and return the root application logger.

    Sets up the root logger with a stdout stream handler, a daily
    rotating file handler, and on Linux systems a systemd journal
    handler. Log files are rotated at midnight with up to 20 backups
    retained.

    On Linux the log file is written to ``/var/log/ddns_updater/``.
    On other platforms it is written to the current working directory.

    :param level: Minimum logging level (default ``logging.INFO``).
    :type level: int | str
    :returns: The configured root logger instance.
    :rtype: logging.Logger
    """

    logger = logging.getLogger()
    logger.setLevel(level=level)

    # log file path
    if platform.system() == "Linux":
        log_dir = pathlib.Path("/var/log/ddns_updater")
    else:
        log_dir = pathlib.Path.cwd()
    log_file = log_dir / "ddns_updater.log"

    # set formatter
    formatter = logging.Formatter('%(asctime)s | %(name)s - %(levelname)s | %(message)s')

    # add handlers
    if platform.system() == "Linux" and journal is not None:
        journal_handler = journal.JournaldLogHandler()
        journal_handler.setFormatter(formatter)
        logger.addHandler(journal_handler)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = handlers.TimedRotatingFileHandler(
        filename=log_file, backupCount=20,
        when="midnight", interval=1)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
