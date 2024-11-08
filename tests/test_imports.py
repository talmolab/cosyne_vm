"""Module that tests the imports of the package."""


def test_import():
    import lablink_client

    from lablink_client import crd_connect
    from lablink_client import database
    from lablink_client import logging_utils
    from lablink_client import subscribe_instance
    from lablink_client import update_inuse_status


if __name__ == "__main__":

    # Add the parent directory to the pythonpath (pytest setup to do this automatically)
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    # Run the test
    test_import()
