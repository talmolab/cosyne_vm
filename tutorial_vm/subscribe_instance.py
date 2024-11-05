"""This module is meant to be run on a VM instance to subscribe to a topic and listen.

The VM instance will subscribe to a topic with the same name as the hostname of the VM 
instance.
"""

import argparse
import socket

from google.cloud import pubsub_v1

from tutorial_vm.crd_connect import connect_to_crd
from tutorial_vm.database import SpannerDatabase
from tutorial_vm.logging_utils import CloudAndConsoleLogger


def create_parser():
    """Create an argument parser for the script."""

    parser = argparse.ArgumentParser(
        description="Subscribe to a topic and listen for messages."
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


# Set up logging
cnc_logger = CloudAndConsoleLogger(module_name=__name__)


def subscribe_and_listen(
    project_id: str = None,
    db_instance_id: str = None,
    db_id: str = None,
    db_table_name: str = None,
):
    """Subscribe to a topic and listen for messages.

    Args:
        project_id: The project ID of the Google Cloud project.
        db_instance_id: The ID of the Cloud Spanner instance.
        db_id: The ID of the Cloud Spanner database.
        db_table_name: The name of the table in the database (to be used in sql queries).
    """

    # TODO: This value could be entered via the startup script
    project_id = project_id or "sandbox-408020"
    cnc_logger.info(f"\tProject ID: {project_id}")

    # Use hostname to find topic and create a subscription
    hostname = socket.gethostname()
    topic_name = f"projects/{project_id}/topics/{hostname}"
    subscription_name = f"projects/{project_id}/subscriptions/{hostname}"
    cnc_logger.info(f"\tTopic Name: {topic_name}")
    cnc_logger.info(f"\tSubscription Name: {subscription_name}")

    # Set-up database client to use in callback
    db_instance_id = db_instance_id or "liezl-test"
    db_id = db_id or "test-db"
    db_table_name = db_table_name or "VirtualMachines"

    cnc_logger.info(
        f"\tDB Instance ID: {db_instance_id}\n"
        f"\tDB ID: {db_id}\n"
        f"\tDB Table Name: {db_table_name}"
    )

    spanner_db = SpannerDatabase.load_database(
        project_id, db_instance_id, db_id, db_table_name
    )

    def callback(message):
        """Get a pin and command from database and execute command to connect to CRD.

        Args:
            message: The message from the topic.
        """

        # TODO: We could do different actions based on this message.
        cnc_logger.info(f"Received message:\n\t{message.data}")

        try:
            # Connect to CRD using command from database
            cnc_logger.info(f"Getting pin and command from database for {hostname}...")
            pin, command = spanner_db.get_pin_and_crd(hostname=hostname)
            cnc_logger.info(f"Pin: {pin}\nCommand: {command}")

            connect_to_crd(command=command, pin=pin, run=True)
            cnc_logger.info(f"Finished running connect_to_crd.")
        except Exception as e:
            cnc_logger.error(f"An error occurred: {e}")

        message.ack()

    # Create a subscription
    with pubsub_v1.SubscriberClient() as subscriber:
        cnc_logger.info(f"Creating subscription: {subscription_name}")
        try:
            subscriber.create_subscription(name=subscription_name, topic=topic_name)
        except Exception as e:
            cnc_logger.error(
                f"Creating subscription {subscription_name} threw an Exception: {e}."
            )

        cnc_logger.info(f"Subscribing to {subscription_name}...")
        future = subscriber.subscribe(subscription_name, callback)

        # Block the main thread and wait for the subscription to be cancelled or fail
        try:
            cnc_logger.info(f"Listening for messages on {subscription_name}...")
            future.result()
        except Exception as e:
            cnc_logger.error(
                f"Listening for messages on {subscription_name} threw an Exception: {e}."
            )


# This is the entry point for the script and is run on the VM instance by start_up.sh
if __name__ == "__main__":

    parser = create_parser()
    args, _ = parser.parse_known_args()

    project_id = args.project_id
    db_instance_id = args.db_instance_id
    db_id = args.db_id
    db_table_name = args.db_table_name

    subscribe_and_listen(
        project_id=project_id,
        db_instance_id=db_instance_id,
        db_id=db_id,
        db_table_name=db_table_name,
    )
