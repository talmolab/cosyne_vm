import argparse
import lablink_client.crd_connect as crd_connect
import pytest

def test_construct_commands():
    """
    Test if the commands are constructed correctly given the code in the argumentsa
    """
    test_args = ["--code", "4/0ASVgi3KnW7VzjUano4ZZeEk802-X3aZ-DoS5fN9sNi6OAspzjB2ZbNI85pgmvTCSLayuH1g"]

    parser = crd_connect.create_parser()
    args = parser.parse_args(test_args)
    actual_crd_command = crd_connect.construct_command(args)
    expected_crd_command = "DISPLAY= /opt/google/chrome-remote-desktop/start-host --code=4/0ASVgi3KnW7VzjUano4ZZeEk802-X3aZ-DoS5fN9sNi6OAspzjB2ZbNI85pgmvTCSLayuH1g --redirect-url='https://remotedesktop.google.com/_/oauthredirect' --name=$(hostname)"
    assert actual_crd_command == expected_crd_command

def test_enforce_pin_type():
    """
    Test if the pin type is enforced correctly
    """
    integer_pin = 123456
    actual_pin = crd_connect.enforce_pin_type(integer_pin)
    expected_pin = "123456"
    assert actual_pin == expected_pin

    string_pin = "123456"
    actual_pin = crd_connect.enforce_pin_type(string_pin)
    expected_pin = "123456"
    assert actual_pin == expected_pin

    string_pin_with_spaces = " 123456 "
    actual_pin = crd_connect.enforce_pin_type(string_pin_with_spaces)
    expected_pin = "123456"
    assert actual_pin == expected_pin

    string_pin_with_letters = "123abc"
    actual_pin = crd_connect.enforce_pin_type(string_pin_with_letters)
    expected_pin = "123abc"
    assert expected_pin == actual_pin

    list_pin = [1, 2, 3, 4, 5, 6]
    actual_pin = crd_connect.enforce_pin_type(list_pin)
    assert actual_pin is None

def test_reconstruct_command():
    none_reconstructed_command = crd_connect.reconstruct_command(None)
    expected_reconstructed_command = "DISPLAY= /opt/google/chrome-remote-desktop/start-host --code=None --redirect-url='https://remotedesktop.google.com/_/oauthredirect' --name=$(hostname)"
    assert none_reconstructed_command == expected_reconstructed_command

    empty_reconstructed_command = crd_connect.reconstruct_command("")
    expected_reconstructed_command = "DISPLAY= /opt/google/chrome-remote-desktop/start-host --code=None --redirect-url='https://remotedesktop.google.com/_/oauthredirect' --name=$(hostname)"
    assert empty_reconstructed_command == expected_reconstructed_command

    real_command = "DISPLAY= /opt/google/chrome-remote-desktop/start-host --code='4/0ASVgi3LBTDPqTU4xJELo6Scw4gu8nL6KWZe1RkzoZeo3oqNTLViv2BLmx48SLyQBb7c7mg' --redirect-url='https://remotedesktop.google.com/_/oauthredirect' --name=$(hostname)"
    real_reconstructed_command = crd_connect.reconstruct_command(real_command)
    assert real_reconstructed_command == real_command