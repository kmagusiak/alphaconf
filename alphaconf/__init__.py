import re
import warnings
from typing import Callable, Optional, Sequence, TypeVar, Union

from .frozendict import frozendict  # noqa: F401 (expose)
from .internal.application import Application
from .internal.configuration import Configuration

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

SECRET_MASKS = [
    # mask if contains a kind of secret and it's not in a file
    re.compile(r'.*(key|password|secret)s?(?!_file)(_|$)|^private(_key|$)').match,
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

_application: Optional[Application] = None
get = _global_configuration.get


def set_application(app: Application) -> None:
    """Setup the application globally

    This loads the configuration and initializes the application.
    The function may raise ExitApplication.

    :param arguments: The argument list to parse (default: True to parse sys.argv)
    :param load_dotenv: Whether to load dotenv environment (default: yes if installed)
    :param env_prefixes: The env prefixes to load the configuration values from (default: auto)
    :param resolve_configuration: Test whether the configuration can be resolved (default: True)
    :param setup_logging: Whether to setup logging (default: True)
    """
    global _application, get
    if _application is app:
        return
    if _application is not None:
        _application.log.info("Another application will be loaded")
    _application = app
    get = app.configuration.get


def run(
    main: Callable[[], T],
    arguments: Union[bool, Sequence[str]] = True,
    *,
    should_exit: bool = True,
    app: Optional[Application] = None,
    **config,
) -> Optional[T]:
    """Run this application (deprecated)

    If an application is not given, a new one will be created with configuration properties
    taken from the config. Also, by default logging is set up.

    :param main: The main function to call
    :param arguments: List of arguments (default: True to read sys.argv)
    :param should_exit: Whether an exception should sys.exit (default: True)
    :param config: Arguments passed to Application.__init__() and Application.setup_configuration()
    :return: The result of main
    """
    warnings.warn("use alphaconf.cli.run directly", DeprecationWarning)
    from .cli import run

    return run(main, arguments, should_exit=should_exit, app=app, **config)


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
__all__ = ["get", "setup_configuration", "set_application", "Application", "frozendict"]
