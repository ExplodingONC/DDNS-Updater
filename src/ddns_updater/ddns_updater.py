"""Entry point for the DDNS updater application.

Loads configuration files, creates one ``DDNSTask`` per DNS target,
and runs them concurrently using a ``ThreadPool``. Each task
independently monitors the local IP and synchronizes DNS records
with the configured provider.
"""

from multiprocessing.pool import ThreadPool

from .logger import setup_root_logger
from .config_loader import load_ddns_config
from .ddns_task import DDNSTask


def main() -> None:
    """Initialize logging, load configs, and run all DDNS tasks."""

    setup_root_logger()

    config_list = load_ddns_config()

    pool = ThreadPool(processes=len(config_list))
    task_list = []

    for ddns_config in config_list:

        api_config = ddns_config["api"]
        task_configs = ddns_config["task"]
        task = DDNSTask(
            api_config=api_config,
            task_configs=task_configs,
        )
        task_list.append(task)

    pool.map(DDNSTask.run, task_list)

    pool.close()
    pool.join()


if __name__ == "__main__":
    main()
