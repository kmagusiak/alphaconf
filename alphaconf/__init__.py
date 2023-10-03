import contextlib
import re
import warnings
from contextvars import ContextVar
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from omegaconf import Container, DictConfig, MissingMandatoryValue, OmegaConf

from .frozendict import frozendict  # noqa: F401 (expose)
from .internal import Application
from .internal.type_resolvers import convert_to_type

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

"""A list of functions which given a key indicate whether it's a secret"""
SECRET_MASKS = [
    # mask if contains a kind of secret and it's not in a file
    re.compile(r'.*(key|password|secret)s?(?!_file)(_|$)|^private(_key|$)').match,
]

#######################################
# APPLICATION CONTEXT

"""The current configuration"""
configuration: ContextVar[DictConfig] = ContextVar('configuration', default=OmegaConf.create())
"""Additional helpers for the application"""
_helpers: ContextVar[Dict[str, str]] = ContextVar('configuration_helpers', default={})

T = TypeVar('T')


@overload
def select(
    container: Any,
    key: str,
    type: Type[T],
    *,
    default: Optional[T] = None,
    required: Literal[True],
) -> T:
    ...


@overload
def select(
    container: Any,
    key: str,
    type: Type[T],
    *,
    default: Optional[T] = None,
    required: bool = False,
) -> Optional[T]:
    ...


@overload
def select(
    container: Any,
    key: str,
    type: Union[str, Type[T], None] = None,
    *,
    default: Any = None,
    required: bool = False,
) -> Any:
    ...


def select(container: Any, key: str, type=None, *, default=None, required: bool = False) -> Any:
    """Select a configuration item from the container

    :param container: The container to select from (Container, dict, etc.)
    :param key: The selection key
    :param type: The type of the object to return
    :param default: The default value is selected value is None
    :param required: Raise MissingMandatoryValue if the selected value and default are None
    :return: The selected value in the container
    """
    c: Any
    # make sure we have a container and select from it
    if isinstance(container, Container):
        c = container
    else:
        c = OmegaConf.create(container)
    c = OmegaConf.select(c, key, throw_on_missing=required)
    # handle empty result
    if c is None:
        if default is None and required:
            raise MissingMandatoryValue("Key not found: %s" % key)
        return default
    # check the returned type and convert when necessary
    if type is not None and isinstance(c, type):
        return c
    if isinstance(c, Container):
        c = OmegaConf.to_object(c)
    if type is not None:
        c = convert_to_type(c, type)
    return c


@overload
def get(
    config_key: str,
    type: Type[T],
    *,
    default: Optional[T] = None,
    required: Literal[True],
) -> T:
    ...


@overload
def get(
    config_key: str,
    type: Type[T],
    *,
    default: Optional[T] = None,
    required: bool = False,
) -> Optional[T]:
    ...


@overload
def get(
    config_key: str,
    type: Union[str, Type[T], None] = None,
    *,
    default: Any = None,
    required: bool = False,
) -> Any:
    ...


def get(config_key: str, type=None, *, default=None, required: bool = False) -> Any:
    """Select a configuration item from the current configuration"""
    return select(configuration.get(), config_key, type=type, default=default, required=required)


def set(**kw):
    """Update the configuration in a with block

    with alphaconf.set(a=value):
        assert alphaconf.get('a') == value
    """
    return with_config(OmegaConf.create(kw))


@contextlib.contextmanager
def with_config(config: DictConfig, merge: bool = True):
    """Set the application and its configuration

    :param app: The application
    :param merge: Wether to merge the current configuration with the application (default false)
    """
    if merge:
        # merging 2 DictConfig objects
        config = cast(DictConfig, OmegaConf.merge(configuration.get(), config))
    token = configuration.set(config)
    yield
    configuration.reset(token)


def set_application(app: Application, merge: bool = False):
    """Set the application and its configuration

    :param app: The application
    :param merge: Wether to merge the current configuration with the application (default false)
    """
    warnings.warn("use alphaconf.with_config(app.configuration)", DeprecationWarning)
    ctx = with_config(app.configuration, merge=merge)
    ctx.__enter__()  # just enter the context and never leave


def run(
    main: Callable[[], T],
    arguments: Union[bool, List[str]] = True,
    *,
    should_exit: bool = True,
    app: Optional[Application] = None,
    **config,
) -> Optional[T]:
    """Run this application

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


def setup_configuration(
    conf: Union[DictConfig, str, Dict],
    helpers: Dict[str, str] = {},
):
    """Add a default configuration

    :param conf: The configuration to merge into the global configuration
    :param helpers: Description of parameters used in argument parser helpers
    """
    # TODO deprecate
    # merge the configurations
    if isinstance(conf, DictConfig):
        config = conf
    else:
        # TODO support a.b: v in dicts?
        created_config = OmegaConf.create(conf)
        if not (created_config and isinstance(created_config, DictConfig)):
            raise ValueError('Expecting a non-empty dict configuration')
        config = created_config
    # merging 2 DictConfig
    config = cast(DictConfig, OmegaConf.merge(configuration.get(), config))
    configuration.set(config)
    # setup helpers
    for h_key in helpers:
        key = h_key.split('.', 1)[0]
        if not config or key not in config:
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
