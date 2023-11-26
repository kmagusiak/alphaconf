import copy
import os
import typing
import warnings
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

from .type_resolvers import convert_to_type, pydantic

T = TypeVar('T')


class RaiseOnMissingType(Enum):
    RAISE = 'raise'


raise_on_missing = RaiseOnMissingType.RAISE
_cla_type = type


class Configuration:
    c: DictConfig
    __type_path: MutableMapping[Type, Optional[str]]
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
        if type is not None and default is not None:
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
        conf: Union[DictConfig, dict, Any],
        helpers: Dict[str, str] = {},
        *,
        path: str = "",
    ):
        """Add a default configuration

        :param conf: The configuration to merge into the global configuration
        :param helpers: Description of parameters used in argument parser helpers
        :param path: The path to add the configuration to
        """
        if isinstance(conf, type):
            conf_type = conf
        elif pydantic and issubclass(type(conf), pydantic.BaseModel):
            conf_type = type(conf)
        else:
            conf_type = None
        if conf_type:
            # if already registered, set path to None
            self.__type_path[conf_type] = None if conf_type in self.__type_path else path
        if path and not path.endswith('.'):
            path += "."
        if isinstance(conf, str):
            warnings.warn("provide a dict directly", DeprecationWarning)
            created_config = OmegaConf.create(conf)
            if not isinstance(created_config, DictConfig):
                raise ValueError("The config is not a dict")
            conf = created_config
        if isinstance(conf, DictConfig):
            config = self.__prepare_dictconfig(conf, path=path)
        else:
            created_config = self.__prepare_config(conf, path=path)
            if not isinstance(created_config, DictConfig):
                raise ValueError("Failed to convert to a DictConfig")
            config = created_config
        # add path and merge
        if path:
            config = self.__add_path(config, path.rstrip("."))
        self._merge([config])
        self.helpers.update(**helpers)

    def add_helper(self, key, description):
        """Assign a helper description"""
        self.helpers[key] = description

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

    def __prepare_dictconfig(
        self, obj: DictConfig, path: str, recursive: bool = True
    ) -> DictConfig:
        sub_configs = []
        for k, v in obj.items_ex(resolve=False):
            if not isinstance(k, str):
                raise ValueError("Expecting only str instances in dict")
            if recursive:
                v = self.__prepare_config(v, path + k + ".")
            if '.' in k:
                obj.pop(k)
                sub_configs.append(self.__add_path(v, k))
        if sub_configs:
            obj = cast(DictConfig, OmegaConf.unsafe_merge(obj, *sub_configs))
        return obj

    def __prepare_config(self, obj, path):
        if isinstance(obj, DictConfig):
            return self.__prepare_dictconfig(obj, path)
        if pydantic:
            obj = self.__prepare_pydantic(obj, path)
        if isinstance(obj, dict):
            result = {}
            changed = False
            for k, v in obj.items():
                result[k] = nv = self.__prepare_config(v, path + k + ".")
                changed |= v is not nv
            if not changed:
                result = obj
            return self.__prepare_dictconfig(OmegaConf.create(result), path, recursive=False)
        return obj

    def __prepare_pydantic(self, obj, path):
        if isinstance(obj, pydantic.BaseModel):
            # pydantic instance, prepare helpers
            self.__prepare_pydantic(type(obj), path)
            return obj.model_dump(mode="json")
        # parse typing recursively for documentation
        for t in typing.get_args(obj):
            self.__prepare_pydantic(t, path)
        # check if not a type
        if not isinstance(obj, type):
            return obj
        # prepare documentation from types
        if issubclass(obj, pydantic.BaseModel):
            # pydantic type
            defaults = {}
            for k, field in obj.model_fields.items():
                check_type = True
                if field.default is not pydantic.fields._Unset:
                    defaults[k] = field.default
                    check_type = not bool(defaults[k])
                elif field.is_required():
                    defaults[k] = "???"
                else:
                    defaults[k] = None
                if desc := (field.description or field.title):
                    self.add_helper(path + k, desc)
                if check_type and field.annotation:
                    self.__prepare_pydantic(field.annotation, path + k + ".")
            return defaults
        return None

    @staticmethod
    def __add_path(config: Any, path: str) -> DictConfig:
        for part in reversed(path.split(".")):
            config = OmegaConf.create({part: config})
        return config
