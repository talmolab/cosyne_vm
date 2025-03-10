"""This module contains code to interact with a Cloud Spanner database.

This script is run on a VM instance, but is also used in the main application.
"""

from google.cloud import spanner
from google.api_core.exceptions import RetryError

try:
    # This is used when running on a VM instance
    from lablink_client.logging_utils import CloudAndConsoleLogger
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
        try:
            with self.database.snapshot() as snapshot:
                results = snapshot.execute_sql(
                    query, params=params, param_types=param_types
                )
        except RetryError as e:
            cnc_logger.error(f"Error: {e}")
            cnc_logger(
                "You may need to rerun authentication commands:"
                "\n\t`gcloud auth application-default login`"
            )
            raise e

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

    # Used on local VM
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

    def unassign_vm(self, hostname, table_name=None):
        """Reset the given VM instance so that it can be assigned to another user.

        Args:
            hostname: The hostname of the VM to be reset

        Raises:
            ValueError: If the hostname does not exist in the database
        """

        if table_name is None:
            table_name = self.table_name

        # Checks if the hostname exists in the database
        self.check_vm_exists(hostname, table_name)

        # Reset the VM instance
        def reset(transaction):
            query = (
                f"UPDATE {table_name} SET {self.pin_column} = NULL, "
                f"{self.crd_column} = NULL, {self.user_email_column} = NULL, "
                f"{self.in_use_column} = FALSE "
                f"WHERE {self.hostname_column} = @hostname"
            )
            self.query = query
            row_ct = transaction.execute_update(
                query,
                params={"hostname": hostname},
                param_types={"hostname": spanner.param_types.STRING},
            )
            cnc_logger.debug(
                f"{row_ct} record(s) updated for {self.hostname_column}={hostname} "
                f"with {self.pin_column}=NULL, {self.crd_column}=NULL, "
                f"{self.user_email_column}=NULL"
            )

        self.database.run_in_transaction(reset)

    # Only used in __main__ (for debug)
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

    def find_and_assign_vm(self, user_email):
        """This method finds and assigns a VM to a user using a transaction.

        Args:
            user_email: The user's email to link to a VM instance.
        """

        def transaction(transaction):
            # Query for an unassigned row
            query = (
                f"SELECT {self.hostname_column} FROM {self.table_name} "
                f"WHERE {self.user_email_column} IS NULL LIMIT 1"
            )
            results = transaction.execute_sql(query)
            data = self.process_results(results=results)
            # rows = list(transaction.execute_sql(query))
            if not data:
                cnc_logger.error(
                    f"User {user_email} requested a VM, "
                    "but no unassigned VMs available"
                )
                raise ValueError("No unassigned VMs available :(")

            # Assign the first unassigned row to the user
            hostname = data[0][self.hostname_column]
            update_statement = (
                f"UPDATE {self.table_name} "
                f"SET {self.user_email_column} = @user_email "
                f"WHERE {self.hostname_column} = @hostname"
            )
            params = {"user_email": user_email, "hostname": hostname}
            param_types = {
                "user_email": spanner.param_types.STRING,
                "hostname": spanner.param_types.STRING,
            }
            transaction.execute_update(
                update_statement, params=params, param_types=param_types
            )
            cnc_logger.info(
                f"VM with hostname [{hostname}] assigned to user [{user_email}]"
            )

            return hostname

        # We will keep trying to assign a user a VM until we succeed!
        while True:
            try:
                # Run the transaction
                hostname = self.database.run_in_transaction(transaction)
                return hostname
            except Exception as e:
                cnc_logger.error(f"Error: {e}")
                raise e

    # Used in manage
    def get_assigned_vms(self, table_name=None):
        """Gets the hostnames of the VMs that are assigned to a user.

        Args:
            table_name: The name of the table in the database to run queries on. Default uses self.table_name.

        Returns:
            A list of hostnames of the VMs that have a user email assigned to them.
        """

        if table_name is None:
            table_name = self.table_name

        query = (
            f"SELECT {self.hostname_column} "
            f"FROM {table_name} "
            f"WHERE {self.user_email_column} IS NOT NULL"
        )
        self.query = query

        data = self.execute_sql_and_process_results(query)

        assigned_vms = [row[self.hostname_column] for row in data]

        return assigned_vms

    def get_assigned_vm_details(self, email: str, table_name=None) -> list:
        """Gets the hostname, pin, and crd of the assigned VM.

        Args:
            email: The email of the user to get the assigned VM details for.

        Rasies:
            ValueError: If the email does not exist in the database

        Returns:
            A tuple of (hostname, pin, command) for the VM assigned to a user email.
        """

        if table_name is None:
            table_name = self.table_name

        query = (
            f"SELECT * FROM {table_name} "
            f"WHERE {self.user_email_column} = @user_email"
        )
        params = {"user_email": email}
        param_types = {"user_email": spanner.param_types.STRING}
        self.query = query

        data = self.execute_sql_and_process_results(
            query, params=params, param_types=param_types
        )

        if not data:
            raise ValueError(f"The email {email} does not exist in the database")

        hostname = data[0][self.hostname_column]
        pin = data[0][self.pin_column]
        command = data[0][self.crd_column]

        cnc_logger.pprint(
            {
                "VM Details for": email,
                self.hostname_column: hostname,
                self.pin_column: pin,
                self.crd_column: command,
            }
        )

        return hostname, pin, command

    # Unused in app or local vm
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

    def get_unassigned_vms_count(self, table_name=None) -> int:
        """Gets the number of unassigned VMs.

        Returns:
            The number of VMs that do not have a user email, pin, or
            command assigned to them.
        """

        if table_name is None:
            table_name = self.table_name

        query = (
            f"SELECT COUNT({self.hostname_column}) FROM {table_name} "
            f"WHERE {self.pin_column} IS NULL AND {self.crd_column} IS NULL "
            f"AND {self.user_email_column} IS NULL"
        )
        self.query = query

        # Execute the SQL query
        with self.database.snapshot() as snapshot:
            results = snapshot.execute_sql(query)

        rows = list(results)
        unassigned_vms_count = rows[0][0] if rows else 0
        cnc_logger.debug(f"Number of unassigned VMs: {unassigned_vms_count}")

        return unassigned_vms_count

    # Not used (yet)
    def get_unused_vms(self, table_name=None):
        """Get the hostnames of the VMs that are not being used.

        While the VMs are not being used, they can be assigned to a user. A VM is not
        being used if the inUse column is set to False which is the default value. The
        inUse column is set to True when the VM is running the SLEAP executable.

        Args:
            table_name: The name of the table in the database to run queries on. Default uses self.table_name.

        Returns:
            A list of hostnames of the VMs that are not being used.
        """

        if table_name is None:
            table_name = self.table_name

        query = f"SELECT {self.hostname_column} FROM {table_name} WHERE {self.in_use_column} IS NOT TRUE"
        self.query = query

        data = self.execute_sql_and_process_results(query)

        unused_vms = [row[self.hostname_column] for row in data]
        cnc_logger.debug(f"Unused VMs: {unused_vms}")

        return unused_vms

    # Used on local VM
    def set_in_use_status(self, hostname, in_use: bool, table_name=None):
        """Updates the inUse status of a given VM in the database.

        The inUse status is set to True when the VM is running the SLEAP executable and
        False when it is not.

        Args:
            hostname: The hostname of the VM to update the inUse status for
            in_use: The boolean value to set the inUse column to.
            table_name: The name of the table in the database to run queries on. Default uses self.table_name.
            Default uses self.table_name.

        Raises:
            ValueError: If the hostname does not exist in the database
        """
        if table_name is None:
            table_name = self.table_name

        # Checks if the hostname exists in the database
        self.check_vm_exists(hostname, table_name)

        # Update inUse status
        def update_in_use(transaction):
            query = (
                f"UPDATE {table_name} SET {self.in_use_column} = @in_use "
                f"WHERE {self.hostname_column} = @hostname"
            )
            self.query = query
            row_ct = transaction.execute_update(
                query,
                params={"in_use": in_use, "hostname": hostname},
                param_types={
                    "in_use": spanner.param_types.BOOL,
                    "hostname": spanner.param_types.STRING,
                },
            )
            cnc_logger.debug(
                f"{row_ct} record(s) updated for {self.hostname_column}={hostname} "
                f"with {self.in_use_column}={in_use}"
            )

        self.database.run_in_transaction(update_in_use)

    # Used in manage
    def get_user_email(self, hostname, table_name=None):
        """Gets the email of the user assigned to the given hostname.

        Args:
            hostname: The hostname of the VM to get the user email for
            table_name: The name of the table in the database (to be used in sql queries).

        Returns:
            The email of the user assigned to the given hostname.
        """

        if table_name is None:
            table_name = self.table_name

        query = (
            f"SELECT {self.user_email_column} "
            f"FROM {table_name} "
            f"WHERE {self.hostname_column} = @hostname"
        )
        self.query = query

        with self.database.snapshot() as snapshot:
            results = snapshot.execute_sql(
                query,
                params={"hostname": hostname},
                param_types={"hostname": spanner.param_types.STRING},
            )

            for row in results:
                return row[0]

    # Used on local VM
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


