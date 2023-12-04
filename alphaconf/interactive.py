import logging
from typing import List

from . import set_application
from .internal.application import Application
from .internal.load_file import read_configuration_file

__doc__ = """Helpers for interactive applications like ipython."""
__all__ = ['mount', 'read_configuration_file', 'load_configuration_file']

application = Application(name="interactive")


def mount(configuration_paths: List[str] = [], setup_logging: bool = True):
    """Mount the interactive application and setup configuration"""
    application.setup_configuration(configuration_paths=configuration_paths)
    set_application(application)
    if setup_logging:
        from . import logging_util

        logging_util.setup_application_logging(
            application.configuration.get('logging', default=None)
        )
    logging.info('Mounted interactive application')


def load_configuration_file(path: str):
    """Read a configuration file and add it to the context configuration"""
    config = read_configuration_file(path)
    logging.debug('Loading configuration from path: %s', path)
    application.configuration.setup_configuration(config)
