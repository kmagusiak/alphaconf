import logging
from typing import List

# absolute import to make sure it's properly initialized
import alphaconf

from .internal.load_file import read_configuration_file

__doc__ = """Helpers for interactive applications."""
__all__ = ['mount', 'read_configuration_file', 'load_configuration_file']


def mount(configuration_paths: List[str] = [], setup_logging: bool = True):
    """Mount a new application with a setup configuration"""
    app = alphaconf.Application(name='interactive')
    app.setup_configuration(
        arguments=False, configuration_paths=configuration_paths, setup_logging=setup_logging
    )
    alphaconf.set_application(app, merge=True)
    logging.info('Mounted interactive application')


def load_configuration_file(path: str):
    """Read a configuration file and add it to the context configuration"""
    config = read_configuration_file(path)
    logging.debug('Loading configuration from path: %s', path)
    alphaconf.setup_configuration(config)
