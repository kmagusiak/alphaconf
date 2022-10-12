import logging

from . import set_application, setup_configuration
from .application import Application
from .load_file import read_configuration_file

__doc__ = """Helpers for interactive applications.
"""
__all__ = ['mount', 'read_configuration_file', 'load_configuration_file']


def mount(configuration_paths=[], setup_logging=True):
    """Mount a new application with a setup configuration"""
    app = Application(name='interactive')
    app.setup_configuration(
        arguments=False, configuration_paths=configuration_paths, setup_logging=setup_logging
    )
    set_application(app, merge=True)
    logging.info('Mounted interactive application')


def load_configuration_file(path):
    """Read a configuration file and add it to the context configuration"""
    config = read_configuration_file(path)
    setup_configuration(config)
