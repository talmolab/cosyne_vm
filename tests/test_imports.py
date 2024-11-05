"""Module that tests the imports of the package."""


def test_import():
    import tutorial_vm

    from tutorial_vm import crd_connect
    from tutorial_vm import database
    from tutorial_vm import logging_utils
    from tutorial_vm import subscribe_instance
    from tutorial_vm import update_inuse_status


if __name__ == "__main__":

    # Add the parent directory to the pythonpath (pytest setup to do this automatically)
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    # Run the test
    test_import()
