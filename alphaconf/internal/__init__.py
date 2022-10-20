import logging
import os
import sys
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union, cast

from omegaconf import DictConfig, OmegaConf

from . import arg_parser, load_file

__doc__ = """Representation of an application with its configuration."""

application_log = logging.getLogger(__name__)


class Application:
    """An application description

    :param properties: Properties of the application, such as:
        name, version, short_description, description, etc.
    """

    __config: Optional[DictConfig]
    __name: str
    version: Optional[str]
    description: Optional[str]
    short_description: Optional[str]
    parsed: Optional[arg_parser.ParseResult]
    argument_parser: arg_parser.ArgumentParser

    def __init__(
        self, *, name=None, version=None, description=None, short_description=None
    ) -> None:
        """Initialize the application.

        Properties:
        - name: the name of the application (always updated)
        - version: version number
        - description: description shown in help
        - short_description: shorter description

        :param properties: Properties for the app
        """
        self.__config = None  # initialize
        self.__name = name or self.__get_default_name()
        self.version = version
        self.description = description
        self.short_description = short_description
        # Add argument parser
        self.__initialize_parser()

    def __initialize_parser(self):
        from .. import _helpers

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
                    'version': self.version or '',
                    'uuid': str(uuid.uuid4()),
                },
            }
        )

    @property
    def name(self) -> str:
        """Get the name of the application"""
        return self.__name

    @property
    def configuration(self) -> DictConfig:
        """Get the configuration of the application, initialize if necessary"""
        if self.__config is None:
            self.setup_configuration(
                arguments=False, resolve_configuration=False, setup_logging=False
            )
            application_log.info('alphaconf initialized')
            assert self.__config is not None
        return self.__config

    def _get_possible_configuration_paths(self, additional_paths: List[str] = []) -> Iterable[str]:
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
        yield from additional_paths

    def _load_dotenv(self, load_dotenv: Optional[bool] = None):
        """Load dotenv variables (optionally)"""
        if load_dotenv is False:
            return
        try:
            import dotenv

            path = dotenv.find_dotenv(usecwd=True)
            application_log.debug('Loading dotenv: %s', path or '(none)')
            dotenv.load_dotenv(path)
        except ModuleNotFoundError:
            if load_dotenv:
                raise
            application_log.debug('dotenv is not installed')

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
        configuration_paths: List[str] = [],
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
        from .. import configuration as ctx_configuration

        application_log.debug('Loading default and app configurations')
        default_configuration = ctx_configuration.get()
        yield default_configuration
        yield self._app_configuration()
        # Read files
        for path in self._get_possible_configuration_paths(configuration_paths):
            if not (path in configuration_paths or os.path.isfile(path)):
                continue
            application_log.debug('Load configuration from %s', path)
            yield load_file.read_configuration_file(path)
        # Environment
        prefixes: Optional[Tuple[str, ...]]
        if env_prefixes is True:
            application_log.debug('Detecting accepted env prefixes')
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
            application_log.debug('Loading env configuration from prefixes %s' % (prefixes,))
            yield self.__load_environ(prefixes)

    def setup_configuration(
        self,
        arguments: Union[bool, List[str]] = True,
        *,
        load_dotenv: Optional[bool] = None,
        env_prefixes: Union[bool, Iterable[str]] = True,
        configuration_paths: List[str] = [],
        resolve_configuration: bool = True,
        setup_logging: bool = False,
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
        application_log.debug('Start setup application')

        # Parse arguments
        if arguments is True:
            arguments = sys.argv[1:]
        if not isinstance(arguments, list):
            arguments = []
        self.parsed = self.argument_parser.parse_args(arguments)

        # Load and merge configurations
        self._load_dotenv(load_dotenv=load_dotenv)
        configurations = list(
            self._get_configurations(
                env_prefixes=env_prefixes,
                configuration_paths=configuration_paths,
            )
        )
        if self.parsed:
            configurations.extend(self.parsed.configurations())
        self.__config = cast(DictConfig, OmegaConf.merge(*configurations))
        application_log.debug('Merged %d configurations', len(configurations))

        # Handle the result
        self._handle_parsed_result()

        # Try to get the whole configuration to resolve links
        if resolve_configuration:
            OmegaConf.resolve(self.__config)

        # Logging
        if setup_logging:
            application_log.debug('Setup logging')
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

        from .. import logging_util

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
        mask_keys: List[str] = ['application.uuid'],
    ) -> dict:
        """Get the configuration as dict with masked items

        :param mask_base: Whether to mask "base" entry
        :param mask_secrets: Whether to mask secret keys
        :param mask_keys: Which keys to mask
        :return: Configuration copy with masked values
        """
        from .. import SECRET_MASKS

        config = cast(dict, OmegaConf.to_container(self.configuration))
        if mask_secrets:
            config = Application.__mask_config(
                config,
                lambda p: any(mask(p) for mask in SECRET_MASKS),
                lambda v: v if v is None or v == '???' else '*****',
            )
        if mask_base and 'base' not in mask_keys:
            # first remove all values if the object is not resolved
            config['base'] = Application.__mask_config(
                config['base'],
                lambda p: not isinstance(
                    OmegaConf.select(self.configuration, p, throw_on_resolution_failure=False),
                    DictConfig,
                ),
                lambda v: {},
            )
            # then collapse dict[str,None] into a list[str]
            config['base'] = Application.__mask_config(
                config['base'],
                lambda _: True,
                lambda v: list(v) if isinstance(v, dict) and not any(v.values()) else v,
            )
        if mask_keys:
            config = Application.__mask_config(config, lambda p: p in mask_keys, lambda _: None)
        return config

    @staticmethod
    def __mask_config(obj, check, replace, path=''):
        """Alter the configuration dict

        :param config: The value to mask
        :param check: Function to check if we replace the value (path: str) -> bool
        :param replace: Function doing the replacement of the value (v) -> Any
        :param key: Current path
        :return: The modified config
        """
        if check(path):
            obj = replace(obj)
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                new = Application.__mask_config(
                    value, check, replace, f"{path}.{key}" if path else key
                )
                if new is not None:
                    result[key] = new
            obj = result
        elif isinstance(obj, list):
            obj = [
                Application.__mask_config(v, check, replace, f"{path}[{i}]")
                for i, v in enumerate(obj)
            ]
        return obj

    def print_help(self, *, usage=None, description=None, arguments=True):
        """Print the help message
        Set the arguments to False to disable printing them."""
        if usage is None:
            usage = f"usage: {self.name or 'app'}"
            usage += " [arguments] [key=value ...]"
        if isinstance(usage, str):
            print(usage)
        if description is None:
            description = self.description
        if isinstance(description, str):
            print()
            print(description)
        if arguments:
            print()
            self.argument_parser.print_help()

    def __str__(self) -> str:
        ready = self.__config is not None
        return f"{type(self).__name__}({self.name}; loaded={ready})"
