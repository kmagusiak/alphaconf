import contextlib
import contextvars
import logging
import os
import re
import sys
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union, cast

from omegaconf import DictConfig, MissingMandatoryValue, OmegaConf

from . import arg_parser

__doc__ = """AlphaConf

Based on omegaconf, provide a simple way to declare and run your application
while loading the configuration from various files and command line
arguments.

Use `alphaconf.get()` or `alphaconf.configuration()` to read
the current application's configuration.

    if __name__ == '__main__':
        alphaconf.Application().run(main)

"""

_log = logging.getLogger(__name__)

"""A list of functions which given a key indicate whether it's a secret"""
SECRET_MASKS = [
    # mask if contains a kind of secret and it's not in a file
    re.compile(r'.*(password|secret|key)(?!_file)(_|$)').match,
]

"""Map of default values"""
_DEFAULTS: Dict[str, Any] = {
    'configurations': [],
    'helpers': {},
    'testing_configurations': [],
}

#######################################
# APPLICATION


class Application:
    """An application configuration description

    :param properties: Properties of the application, such as:
        name, version, short_description, description, etc.
    """

    __config: Optional[DictConfig]

    def __init__(self, **properties) -> None:
        """Initialize the application.

        Properties:
        - name: the name of the application (always updated)
        - version: version number
        - description: description shown in help
        - short_description: shorter description

        :param properties: Properties for the app
        """
        self.__config = None  # initialize
        if not properties.get('name'):
            properties['name'] = self.__get_default_name()
        self.properties = properties
        # Add argument parser
        self.__initialize_parser()

    def __initialize_parser(self):
        self.parsed = None
        self.argument_parser = arg_parser.ArgumentParser()
        parser = self.argument_parser
        arg_parser.configure_parser(parser, app=self)
        parser.help_messages.update(_DEFAULTS['helpers'])

    @staticmethod
    def __get_default_name() -> str:
        """Find the default name from sys.argv"""
        name = os.path.basename(sys.argv[0])
        if name.endswith('.py'):
            name = name[:-3]
        if name == '__main__':
            # executing a module using python -m
            name = os.path.basename(os.path.dirname(sys.argv[0]))
        return name

    def _app_configuration(self) -> DictConfig:
        """Get the application configuration key"""
        return OmegaConf.create(
            {
                'application': {
                    'name': self.name,
                    'version': self.properties.get('version'),
                    'uuid': str(uuid.uuid4()),
                },
            }
        )

    @property
    def name(self):
        """Get the name of the application"""
        return self.properties['name']

    @property
    def configuration(self) -> DictConfig:
        """Get the configuration of the application, initialize if necessary"""
        if self.__config is None:
            self.setup_configuration(
                arguments=False, resolve_configuration=False, setup_logging=False
            )
            _log.info('alphaconf initialized')
            assert self.__config is not None
        return self.__config

    def get_config(self, key: str = "", type=None) -> Any:
        """Get a configuration value by key

        The value is resolved and a missing exception may be thrown for mandatory arguments.

        :param key: Optional selection key for the configuration
        :param type: Optional type to convert to
        :return: The value or None
        """
        if key:
            c = OmegaConf.select(self.configuration, key, throw_on_missing=True)
        else:
            c = self.configuration
        if isinstance(c, DictConfig):
            c = OmegaConf.to_object(c)
        if type and c is not None:
            from . import arg_type

            c = arg_type.convert_to_type(c, type)
        return c

    def _get_possible_configuration_paths(self) -> Iterable[str]:
        """List of paths where to find configuration files"""
        name = self.name
        is_windows = sys.platform.startswith('win')
        for path in [
            '$APPDATA/{}.yaml' if is_windows else '/etc/{}.yaml',
            '$LOCALAPPDATA/{}.yaml' if is_windows else '',
            '$HOME/.{}.yaml',
            '$HOME/.config/{}.yaml',
            '$PWD/{}.yaml',
        ]:
            path = os.path.expandvars(path.format(name))
            if path and '$' not in path:
                yield path

    def _load_dotenv(self, load_dotenv: Optional[bool] = None):
        """Load dotenv variables (optionally)"""
        if load_dotenv is False:
            return
        try:
            import dotenv

            _log.debug('Loading dotenv')
            dotenv.load_dotenv()
        except ModuleNotFoundError:
            if load_dotenv:
                raise
            _log.debug('dotenv is not installed')

    def __load_environ(self, prefixes: Iterable[str]) -> DictConfig:
        """Load environment variables into a dict configuration"""
        from yaml.error import YAMLError  # type: ignore

        trans = str.maketrans('_', '.', '"\\=')
        dotlist = [
            (name.lower().translate(trans), value)
            for name, value in os.environ.items()
            if name.startswith(tuple(prefixes))
        ]
        conf = OmegaConf.create({})
        for name, value in dotlist:
            try:
                conf.merge_with_dotlist(["%s=%s" % (name, value)])
            except YAMLError:
                # if cannot load the value as a dotlist, just add the string
                OmegaConf.update(conf, name, value)
        return conf

    def _get_configurations(
        self,
        env_prefixes: Union[bool, Iterable[str]] = True,
    ) -> Iterable[DictConfig]:
        """List of all configurations that can be loaded automatically

        - All of the default configurations
        - The app configuration
        - Reads existing files from possible configuration paths
        - Reads environment variables based on given prefixes

        :param env_prefixes: Prefixes of environment variables to load
        :return: OmegaConf configurations (to be merged)
        """
        _log.debug('Loading default and app configurations')
        yield from _DEFAULTS['configurations']
        yield from _DEFAULTS['testing_configurations']
        yield self._app_configuration()
        # Read files
        for path in self._get_possible_configuration_paths():
            if os.path.exists(path):
                _log.debug('Load configuration from %s', path)
                conf = OmegaConf.load(path)
                if isinstance(conf, DictConfig):
                    yield conf
                else:
                    yield from conf
        # Environment
        prefixes: Optional[Tuple[str, ...]]
        if env_prefixes is True:
            _log.debug('Detecting accepted env prefixes')
            default_keys = {k for cfg in _DEFAULTS['configurations'] for k in cfg.keys()}
            prefixes = tuple(
                k.upper() + '_'
                for k in default_keys
                if k not in ('base', 'python') and not k.startswith('_')
            )
        elif isinstance(env_prefixes, Iterable):
            prefixes = tuple(env_prefixes)
        else:
            prefixes = None
        if prefixes:
            _log.debug('Loading env configuration from prefixes %s' % (prefixes,))
            yield self.__load_environ(prefixes)

    def setup_configuration(
        self,
        arguments: Union[bool, List[str]] = True,
        *,
        load_dotenv: Optional[bool] = None,
        env_prefixes: Union[bool, Iterable[str]] = True,
        resolve_configuration: bool = True,
        setup_logging: bool = True,
    ) -> None:
        """Setup the application configuration

        Can be called only once to setup the configuration and initialize the application.
        The function may raise ExitApplication.

        :param arguments: The argument list to parse (default: True to parse sys.argv)
        :param load_dotenv: Whether to load dotenv environment (default: yes if installed)
        :param env_prefixes: The env prefixes to load the configuration values from (default: auto)
        :param resolve_configuration: Test whether the configuration can be resolved (default: True)
        :param setup_logging: Whether to setup logging (default: True)
        """
        if self.__config is not None:
            raise RuntimeError('Configuration already set')
        _log.debug('Start setup application')

        # Parse arguments
        if arguments is True:
            arguments = sys.argv[1:]
        if not isinstance(arguments, list):
            arguments = []
        self.parsed = self.argument_parser.parse_args(arguments)

        # Load and merge configurations
        self._load_dotenv(load_dotenv=load_dotenv)
        configurations = list(self._get_configurations(env_prefixes=env_prefixes))
        if self.parsed:
            configurations.extend(self.parsed.configurations())
        self.__config = cast(DictConfig, OmegaConf.merge(*configurations))
        _log.debug('Merged %d configurations', len(configurations))

        # Handle the result
        self._handle_result()

        # Try to get the whole configuration to resolve links
        if resolve_configuration:
            self.get_config()

        # Logging
        if setup_logging:
            _log.debug('Setup logging')
            self._setup_logging()

    def _handle_result(self):
        """Handle result that is in self.parsed"""
        if self.parsed.result:
            return self.parsed.result.run(self)
        if self.parsed.rest:
            raise arg_parser.ArgumentError(f"Too many arguments {self.parsed.rest}")
        return None

    def _setup_logging(self) -> None:
        """Setup logging

        Set the time to GMT, log key 'logging' from configuration or if none, base logging.
        """
        import logging

        from . import logging_util

        logging_util.set_gmt()
        log = logging.getLogger()
        logging_config = self.get_config('logging')
        if logging_config:
            # Configure using the st configuration
            import logging.config

            logging.config.dictConfig(logging_config)
        elif len(log.handlers) == 0:
            # Default logging if not yet initialized
            output = logging.StreamHandler()
            output.setFormatter(logging_util.ColorFormatter())
            log.addHandler(output)
            log.setLevel(logging.INFO)

    @contextlib.contextmanager
    def update_configuration(self, conf: Union[DictConfig, Dict]):
        """Returns a context where the application configuration is merged
        with a given configuration.

        :param conf: The configuraiton
        """
        current_config = self.configuration
        try:
            self.__config = cast(DictConfig, OmegaConf.merge(current_config, conf))
            yield self
        finally:
            self.__config = current_config

    def yaml_configuration(self, mask_base: bool = True, mask_secrets: bool = True) -> str:
        """Get the configuration as yaml string

        :param mask_base: Whether to mask "base" entry
        :return: Configuration as string (yaml)
        """
        configuration = self.configuration
        if mask_base or mask_secrets:
            configuration = configuration.copy()
        if mask_secrets:
            configuration = Application.__mask_secrets(configuration)
        if mask_base:
            configuration['base'] = {
                key: list(choices.keys()) for key, choices in configuration.base.items()
            }
        return OmegaConf.to_yaml(configuration)

    @staticmethod
    def __mask_secrets(configuration):
        for key in list(configuration):
            if isinstance(key, str) and any(mask(key) for mask in SECRET_MASKS):
                configuration[key] = '*****'
            elif isinstance(configuration[key], (Dict, DictConfig)):
                configuration[key] = Application.__mask_secrets(configuration[key])
        return configuration

    def print_help(self, *, usage=None, description=None, arguments=True):
        """Print the help message
        Set the arguments to False to disable printing them."""
        p = self.properties
        if usage is None:
            usage = f"usage: {p.get('name') or 'app'}"
            usage += " [arguments] [key=value ...]"
        if isinstance(usage, str):
            print(usage)
        if description is None:
            description = p.get('description')
        if isinstance(description, str):
            print()
            print(description)
        if arguments:
            print()
            self.argument_parser.print_help()

    def run(self, main, arguments=True, *, should_exit=True, **configuration):
        """Run this application

        :param main: The main function to call
        :param arguments: List of arguments (default: True to read sys.argv)
        :param should_exit: Whether an exception should sys.exit (default: True)
        :param configuration: Arguments passed to setup_configuration()
        :return: The result of main
        """
        try:
            self.setup_configuration(arguments, **configuration)
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
        log = logging.getLogger()
        if _DEFAULTS['testing_configurations']:
            log.info('Application testing (%s: %s)', self.name, main.__qualname__)
            return None
        # Run the application
        token = application.set(self)
        try:
            log.info('Application start (%s: %s)', self.name, main.__qualname__)
            result = main()
            if result is None:
                log.info('Application end.')
            else:
                log.info('Application end: %s', result)
            return result
        except Exception as e:
            # no need to log exc_info beacause the parent will handle it
            log.error('Application failed (%s) %s', type(e).__name__, e, exc_info=should_exit)
            if should_exit:
                log.debug('Exit application')
                sys.exit(1)
            raise
        finally:
            application.reset(token)

    def __str__(self) -> str:
        running = self == application.get()
        ready = self.__config is not None
        return f"{type(self).__name__}({self.name}; loaded={ready}; running={running})"


#######################################
# APPLICATION CONTEXT


"""The application context"""
application: contextvars.ContextVar[Application] = contextvars.ContextVar('application')


def configuration() -> DictConfig:
    """Get the configuration for the current application"""
    app = application.get()
    return app.configuration


def get(config_key: str, type=None) -> Any:
    """Select a configuration from the current application"""
    app = application.get()
    return app.get_config(config_key, type=type)


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
    if testing is False:
        _DEFAULTS['testing_configurations'].clear()
    config_key = 'testing_configurations' if testing else 'configurations'
    _DEFAULTS[config_key].append(config)
    # setup helpers
    for h_key in helpers:
        key = h_key.split('.', 1)[0]
        if key not in config:
            raise ValueError('Invalid helper not in configuration [%s]' % key)
    _DEFAULTS['helpers'].update(helpers)


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
