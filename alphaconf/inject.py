import inspect
from dataclasses import dataclass
from typing import Callable, Dict, TypeVar

import alphaconf

R = TypeVar('R')


@dataclass
class InjectArgument:
    name: str
    verify: bool = False
    # rtype: type = None  # TODO add type transformer

    def get_value(self, type_spec, required):
        get_args: dict = {'key': self.name}
        if type_spec:
            get_args['type'] = type_spec
        if not required:
            get_args['default'] = None
        value = alphaconf.get(**get_args)
        return value


class Injector:
    args: Dict[str, InjectArgument]
    prefix: str

    def __init__(self, prefix: str = ""):
        if prefix and not prefix.endswith("."):
            prefix += "."
        self.prefix = prefix
        self.args = {}

    def inject(self, name: str, optional, type, resolver):
        pass

    def decorate(self, func: Callable[..., R]) -> Callable[[], R]:
        signature = inspect.signature(func)

        def call():
            args = {}  # TODO {**self.values}
            for name, iarg in self.args.items():
                param = signature.parameters.get(name, None)
                if not param:
                    if iarg.verify:
                        raise TypeError("Missing argument", name)
                    continue
                arg_type = None
                if param.annotation is not param.empty and isinstance(param.annotation, type):
                    arg_type = param.annotation
                required = param.default is param.empty
                value = iarg.get_value(arg_type, required)
                if value is None and not required:
                    continue
                args[name] = value
            return func(**args)

        return call
