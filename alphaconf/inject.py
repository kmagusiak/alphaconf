import functools
import inspect
from typing import Any, Callable, Dict, Optional, Union

import alphaconf

from .internal.type_resolvers import type_from_annotation

__all__ = ["inject", "inject_auto"]


class ParamDefaultsFunction:
    """Function wrapper that injects default parameters"""

    _arg_factory: Dict[str, Callable[[], Any]]

    def __init__(self, func: Callable):
        self.func = func
        self.signature = inspect.signature(func)
        self._arg_factory = {}

    def bind(self, name: str, factory: Callable[[], Any]):
        self._arg_factory[name] = factory

    def __call__(self, *a, **kw):
        args = self.signature.bind_partial(*a, **kw).arguments
        kw.update(
            {name: factory() for name, factory in self._arg_factory.items() if name not in args}
        )
        return self.func(*a, **kw)

    @staticmethod
    def wrap(func) -> "ParamDefaultsFunction":
        if isinstance(func, ParamDefaultsFunction):
            return func
        return functools.wraps(func)(ParamDefaultsFunction(func))


def getter(
    key: str, ktype: Optional[type] = None, *, param: Optional[inspect.Parameter] = None
) -> Callable[[], Any]:
    """Factory function that calls alphaconf.get

    The parameter from the signature can be given to extract the type to cast to
    and whether the configuration value is optional.

    :param key: The key using in alphaconf.get
    :param ktype: Type to cast to
    :param param: The parameter object from the signature
    """
    if ktype is None and param and (ptype := param.annotation) is not param.empty:
        ktype = next(type_from_annotation(ptype), None)
    if param is not None and param.default is not param.empty:
        xparam = param
        return (
            lambda: xparam.default
            if (value := alphaconf.get(key, ktype, default=None)) is None
            and xparam.default is not xparam.empty
            else value
        )
    return lambda: alphaconf.get(key, ktype)


def inject(name: str, factory: Union[None, str, Callable[[], Any]]):
    """Inject an argument to a function from a factory or alphaconf"""

    def do_inject(func):
        f = ParamDefaultsFunction.wrap(func)
        if isinstance(factory, str) or factory is None:
            b = getter(factory or name, param=f.signature.parameters[name])
        else:
            b = factory
        f.bind(name, b)
        return f

    return do_inject


def inject_auto(*, prefix: str = "", ignore: set = set()):
    """Inject automatically all paramters"""
    if prefix and not prefix.endswith("."):
        prefix += "."

    def do_inject(func):
        f = ParamDefaultsFunction.wrap(func)
        for name, param in f.signature.parameters.items():
            if name in ignore:
                continue
            f.bind(name, getter(prefix + name, param=param))
        return f

    return do_inject
