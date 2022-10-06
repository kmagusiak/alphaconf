import contextlib
import contextvars
import logging
import re
import sys
from contextvars import ContextVar
from typing import Any, Callable, Dict, Union, cast

from omegaconf import DictConfig, MissingMandatoryValue, OmegaConf

from .application import Application, _log
from .arg_parser import ArgumentError, ExitApplication
from .type_resolvers import convert_to_type

__doc__ = """AlphaConf

Based on omegaconf, provide a simple way to declare and run your application
while loading the configuration from various files and command line
arguments.

Use `alphaconf.get()` to read the current application's configuration.

    if __name__ == '__main__':
        alphaconf.run(main)

"""

"""A list of functions which given a key indicate whether it's a secret"""
SECRET_MASKS = [
    # mask if contains a kind of secret and it's not in a file
    re.compile(r'.*(key|password|secret)s?(?!_file)(_|$)').match,
]

#######################################
# APPLICATION CONTEXT

"""The application context"""
application: ContextVar[Application] = ContextVar('application')
"""The current configuration"""
configuration: ContextVar[DictConfig] = ContextVar('configuration', default=OmegaConf.create())
"""Additional helpers for the application"""
_helpers: ContextVar[Dict[str, str]] = ContextVar('configuration_helpers', default={})


def get(config_key: str, type=None, *, default=None) -> Any:
    """Select a configuration item from the current application"""
    conf = configuration.get()
    if config_key:
        c = OmegaConf.select(conf, config_key, throw_on_missing=True)
    else:
        c = conf
    if isinstance(c, DictConfig):
        c = OmegaConf.to_object(c)
    elif c is None:
        return default
    if type and c is not None:
        c = convert_to_type(c, type)
    return c


@contextlib.contextmanager
def set(**kw):
    """Update the configuration in a with block"""
    if not kw:
        yield
        return
    config = configuration.get()
    config = cast(DictConfig, OmegaConf.merge(config, kw))
    token = configuration.set(config)
    yield
    configuration.reset(token)


def set_application(app: Application, merge: bool = False):
    """Set the application and its configuration

    :param app: The application
    :param merge: Wether to merge the current configuration with the application (default false)
    """
    application.set(app)
    config = app.configuration
    if merge:
        config = cast(DictConfig, OmegaConf.merge(configuration.get(), config))
    configuration.set(config)


def run(main: Callable, arguments=True, *, should_exit=True, app: Application = None, **config):
    """Run this application

    :param main: The main function to call
    :param arguments: List of arguments (default: True to read sys.argv)
    :param should_exit: Whether an exception should sys.exit (default: True)
    :param config: Arguments passed to setup_configuration()
    :return: The result of main
    """
    if app is None:
        properties = {
            k: config.pop(k)
            for k in ['name', 'version', 'description', 'short_description']
            if k in config
        }
        app = Application(**properties)
    try:
        app.setup_configuration(arguments, **config)
    except MissingMandatoryValue as e:
        _log.error(e)
        if should_exit:
            sys.exit(99)
        raise
    except ArgumentError as e:
        _log.error(e)
        if should_exit:
            sys.exit(2)
        raise
    except ExitApplication:
        _log.debug('Normal application exit')
        if should_exit:
            sys.exit()
        return
    context = contextvars.copy_context()
    try:
        return context.run(__run_application, app=app, main=main, exc_info=should_exit)
    except Exception:
        if should_exit:
            _log.debug('Exit application')
            sys.exit(1)
        raise


def __run_application(app: Application, main: Callable, exc_info=True):
    """Set the application and execute main"""
    set_application(app)
    app_log = logging.getLogger()
    if get('testing', bool):
        app_log.info('Application testing (%s: %s)', app.name, main.__qualname__)
        return None
    # Run the application
    try:
        app_log.info('Application start (%s: %s)', app.name, main.__qualname__)
        result = main()
        if result is None:
            app_log.info('Application end.')
        else:
            app_log.info('Application end: %s', result)
        return result
    except Exception as e:
        # no need to log exc_info beacause the parent will handle it
        app_log.error('Application failed (%s) %s', type(e).__name__, e, exc_info=exc_info)
        raise


def setup_configuration(
    conf: Union[DictConfig, str, Dict],
    helpers: Dict[str, str] = {},
):
    """Add a default configuration

    :param conf: The configuration to add
    :param helpers: Description of parameters used in argument parser helpers
    """
    # merge the configurations
    if isinstance(conf, DictConfig):
        config = conf
    else:
        config = cast(DictConfig, OmegaConf.create(conf))
    configuration.set(cast(DictConfig, OmegaConf.merge(configuration.get(), config)))
    # setup helpers
    for h_key in helpers:
        key = h_key.split('.', 1)[0]
        if key not in config:
            raise ValueError('Invalid helper not in configuration [%s]' % key)
    _helpers.set({**_helpers.get(), **helpers})


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
        # change the default to keep module-level logging by default
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
        'handlers': {},
        'root': {
            'handlers': [],
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
