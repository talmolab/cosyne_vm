from lablink_client.database import SpannerDatabase
import unittest

class TestSpannerDatabase(unittest.TestCase):
    def test_create_database(self):
        """
        Test if the SpannerDatabase loads the existing database correctly
        """
        db = SpannerDatabase.load_database(project_id="vmassign-dev", instance_id="vmassign-test", database_id="users", table_name="Users")
        self.assertIsNotNone(db)
    
    def test_get_column_names(self):
        """
        Test if the column names are fetched correctly
        """
        db = SpannerDatabase.load_database(project_id="vmassign-dev", instance_id="vmassign-test", database_id="users", table_name="Users")
        actual_column_names = db.get_column_names()
        expected_column_names = ['Hostname', 'Pin', 'CrdCmd', 'UserEmail', 'inUse']
        self.assertEqual(actual_column_names, expected_column_names)

    def test_read_data(self):
        """
        Test if the data is read correctly
        """
        db = SpannerDatabase.load_database(project_id="vmassign-dev", instance_id="vmassign-test", database_id="users", table_name="Users")
        actual_data = db.read_data(table_name="Users")
        expected_data = []
        self.assertEqual(actual_data, expected_data)

    def test_vm_exists(self):
        """
        Test if the VM exists in the database
        """
        db = SpannerDatabase.load_database(project_id="vmassign-dev", instance_id="vmassign-test", database_id="users", table_name="Users")
        actual_result = db.vm_exists(hostname="vm1")
        self.assertFalse(actual_result)
    
    def test_vm_exists(self):
        """
        Test if the VM exists in the database
        """
        db = SpannerDatabase.load_database(project_id="vmassign-dev", instance_id="vmassign-test", database_id="users", table_name="Users")
        self.assertRaises(ValueError, db.check_vm_exists, hostname="vm1")