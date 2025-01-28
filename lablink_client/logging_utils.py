"""This module contains a class for logging to both the console and Cloud Logging.

This script is run on a VM instance, but is also used in the main application.
"""

import logging
import pprint

from google.cloud import logging as cloud_logging


class CloudAndConsoleLogger:

    def __init__(self, module_name: str, level=logging.DEBUG, format=None):
        self.name = module_name

        format = format or "%(module)s[%(levelname)s]: %(message)s"
        self.formatter = logging.Formatter(format, datefmt="%H:%M:%S")
        self.level = level
        self.console_logger = self.setup_console_logging(
            level=self.level, formatter=self.formatter
        )   
        self._cloud_logger = None


    @property
    def cloud_logger(self):
        if self._cloud_logger is None:
            self._cloud_logger = self.setup_cloud_logging(
                level=self.level, formatter=self.formatter
            )
        return self._cloud_logger

    def __getattr__(self, name):
        """Pass the log call to both the console and cloud loggers."""

        def wrapper(*args, **kwargs):
            getattr(self.console_logger, name)(*args, **kwargs)
            getattr(self.cloud_logger, name)(*args, **kwargs)

        return wrapper

    def pprint(self, obj, level=logging.INFO):
        """Pretty-print an object and log the output.

        Args:
            obj: The object to pretty-print and log.
            level (int, optional): The logging level. Defaults to logging.INFO.
        """

        pp = pprint.PrettyPrinter(indent=4)
        pretty_str = pp.pformat(obj)
        self.log(level, pretty_str)

    # TODO: This is duplicated in database.py
    def setup_console_logging(
        self, level=logging.DEBUG, formatter: logging.Formatter = None
    ):
        """Set up logging for the module which prints to stdout.

        Args:
            level (int, optional): The logging level. Defaults to logging.DEBUG.
            formatter (logging.Formatter): The formatter to use for the logs.

        Returns:
            logging.Logger: The logger for the module.
        """

        # Set up logging
        logger = logging.getLogger(f"{self.name}_console_logger")
        logger.setLevel(level)

        # Create a console handler to actually show messages
        handler = logging.StreamHandler()
        handler.setLevel(level)

        # Set the formatter for the handler
        handler.setFormatter(formatter)

        # Add the console handler to the logger
        logger.addHandler(handler)

        return logger

    def setup_cloud_logging(
        self, level=logging.DEBUG, formatter: logging.Formatter = None
    ):
        """Set up logging to Cloud Logging.

        Args:
            level (int, optional): The logging level. Defaults to logging.DEBUG.
            formatter (logging.Formatter): The formatter to use for the logs.

        Returns:
            logging.Logger: The logger for the module.
        """

        # Set up logging
        client = cloud_logging.Client()

        # Connect the logger to the Cloud Logging handler
        handler = client.get_default_handler()

        # Set the formatter for the handler
        handler.setFormatter(formatter)

        cloud_logger = logging.getLogger(f"{self.name}_cloud_logger")
        cloud_logger.setLevel(level)  # defaults to WARN
        cloud_logger.addHandler(handler)

        return cloud_logger
