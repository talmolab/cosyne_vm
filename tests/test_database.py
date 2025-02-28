from lablink_client.database import SpannerDatabase
import pytest


def add_vm(database):
    """Adds a new VM to the database

    Args:
        database (Database): The SpannerDatabase object for testing
    """

    def insert_vm_row(transaction):
        query = "INSERT INTO Users (Hostname, Pin, CrdCmd, UserEmail, inUse) VALUES ('vm1', NULL, NULL, NULL, False)"
        transaction.execute_update(query)
        print("Inserted VM")

    database.run_in_transaction(insert_vm_row)


def test_create_database():
    """
    Test if the SpannerDatabase loads the existing database correctly
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    assert db is not None


def test_get_column_names():
    """
    Test if the column names are fetched correctly
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    actual_column_names = db.get_column_names()
    expected_column_names = ["Hostname", "Pin", "CrdCmd", "UserEmail", "inUse"]
    assert actual_column_names == expected_column_names


def test_read_data_empty():
    """
    Test if the data is read correctly
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    actual_data = db.read_data(table_name="Users")
    expected_data = []
    assert actual_data == expected_data


def test_vm_exists_empty():
    """
    Test if the VM exists in the database
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    actual_result = db.vm_exists(hostname="vm1")
    expected_result = False
    assert actual_result == expected_result


def test_check_vm_exists_empty():
    """
    Test if the VM exists in the database
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    with pytest.raises(ValueError):
        db.check_vm_exists(hostname="vm1")


def test_read_data():
    """
    Test if the data is read correctly
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    add_vm(db.database)
    actual_data = db.read_data(table_name="Users")
    expected_data = [
        {
            "Hostname": "vm1",
            "Pin": None,
            "CrdCmd": None,
            "UserEmail": None,
            "inUse": False,
        }
    ]
    assert actual_data == expected_data


def test_vm_exists():
    """
    Test if the VM exists in the database
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    actual_result = db.vm_exists(hostname="vm1")
    expected_result = True
    assert actual_result == expected_result


def test_check_vm_exists():
    """
    Test if the VM exists in the database
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    db.check_vm_exists(hostname="vm1")


def test_assign_vm():
    """
    Test if the VM is assigned correctly
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    db.find_and_assign_vm(user_email="abc1234@gmail.com")
    actual_data = db.read_data(table_name="Users")
    expected_data = [
        {
            "Hostname": "vm1",
            "Pin": None,
            "CrdCmd": None,
            "UserEmail": "abc1234@gmail.com",
            "inUse": False,
        }
    ]
    assert actual_data == expected_data


def test_get_assigned_vm_details():
    """
    Test if the function raises an Exception when the VM is already in use
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    actual_data = db.get_assigned_vm_details(hostname="vm1")
    expected_data = ("vm1", None, None)
    assert actual_data == expected_data


def test_unassign_vm():
    """
    Test if the VM is unassigned correctly
    """
    db = SpannerDatabase.load_database(
        project_id="vmassign-dev",
        instance_id="vmassign-test",
        database_id="users",
        table_name="Users",
    )
    db.unassign_vm(hostname="vm1")
    actual_data = db.read_data(table_name="Users")
    expected_data = [
        {
            "Hostname": "vm1",
            "Pin": None,
            "CrdCmd": None,
            "UserEmail": None,
            "inUse": False,
        }
    ]
    assert actual_data == expected_data
