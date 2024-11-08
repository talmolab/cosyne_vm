"""This script connects to a Linux remote machine via CRD.

The command needs to be retrieved from https://remotedesktop.google.com/headless/

Example:
    $ python crd_connect.py <copy/pasted command from CRD>

This script is run on a VM instance only.
"""

import argparse
import random
import subprocess

from lablink_client.logging_utils import CloudAndConsoleLogger


# Set up logging
cnc_logger = CloudAndConsoleLogger(module_name=__name__)


def create_parser():
    """Creates a parser for the command line arguments.

    Returns:
        argparse.ArgumentParser: The parser for the command line arguments.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--code",
        help="Unique code to allow connection via CRD with specific Google login.",
        type=str,
        default=None,
    )

    return parser


def construct_command(args):
    """Constructs the Linux CRD command to connect to a remote machine.

    Args:
        args (argparse.Namespace): The command line arguments.

    Returns:
        str: The Linux CRD command to connect to a remote machine.
    """

    redirect_url = "'https://remotedesktop.google.com/_/oauthredirect'"
    name = "$(hostname)"

    command = "DISPLAY= /opt/google/chrome-remote-desktop/start-host"
    command += f" --code={args.code}"
    command += f" --redirect-url={redirect_url}"
    command += f" --name={name}"

    return command


def enforce_pin_type(pin) -> str:
    """Enforces that the pin is a string of 6 digits.

    Converts integers to strings and removes leading/trailing whitespace.

    Returns:
        str: The pin as a string if it was a string or integer otherwise None.
    """

    if isinstance(pin, int):
        pin = str(pin)
    if isinstance(pin, str):
        pin = pin.strip()
    else:
        pin = None
    return pin


def generate_pin(pin_length=6):
    """Generates a random 6-digit PIN.

    Args:
        pin_length (int): The length of the PIN.

    Returns:
        str: The generated PIN.
    """

    return "".join(random.choice("0123456789") for _ in range(pin_length))


def reconstruct_command(command: str = None):
    """Reconstructs the Chrome Remote Desktop command.

    Args:
        command (str): The command to connect to the remote machine.
    """

    if command is None:
        args_to_parse = None  # Uses sys.argv
    else:
        args_to_parse = command.split()

    # Parse the command line arguments
    parser = create_parser()
    args, _ = parser.parse_known_args(args=args_to_parse)

    cnc_logger.info("Args:")
    cnc_logger.pprint(vars(args))

    # Construct the command to connect to the remote machine
    command = construct_command(args)
    cnc_logger.info(f"Command: {command}")

    return command


def connect_to_crd(command=None, pin=None, run=True):
    """Connects to a remote machine via CRD.

    Args:
        command (str): The command to connect to the remote machine.
        pin (str): The PIN to use to connect to the remote machine.
        run (bool): Whether to run the command or not.
    """

    # Parse the command line arguments
    command = reconstruct_command(command)

    # Generate a sequence of 6 random integers between 0 and 9
    pin = enforce_pin_type(pin)
    if pin is None or len(pin) != 6:
        cnc_logger.warning("Generating a random PIN...")
        pin = generate_pin()
    cnc_logger.info(f"Pin: {pin}")

    # Add a newline to the pin and then add the pin again for verification
    pin_with_newline = pin + "\n"
    pin_with_verification = pin_with_newline + pin_with_newline

    if run:
        # Run the command and capture the output
        result = subprocess.run(
            command,
            input=pin_with_verification,
            shell=True,
            capture_output=True,
            text=True,
        )

        cnc_logger.debug("Output:\n" + result.stdout)

        if result.stderr:
            cnc_logger.error("Error:" + result.stderr)


if __name__ == "__main__":
    # command = "DISPLAY= /opt/google/chrome-remote-desktop/start-host --code='4/3fQi9BR_wLaDbpFpEM7dHOAMpkWj07OHvWkIg' --redirect-url='https://remotedesktop.google.com/_/oauthredirect' --name=$(hostname)"
    # connect_to_crd(command=command, run=False)
    connect_to_crd(run=True)