def manually_assign_and_crd_connect():
    """Run this with a command line argument to test the database. For example:

    python database.py A/0asfhsadfh
    """

    # Debug/demo code, not to be used on VM instances or in production

    import getpass
    import subprocess

    try:
        from vmassign import config
        from vmassign.vm.local.crd_connect import reconstruct_command
    except Exception as e:
        message = (
            "This script must be run from the main project directory, "
            "not from a VM instance. If you are running from the main project "
            "directory, make sure you have followed the installation instructions "
            "in the README.md"
        )
        cnc_logger.error(f"Error: {e}\n{message}")

    assign_vm = True

    # Edit this info in config.py
    project_id = config.PROJECT_ID
    instance_id = config.DB_INSTANCE_ID
    database_id = config.DB_DATABASE_ID
    table_name = config.DB_TABLE_NAME

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
        command = reconstruct_command()
        spanner_db.add_crd_and_pin(vm_hostname, pin, command, override=True)

        pin_retrieved, command_retrieved = spanner_db.get_pin_and_crd(vm_hostname)
        assert pin_retrieved == pin
        assert command_retrieved == command

        publish_cmd = f"gcloud pubsub topics publish {vm_hostname} --message='start'"
        args = publish_cmd.split()
        subprocess.run(args)


if __name__ == "__main__":
    # Debug/demo code, not to be used on VM instances or in production
    manually_assign_and_crd_connect()
