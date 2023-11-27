import itertools
import logging
import os
import sys
import uuid
from typing import Callable, Iterable, List, MutableMapping, Optional, Tuple, Union, cast

from omegaconf import DictConfig, OmegaConf

from . import arg_parser, load_file
from .configuration import Configuration


class Application:
    """An application description"""

    log = logging.getLogger('alphaconf')
    __config: Optional[Configuration] = None
    __name: str
    properties: MutableMapping[str, str]
    argument_parser: arg_parser.ArgumentParser
    parsed: Optional[arg_parser.ParseResult] = None

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        **properties,
    ) -> None:
        """Initialize the application.

        Properties:
        - name: the name of the application (always updated)
        - version
        - description
        - ...
        """
        self.__config = None  # initialize
        self.__name = name or self.__get_default_name()
        self.properties = properties
        self.argument_parser = self._build_argument_parser()

    def _build_argument_parser(self) -> arg_parser.ArgumentParser:
        from .. import _global_configuration

        p = arg_parser.ArgumentParser(_global_configuration.helpers)
        arg_parser.configure_parser(p, app=self)
        return p

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
                    'version': self.properties.get('version') or '',
                    'uuid': str(uuid.uuid4()),
                },
            }
        )

    @property
    def name(self) -> str:
        """Get the name of the application"""
        return self.__name

    @property
    def configuration(self) -> Configuration:
        """Get the configuration of the application, initialize if necessary"""
        if self.__config is None:
            self.setup_configuration()
            self.log.info('alphaconf initialized')
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
            path = path and os.path.expandvars(path)
            if path and '$' not in path:
                for ext in load_file.SUPPORTED_EXTENSIONS:
                    yield path.format(f"{name}.{ext}")

    def _get_configurations(
        self,
        configuration_paths: Iterable[str] = [],
        env_prefixes: Union[bool, Iterable[str]] = True,
    ) -> Iterable[DictConfig]:
        """List of all configurations that can be loaded automatically

        - Global configuration
        - The app configuration
        - Read file defined in PYTHON_ALPHACONF
        - Reads existing files from possible configuration paths
        - Reads environment variables based on given prefixes

        :param env_prefixes: Prefixes of environment variables to load
        :return: OmegaConf configurations (to be merged)
        """
        self.log.debug('Loading default and app configurations')
        assert self.__config is not None
        default_configuration = self.__config.c
        yield default_configuration
        yield self._app_configuration()
        # Read files
        env_configuration_path = os.environ.get('PYTHON_ALPHACONF') or ''
        for path in itertools.chain(
            [env_configuration_path],
            self._get_possible_configuration_paths(),
            configuration_paths,
        ):
            if not os.path.isfile(path):
                continue
            self.log.debug('Load configuration from %s', path)
            yield load_file.read_configuration_file(path)
        # Environment
        prefixes: Optional[Tuple[str, ...]]
        if env_prefixes is True:
            self.log.debug('Detecting accepted env prefixes')
            default_keys = {str(k) for k in default_configuration}
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
            self.log.debug('Loading env configuration from prefixes %s', prefixes)
            yield self.__config.from_environ(prefixes)
        if self.parsed:
            yield from self.parsed.configurations()

    def setup_configuration(
        self,
        *,
        arguments: List[str] = [],
        configuration_paths: Iterable[str] = [],
        load_dotenv: Optional[bool] = None,
        env_prefixes: Union[bool, Iterable[str]] = True,
        resolve_configuration: bool = True,
    ):
        from .. import _global_configuration as ctx_configuration
        from .dotenv_vars import try_dotenv

        try_dotenv(load_dotenv=load_dotenv)

        self.log.debug('Parse arguments')
        self.parsed = self.argument_parser.parse_args(arguments)

        self.log.debug('Start setup configuration')
        self.__config = Configuration(parent=ctx_configuration)
        self.__config._merge(
            self._get_configurations(
                configuration_paths=configuration_paths, env_prefixes=env_prefixes
            )
        )
        self.log.debug('Merged configurations')

        # Handle the result
        self._handle_parsed_result()

        # Try to get the whole configuration to resolve links
        if resolve_configuration:
            OmegaConf.resolve(self.__config.c)

    def _handle_parsed_result(self):
        """Handle result that is in self.parsed"""
        if self.parsed.result:
            return self.parsed.result.run(self)
        if self.parsed.rest:
            raise arg_parser.ArgumentError(f"Too many arguments {self.parsed.rest}")
        return None

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

        config = cast(dict, OmegaConf.to_container(self.configuration.c))
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
                    OmegaConf.select(self.configuration.c, p, throw_on_resolution_failure=False),
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
    def __mask_config(obj, check: Callable[[str], bool], replace: Callable, path: str = ''):
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

    def print_help(self, *, arguments: bool = True):
        """Print the help message
        Set the arguments to False to disable printing them."""
        prop = self.properties
        if usage := prop.get('usage'):
            print(usage)
        else:
            usage = f"usage: {self.name or 'app'}"
            usage += " [arguments] [key=value ...]"
            print(usage)
        if description := (prop.get('description') or prop.get('short_description')):
            print()
            print(description)
        if arguments:
            print()
            self.argument_parser.print_help()

    def __str__(self) -> str:
        ready = self.__config is not None
        return f"{type(self).__name__}({self.name}; loaded={ready})"
