"""This module contains code to interact with a Cloud Spanner database.

This script is run on a VM instance, but is also used in the main application.
"""

from google.cloud import spanner

try:
    # This is used when running on a VM instance
    from logging_utils import CloudAndConsoleLogger
except ImportError:
    # This is used when running in the main application
    from vmassign import CloudAndConsoleLogger


cnc_logger = CloudAndConsoleLogger(module_name=__name__)


class SpannerDatabase:
    def __init__(self, project_id, instance_id, database_id, table_name):
        """Initializes a SpannerDatabase object.

        Args:
            project_id: The ID of the project that owns the Cloud Spanner instance.
            instance_id: The ID of the Cloud Spanner instance.
            database_id: The ID of the Cloud Spanner database.
            table_name: The name of the table in the database (to be used in sql queries).

        Returns:
            A SpannerDatabase object.
        """

        self.project_id = project_id
        self.instance_id = instance_id
        self.database_id = database_id

        # TODO: There could be more than a single table in a database
        self.table_name = table_name

        # Latest query and results
        self.query = None

        # Instantiate a client and get a Cloud Spanner instance and database by ID.
        self.spanner_client = spanner.Client(project=project_id)
        self.instance = self.spanner_client.instance(instance_id)
        self.database = self.instance.database(database_id)

        # TODO: This really only makes this class compatible with a specific schema
        # Get the column names of the database
        self.column_names = self.get_column_names()
        self.pin_column = "Pin"
        self.crd_column = "CrdCmd"
        self.hostname_column = "Hostname"
        self.user_email_column = "UserEmail"
        self.in_use_column = "inUse"
        for column in [
            self.pin_column,
            self.crd_column,
            self.hostname_column,
            self.user_email_column,
            self.in_use_column,
        ]:
            if column not in self.column_names:
                raise ValueError(f"Column {column} does not exist in the database")

    def get_column_names(self, table_name=None):
        """Gets the column names of the database."""

        if table_name is None:
            table_name = self.table_name

        query = f"""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = @table_name
        """
        params = {"table_name": table_name}
        param_types = {"table_name": spanner.param_types.STRING}

        with self.database.snapshot() as snapshot:
            results = snapshot.execute_sql(
                query, params=params, param_types=param_types
            )

        column_names = [r[0] for r in results]

        return column_names

    def process_results(self, results):
        """Processes the results of an SQL query.

        Args:
            results: The result set from the SQL query.

        Returns:
            A list of dictionaries containing the data from the database. Each dictionary
            represents a row in the table with the column names as keys and the column values
            as values.
        """

        # Convert the result set to a list to populate the metadata
        rows = list(results)

        # Get the column names from the metadata
        column_names = [field.name for field in results.metadata.row_type.fields]

        # Convert all rows to dictionaries
        data = [dict(zip(column_names, row)) for row in rows]

        return data

    def execute_sql_and_process_results(
        self, query, params=None, param_types=None
    ) -> list:
        """Executes an SQL query and processes the results.

        Args:
            query: The SQL query to execute.

        Returns:
            A list of dictionaries containing the data from the database. Each dictionary
            represents a row in the table with the column names as keys and the column values
            as values.
        """

        # Execute the SQL query
        with self.database.snapshot() as snapshot:
            results = snapshot.execute_sql(
                query, params=params, param_types=param_types
            )

        # Process the results
        data = self.process_results(results)

        return data

    def read_data(
        self,
        table_name=None,
    ):
        """Reads all data from the database for specified table.

        Args:
            table_name: The name of the table in the database (to be used in sql queries).
            If None, the default table name is used (self.table_name).

        Returns:
            A list of dictionaries containing the data from the database. Each dictionary
            represents a row in the table with the column names as keys and the column values
            as values.
        """

        if table_name is None:
            table_name = self.table_name

        query = f"SELECT * FROM {table_name}"
        self.query = query

        data = self.execute_sql_and_process_results(query)
        cnc_logger.debug(data)

        return data

    @classmethod
    def load_database(cls, project_id, instance_id, database_id, table_name=None):
        """Loads an existing database from Cloud Spanner.

        Args:
            project_id: The ID of the project that owns the Cloud Spanner instance.
            instance_id: The ID of the Cloud Spanner instance.
            database_id: The ID of the Cloud Spanner database.
            table_name: The name of the table in the database (to be used in sql queries).

        Returns:
            A SpannerDatabase object.
        """

        return cls(project_id, instance_id, database_id, table_name)

    def add_crd_and_pin(self, hostname, pin, cmd, table_name=None, override=False):
        """Adds a command and pin to the given hostname in the database when a user connects to the VM with the corresponding hostname

        Args:
            hostname: The hostname of the VM to be added to the database
            pin: The pin that user sets to be added to the database
            cmd: The CRD command to be added to the database
            table_name: The name of the table in the database (to be used in sql queries).
            override: If True, the pin and command will be updated even if the hostname
                already has a pin or command. If False, a ValueError will be raised if the
                hostname already has a pin or command.

        Raises:
            ValueError: If the hostname does not exist in the database
            ValueError: If the hostname already has a pin or command
        """

        if table_name is None:
            table_name = self.table_name

        # Checks if the hostname exists in the database
        self.check_vm_exists(hostname, table_name)

        # Checks if the hostname already has a pin or command)
        if not override and self.get_pin_and_crd(hostname) != (None, None):
            raise ValueError(f"The hostname {hostname} already has a pin or command")

        # Adds the given CRD command and pin to the database
        def update_cmd_and_pin(transaction):
            query = (
                f"UPDATE {table_name} SET {self.pin_column} = @pin, "
                f"{self.crd_column} = @cmd WHERE {self.hostname_column} = @hostname"
            )
            self.query = query
            row_ct = transaction.execute_update(
                query,
                params={"pin": pin, "cmd": cmd, "hostname": hostname},
                param_types={
                    "pin": spanner.param_types.STRING,
                    "cmd": spanner.param_types.STRING,
                    "hostname": spanner.param_types.STRING,
                },
            )
            cnc_logger.debug(
                f"{row_ct} record(s) updated for {self.hostname_column}={hostname} "
                f"with {self.pin_column}={pin} and {self.crd_column}={cmd}"
            )

        self.database.run_in_transaction(update_cmd_and_pin)

    def get_pin_and_crd(self, hostname, table_name=None):
        """Gets the pin and command for the given hostname from the database

        Args:
            hostname: The hostname of the VM to get the pin and command from

        Returns:
            A tuple containing the pin and command for the given hostname. For example:

            (pin, cmd)

        Raises:
            ValueError: If the hostname does not exist in the database
        """

        if table_name is None:
            table_name = self.table_name

        # Check if the hostname exists in the database
        self.check_vm_exists(hostname, table_name)

        query = f"SELECT * FROM {table_name} WHERE {self.hostname_column} = @hostname"
        self.query = query

        data = self.execute_sql_and_process_results(
            query,
            params={"hostname": hostname},
            param_types={"hostname": spanner.param_types.STRING},
        )

        pin, command = data[0][self.pin_column], data[0][self.crd_column]
        cnc_logger.debug(f"Pin and CRD for {hostname}: {pin}, {command}")

        return pin, command

    def vm_exists(self, hostname, table_name=None):
        """Checks if the given hostname exists in the database

        Args:
            hostname: The hostname to check

        Returns:
            True if the hostname exists in the database, False otherwise
        """

        if table_name is None:
            table_name = self.table_name

        query = f"SELECT * FROM {table_name} WHERE {self.hostname_column} = @hostname"
        self.query = query

        with self.database.snapshot() as snapshot:
            result = snapshot.execute_sql(
                query,
                params={"hostname": hostname},
                param_types={"hostname": spanner.param_types.STRING},
            )
            for row in result:
                return True

        return False

    def check_vm_exists(self, hostname, table_name=None):
        """Checks if the given hostname exists in the database.

        Args:
            hostname: The hostname to check
            table_name: The name of the table in the database (to be used in sql queries).

        Raises:
            ValueError: If the hostname does not exist in the database

        Returns:
            None
        """

        if not self.vm_exists(hostname, table_name):
            raise ValueError(f"The hostname {hostname} does not exist in the database")

    def get_unassigned_vms(self, table_name=None) -> list:
        """Gets the hostnames of the unassigned VMs.

        Returns:
            A list of hostnames of the VMs that do not have a user email, pin,  or
            command assigned to them.
        """

        if table_name is None:
            table_name = self.table_name

        query = (
            f"SELECT {self.hostname_column} FROM {table_name} "
            f"WHERE {self.pin_column} IS NULL AND {self.crd_column} IS NULL "
            f"AND {self.user_email_column} IS NULL"
        )
        self.query = query

        data = self.execute_sql_and_process_results(query)

        unassigned_vms = [row[self.hostname_column] for row in data]
        cnc_logger.debug(f"Unassigned VMs: {unassigned_vms}")

        return unassigned_vms

    def assign_vm(self, hostname, user_email, table_name=None):
        """Assigns a VM to a user in the database

        Args:
            hostname: The hostname of the VM to be assigned to the user
            user_email: The email of the user to assign the VM to

        Raises:
            ValueError: If the hostname does not exist in the database
            ValueError: If the hostname already has a user assigned to it
        """
        if table_name is None:
            table_name = self.table_name

        # Checks if the hostname exists in the database
        self.check_vm_exists(hostname, table_name)

        # Assigns the VM to the user
        def update_user_email(transaction):
            query = (
                f"UPDATE {self.table_name} SET {self.user_email_column} = @user_email "
                f"WHERE {self.hostname_column} = @hostname"
            )
            self.query = query
            row_ct = transaction.execute_update(
                query,
                params={"user_email": user_email, "hostname": hostname},
                param_types={
                    "user_email": spanner.param_types.STRING,
                    "hostname": spanner.param_types.STRING,
                },
            )
            cnc_logger.debug(
                f"{row_ct} record(s) updated for {self.hostname_column}={hostname} "
                f"with {self.user_email_column}={user_email}"
            )

        self.database.run_in_transaction(update_user_email)

    def get_unused_vms(self, table_name=None):
        """Get the hostnames of the VMs that are not being used.

        While the VMs are not being used, they can be assigned to a user. A VM is not
        being used if the inUse column is set to False which is the default value. The
        inUse column is set to True when the VM is running the SLEAP executable.

        Returns:
            The hostnames of the VMs that are not using by any user
        """

        if table_name is None:
            table_name = self.table_name

        query = f"SELECT {self.hostname_column} FROM {table_name} WHERE {self.in_use_column} IS NOT TRUE"
        self.query = query

        data = self.execute_sql_and_process_results(query)

        unused_vms = [row[self.hostname_column] for row in data]
        cnc_logger.debug(f"Unused VMs: {unused_vms}")

        return unused_vms


