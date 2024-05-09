import logging
import re
from typing import Callable, MutableSequence, Optional, TypeVar

from .frozendict import frozendict  # noqa: F401 (expose)
from .internal.configuration import Configuration
from .internal.load_file import read_configuration_file

__doc__ = """AlphaConf

Based on omegaconf, provide a simple way to declare and run your application
while loading the configuration from various files and command line
arguments.

Use `alphaconf.get()` to read the current application's configuration.
The application and configuration are stored in context vars which are set
using the `run()` or the `set_application()` functions.
Before, you setup the application configuration, you may want to register
default configuration by using `setup_configuration()`.

A simple application, should just call run to benefit from argument parsing,
configuration load and logging setup.

    if __name__ == '__main__':
        alphaconf.cli.run(main)

"""

SECRET_MASKS: MutableSequence[Callable] = [
    # mask if contains a kind of secret and it's not in a file
    re.compile(
        r'.*(key|password|secret)s?(?!_file)(?!_path)(_|$)|^(authentication|private)(_key|$)'
    ).match,
]
"""A list of functions which given a key indicate whether it's a secret"""

T = TypeVar('T')

#######################################
# APPLICATION CONTEXT
# ContextVar are no more used because some executions frameworks reset
# the context.

_global_configuration: Configuration = Configuration()
"""The global configuration"""

setup_configuration = _global_configuration.setup_configuration
get = _global_configuration.get
__initialized = False


def load_configuration_file(path: str):
    """Read a configuration file and add it to the context configuration"""
    config = read_configuration_file(path)
    logging.debug('Loading configuration from path: %s', path)
    setup_configuration(config)


def select_configuration(name, key):
    pass  # TODO


def initialize(
    app_name: str = '',
    setup_logging: bool = True,
    load_dotenv: Optional[bool] = None,
    force: bool = False,
):
    """Initialize the application and setup configuration"""
    global __initialized
    if __initialized and not force:
        logging.info("The application is already initialized", stack_info=True)
        return
    __initialized = True

    # load from dotenv
    from .internal.dotenv_vars import try_dotenv

    try_dotenv(load_dotenv=load_dotenv)

    # load the application
    from .internal import application as app

    configurations = app.get_configurations(
        app_name=app_name, default_configuration=_global_configuration.c
    )
    _global_configuration._merge(configurations)

    # setup logging
    if setup_logging:
        from . import get, logging_util

        logging_util.setup_application_logging(get('logging', default=None))
    logging.debug('Application initialized')


#######################################
# BASIC CONFIGURATION


def __alpha_configuration():
    """The default configuration for alphaconf"""
    logging_default = {
        'version': 1,
        'formatters': {
            'simple': {
                'format': '%(asctime)s %(levelname)s %(name)s: %(message)s',
                'datefmt': '%H:%M:%S',
            },
            'default': {
                'format': '%(asctime)s %(levelname)s'
                ' %(name)s [%(process)s,%(threadName)s]: %(message)s',
            },
            'color': {
                'class': 'alphaconf.logging_util.ColorFormatter',
                'format': '${..default.format}',
            },
            'json': {
                'class': 'alphaconf.logging_util.JSONFormatter',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'color',
                'stream': 'ext://sys.stdout',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        # change the default to keep module-level logging
        'disable_existing_loggers': False,
    }
    logging_none = {
        'version': 1,
        'formatters': {
            'default': {
                'format': '%(asctime)s %(levelname)s'
                ' %(name)s [%(process)s,%(threadName)s]: %(message)s',
            },
        },
        'handlers': {
            'null': {
                'class': 'logging.NullHandler',
            },
        },
        'root': {
            'handlers': ['null'],
            'level': 'INFO',
        },
    }
    conf = {
        'logging': '${oc.select:base.logging.default}',
        'base': {'logging': {'default': logging_default, 'none': logging_none}},
    }
    setup_configuration(conf)


# Initialize configuration
__alpha_configuration()
__all__ = ["get", "setup_configuration", "frozendict"]
