import logging
import os
import sys
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union, cast

from omegaconf import DictConfig, OmegaConf

from . import arg_parser, load_file

__doc__ = """Application

Representation of an application with its configuration.
"""

_log = logging.getLogger(__name__)


class Application:
    """An application description

    :param properties: Properties of the application, such as:
        name, version, short_description, description, etc.
    """

    __config: Optional[DictConfig]
    properties: Dict[str, str]
    parsed: Optional[arg_parser.ParseResult]
    argument_parser: arg_parser.ArgumentParser

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
        from . import _helpers

        self.parsed = None
        self.argument_parser = parser = arg_parser.ArgumentParser()
        arg_parser.configure_parser(parser, app=self)
        parser.help_messages.update(_helpers.get())

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

    def _get_possible_configuration_paths(self) -> Iterable[str]:
        """List of paths where to find configuration files"""
        name = self.name
        is_windows = sys.platform.startswith('win')
        for path in [
            '$APPDATA/{}' if is_windows else '/etc/{}',
            '$LOCALAPPDATA/{}' if is_windows else '',
            '$HOME/.{}',
            '$HOME/.config/{}',
            '$PWD/{}',
        ]:
            path = os.path.expandvars(path)
            if path and '$' not in path:
                for ext in load_file.SUPPORTED_EXTENSIONS:
                    yield path.format(name + '.' + ext)

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
        prefixes = tuple(prefixes)
        dotlist = [
            (name.lower().translate(trans), value)
            for name, value in os.environ.items()
            if name.startswith(prefixes)
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
        from . import configuration as ctx_configuration

        _log.debug('Loading default and app configurations')
        default_configuration = ctx_configuration.get()
        yield default_configuration
        yield self._app_configuration()
        # Read files
        for path in self._get_possible_configuration_paths():
            if os.path.isfile(path):
                _log.debug('Load configuration from %s', path)
                conf = load_file.read_configuration_file(path)
                if isinstance(conf, DictConfig):
                    yield conf
                else:
                    yield from conf
        # Environment
        prefixes: Optional[Tuple[str, ...]]
        if env_prefixes is True:
            _log.debug('Detecting accepted env prefixes')
            default_keys = {str(k) for k in default_configuration.keys()}
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
        self._handle_parsed_result()

        # Try to get the whole configuration to resolve links
        if resolve_configuration:
            OmegaConf.resolve(self.__config)

        # Logging
        if setup_logging:
            _log.debug('Setup logging')
            self._setup_logging()

    def _handle_parsed_result(self):
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
        logging_config = cast(Dict[str, Any], OmegaConf.to_object(self.configuration.logging))
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

    def masked_configuration(
        self,
        *,
        mask_base: bool = True,
        mask_secrets: bool = True,
        mask_keys: List[str] = [],
    ) -> DictConfig:
        """Get the configuration as yaml string

        :param mask_base: Whether to mask "base" entry
        :param mask_secrets: Whether to mask secret keys
        :param mask_keys: Which keys to mask
        :return: Configuration copy with masked values
        """
        config = self.configuration.copy()
        if mask_secrets:
            config = Application.__mask_secrets(config)
        if mask_base:
            config['base'] = {key: list(choices.keys()) for key, choices in config.base.items()}
        if mask_keys:
            config = OmegaConf.masked_copy(
                config, [k for k in config.keys() if k not in mask_keys and isinstance(k, str)]
            )
        return config

    @staticmethod
    def __mask_secrets(configuration):
        from . import SECRET_MASKS

        for key in list(configuration):
            if isinstance(key, str) and any(mask(key) for mask in SECRET_MASKS):
                configuration[key] = '*****'
            elif isinstance(configuration[key], (Dict, DictConfig, dict)):
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

    def __str__(self) -> str:
        ready = self.__config is not None
        return f"{type(self).__name__}({self.name}; loaded={ready})"