# Debug/demo code, not to be used on VM instances or in production
if __name__ == "__main__":
    """Run this with a command line argument to test the database. For example:

    python database.py A/0asfhsadfh
    """

    import getpass
    import sys

    try:
        from vmassign import config
    except Exception as e:
        message = (
            "This script must be run from the main project directory, "
            "not from a VM instance. If you are running from the main project "
            "directory, make sure you have followed the installation instructions "
            "in the README.md"
        )
        cnc_logger.error(f"Error: {e}\n{message}")

    assign_vm = False

    # Edit this info in config.py
    project_id = config.PROJECT_ID
    instance_id = config.INSTANCE_ID
    database_id = config.DATABASE_ID
    table_name = config.TABLE_NAME

    spanner_db = SpannerDatabase.load_database(
        project_id, instance_id, database_id, table_name
    )

    unassigned_vms = spanner_db.get_unassigned_vms()

    vm_hostname = getpass.getuser() + "-vm-1"
    user_email = "spoof@talmolab.org"
    spanner_db.assign_vm(hostname=vm_hostname, user_email=user_email)

    spanner_db.get_unassigned_vms()

    if assign_vm:
        pin = "723177"
        code = sys.argv[1]
        command = (
            f"DISPLAY= /opt/google/chrome-remote-desktop/start-host --code='{code}' "
            f"--redirect-url='https://remotedesktop.google.com/_/oauthredirect' --name=$(hostname)"
        )
        spanner_db.add_crd_and_pin(vm_hostname, pin, command, override=True)

        pin_retrieved, command_retrieved = spanner_db.get_pin_and_crd(vm_hostname)
        assert pin_retrieved == pin
        assert command_retrieved == command
