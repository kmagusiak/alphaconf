import copy
import os
from enum import Enum
from typing import (
    Any,
    Dict,
    Iterable,
    MutableMapping,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from omegaconf import Container, DictConfig, OmegaConf

from .type_resolvers import convert_to_type

T = TypeVar('T')


class RaiseOnMissingType(Enum):
    RAISE = 'raise'


raise_on_missing = RaiseOnMissingType.RAISE
_cla_type = type


class Configuration:
    c: DictConfig
    __type_path: MutableMapping[Type, str]
    __type_value: MutableMapping[Type, Any]
    helpers: Dict[str, str]

    def __init__(self, *, parent: Optional["Configuration"] = None) -> None:
        if parent:
            self.c = OmegaConf.create(parent.c)
            self.helpers = copy.copy(parent.helpers)
            self.__type_path = copy.copy(parent.__type_path)
        else:
            self.c = OmegaConf.create({})
            self.helpers = {}
            self.__type_path = {}
        self.__type_value = {}

    @overload
    def get(
        self,
        key: str,
        type: Type[T],
        *,
        default: Union[T, RaiseOnMissingType] = raise_on_missing,
    ) -> T:
        ...

    @overload
    def get(
        self,
        key: str,
        type: Union[str, Type[T], None] = None,
        *,
        default: Any = raise_on_missing,
    ) -> Any:
        ...

    @overload
    def get(
        self,
        key: Type[T],
        type: None = None,
        *,
        default: Union[T, RaiseOnMissingType] = raise_on_missing,
    ) -> T:
        ...

    def get(self, key: Union[str, Type], type=None, *, default=raise_on_missing):
        """Get a configuation value and cast to the correct type"""
        if isinstance(key, _cla_type):
            return self.__get_type(key, default=default)
        # get using a string key
        assert isinstance(key, str), "Expecting a str key"
        value = OmegaConf.select(
            self.c,
            key,
            default=raise_on_missing,
        )
        if value is raise_on_missing:
            if default is raise_on_missing:
                raise ValueError(f"No value for: {key}")
            return default
        # check the returned type and convert when necessary
        if type is not None and isinstance(value, type):
            return value
        if isinstance(value, Container):
            value = OmegaConf.to_object(value)
        if type is not None:
            value = convert_to_type(value, type)
        return value

    def __get_type(self, key: Type, *, default=raise_on_missing):
        value = self.__type_value.get(key)
        if value is not None:
            return value
        key_str = self.__type_path.get(key)
        if key_str is None:
            if default is raise_on_missing:
                raise ValueError(f"Key not found for type {key}")
            return default
        try:
            value = self.get(key_str, key)
            self.__type_value = value
        except ValueError:
            if default is raise_on_missing:
                raise
            value = default
        return value

    def _merge(self, configs: Iterable[DictConfig]):
        """Merge the current configuration with the given ones"""
        self.c = cast(DictConfig, OmegaConf.merge(self.c, *configs))

    def setup_configuration(
        self,
        conf: Union[DictConfig, str, Dict],  # XXX Type[BaseModel]
        helpers: Dict[str, str] = {},  # XXX deprecated arg?
    ):
        """Add a default configuration

        :param conf: The configuration to merge into the global configuration
        :param helpers: Description of parameters used in argument parser helpers
        """
        # merge the configurations
        # TODO prepare_config in DictConfig?
        # TODO type in values
        if isinstance(conf, str):
            created_config = OmegaConf.create(conf)
            if not isinstance(created_config, DictConfig):
                raise ValueError("The config is not a dict")
            conf = created_config
        if isinstance(conf, DictConfig):
            config = conf
        else:
            created_config = OmegaConf.create(Configuration._prepare_config(conf))
            if not (created_config and isinstance(created_config, DictConfig)):
                raise ValueError('Expecting a non-empty dict configuration')
            config = created_config
        self._merge([config])
        # setup helpers
        for h_key in helpers:
            key = h_key.split('.', 1)[0]
            if not config or key not in config:
                raise ValueError('Invalid helper not in configuration [%s]' % key)
        self.helpers.update(**helpers)

    def from_environ(self, prefixes: Iterable[str]) -> DictConfig:
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
            # TODO adapt name something.my_config from something.my.config
            try:
                conf.merge_with_dotlist([f"{name}={value}"])
            except YAMLError:
                # if cannot load the value as a dotlist, just add the string
                OmegaConf.update(conf, name, value)
        return conf

    @staticmethod
    def _prepare_config(conf):
        if not isinstance(conf, dict):
            return conf
        for k, v in conf.items():
            if '.' in k:
                parts = k.split('.')
                k = parts[0]
                v = {'.'.join(parts[1:]): v}
            conf[k] = Configuration._prepare_config(v)
        return conf
