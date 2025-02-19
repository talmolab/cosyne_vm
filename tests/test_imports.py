"""Module that tests the imports of the package."""


def test_import():
    import lablink_client

    from lablink_client import crd_connect
    from lablink_client import database
    from lablink_client import logging_utils
    from lablink_client import subscribe_instance
    from lablink_client import update_inuse_status
