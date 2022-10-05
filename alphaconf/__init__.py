import contextlib
import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional, Union, cast

from omegaconf import MissingMandatoryValue  # XXX still needed?
from omegaconf import DictConfig, OmegaConf

from . import application as _app
from .application import Application, arg_parser  # noqa: F401

__doc__ = """AlphaConf

Based on omegaconf, provide a simple way to declare and run your application
while loading the configuration from various files and command line
arguments.

Use `alphaconf.get()` or `alphaconf.configuration()` to read
the current application's configuration.

    if __name__ == '__main__':
        alphaconf.Application().run(main)

"""

#######################################
# APPLICATION CONTEXT


"""The application context"""
application: ContextVar[_app.Application] = ContextVar('application')
configuration: ContextVar[DictConfig] = ContextVar('configuration', default=OmegaConf.create())


def get(config_key: str, type=None) -> Any:
    """Select a configuration from the current application"""
    app = application.get()
    return app.get_config(config_key, type=type)


@contextlib.contextmanager
def set(**kw):
    """Update the configuration in a with block"""
    if not kw:
        return
    config = configuration.get()
    config = cast(DictConfig, OmegaConf.merge(config, kw))
    token = configuration.set(config)
    yield
    configuration.reset(token)


def run(main, arguments=True, *, should_exit=True, app: _app.Application = None, **config):
    """Run this application

    :param main: The main function to call
    :param arguments: List of arguments (default: True to read sys.argv)
    :param should_exit: Whether an exception should sys.exit (default: True)
    :param config: Arguments passed to setup_configuration()
    :return: The result of main
    """
    if app is None:
        app = _app.Application()
    _log = _app._log
    try:
        app.setup_configuration(arguments, **config)
    except MissingMandatoryValue as e:
        _log.error(e)
        if should_exit:
            sys.exit(99)
        raise
    except arg_parser.ArgumentError as e:
        _log.error(e)
        if should_exit:
            sys.exit(2)
        raise
    except arg_parser.ExitApplication:
        _log.debug('Normal application exit')
        if should_exit:
            sys.exit()
        return
    app_log = logging.getLogger()
    if _app._DEFAULTS['testing_configurations']:
        app_log.info('Application testing (%s: %s)', app.name, main.__qualname__)
        return None
    # Run the application
    token = application.set(app)
    toekn_c = configuration.set(app.configuration)
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
        app_log.error('Application failed (%s) %s', type(e).__name__, e, exc_info=should_exit)
        if should_exit:
            app_log.debug('Exit application')
            sys.exit(1)
        raise
    finally:
        configuration.reset(toekn_c)
        application.reset(token)


def setup_configuration(
    conf: Union[DictConfig, str, Dict],
    helpers: Dict[str, str] = {},
    testing: Optional[bool] = None,
):
    """Add a default configuration

    :param conf: The configuration to add
    :param helpers: Description of parameters used in argument parser helpers
    :param testing: If set, True adds the configuration to testing configurations,
                    if False, the testing configurations are cleared
    """
    if isinstance(conf, DictConfig):
        config = conf
    else:
        config = cast(DictConfig, OmegaConf.create(conf))
    defaults = _app._DEFAULTS  # XXX move
    if testing is False:
        defaults['testing_configurations'].clear()
    config_key = 'testing_configurations' if testing else 'configurations'
    defaults[config_key].append(config)
    # setup helpers
    for h_key in helpers:
        key = h_key.split('.', 1)[0]
        if key not in config:
            raise ValueError('Invalid helper not in configuration [%s]' % key)
    defaults['helpers'].update(helpers)


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
