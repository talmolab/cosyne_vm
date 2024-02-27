"""This module checks if a process is running on the local machine."""

import argparse
import socket
import time

try:
    import psutil
except ImportError as e:
    print(
        "psutil is not installed in the development environment. "
        "Please install it using `pip install psutil`"
    )
    raise e

from database import SpannerDatabase
from logging_utils import CloudAndConsoleLogger


cnc_logger = CloudAndConsoleLogger(
    module_name=__name__, format="%(module)s[%(levelname)s]%(asctime)s: %(message)s"
)


def create_parser():
    """Create an argument parser for the script."""
    parser = argparse.ArgumentParser(
        description="Check if a process is running on the local machine."
    )
    parser.add_argument(
        "--process",
        default="sleap",
        type=str,
        help="The name of the process to check.",
    )
    parser.add_argument(
        "--interval",
        default=30,
        type=int,
        help="The interval at which to check if the process is running.",
    )

    parser.add_argument(
        "--project_id",
        default="sandbox-408020",
        type=str,
        help="The project ID of the Google Cloud project.",
    )
    parser.add_argument(
        "--db_instance_id",
        default="liezl-test",
        type=str,
        help="The ID of the Cloud Spanner instance.",
    )
    parser.add_argument(
        "--db_id",
        default="test-db",
        type=str,
        help="The ID of the Cloud Spanner database.",
    )
    parser.add_argument(
        "--db_table_name",
        default="VirtualMachines",
        type=str,
        help="The name of the table in the database (to be used in sql queries).",
    )
    return parser


def is_process_running(process_name):
    # Iterate over all running process
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if any(process_name.lower() in part.lower() for part in proc.cmdline()):
                cnc_logger.debug(f"{process_name} is running.")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    cnc_logger.debug(f"{process_name} is not running.")
    return False


def listen_for_process(process_name, interval=30, status_change_callback=None):
    """Listen for a process to be running on the local machine.

    This hangs up the process, so it should be run last or in a separate thread.

    Args:
        process_name: The name of the process to check.
        interval: The interval at which to check if the process is running.
        status_change_callback: A callback function to call when the status of the
            process changes.
    """

    if status_change_callback is None:
        status_change_callback = lambda x: x

    cnc_logger.info(f"Checking if {process_name} is running every {interval} seconds.")
    process_running_prev = is_process_running(process_name)

    while True:
        # Get the current status of the process
        proccess_running_current = is_process_running(process_name)

        # If the status has changed, call the callback function
        if proccess_running_current != process_running_prev:
            if status_change_callback:
                status_change_callback(proccess_running_current)

        # Update the previous status
        process_running_prev = proccess_running_current

        time.sleep(interval)


def update_status_in_db(status, db_client: SpannerDatabase, hostname: str):
    """Update the status of the local machine in the database.

    Args:
        status: The status to update in the database.
        db_client: The SpannerDatabase client to use to update the status.
        hostname: The hostname of the local machine.
    """
    cnc_logger.info(f"Updating status in the database for inUse to {status}")

    hostname = socket.gethostname()
    db_client.set_in_use_status(hostname=hostname, in_use=status)


def main(
    process_name=None,
    interval=None,
    project_id=None,
    db_instance_id=None,
    db_id=None,
    db_table_name=None,
    hostname=None,
):
    # Parse the command line arguments
    parser = create_parser()
    args = parser.parse_args()

    # Use the command line arguments or the function arguments
    # Process query arguments
    process_name = process_name or args.process
    interval = interval or args.interval

    # Database arguments
    project_id = project_id or args.project_id
    db_instance_id = db_instance_id or args.db_instance_id
    db_id = db_id or args.db_id
    db_table_name = db_table_name or args.db_table_name
    hostname = hostname or socket.gethostname()

    # Create a SpannerDatabase client
    spanner_db = SpannerDatabase(
        project_id=project_id,
        instance_id=db_instance_id,
        database_id=db_id,
        table_name=db_table_name,
    )

    # Create a callback function to update the status in the database
    status_change_callback = lambda status: update_status_in_db(
        status=status, db_client=spanner_db, hostname=hostname
    )

    # This hangs up the process, should be run last or in a separate thread
    listen_for_process(process_name, interval, status_change_callback)


if __name__ == "__main__":

    try:
        # Running on development environment with vmassign (our repo) installed
        from vmassign import config

        interval = 5
        project_id = config.PROJECT_ID
        db_instance_id = config.DB_INSTANCE_ID
        db_id = config.DB_DATABASE_ID
        db_table_name = config.DB_TABLE_NAME
    except ImportError:
        # Running on VM instance, expecting cli args from start_up.sh
        interval = None
        project_id = None
        db_instance_id = None
        db_id = None
        db_table_name = None

    main(
        interval=interval,
        project_id=project_id,
        db_instance_id=db_instance_id,
        db_id=db_id,
        db_table_name=db_table_name,
    )
