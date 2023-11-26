import datetime
from pathlib import Path

from omegaconf import OmegaConf

try:
    import pydantic
except ImportError:
    pydantic = None  # type: ignore

__doc__ = """Resolves types when reading values from the configuration.

You can add values to TYPE_CONVERTER which is used in `alphaconf.get()`.
This way, you can load values from an external source.
By the way, you could register new resolvers in OmegaConf.
"""


def read_text(value):
    return Path(value).expanduser().read_text()


def parse_bool(value) -> bool:
    if isinstance(value, str):
        value = value.strip().lower()
        if value in ('no', 'false', 'n', 'f', 'off', 'none', 'null', 'undefined', '0'):
            return False
    return bool(value)


TYPE_CONVERTER = {
    bool: parse_bool,
    datetime.datetime: datetime.datetime.fromisoformat,
    datetime.date: lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(),
    datetime.time: datetime.time.fromisoformat,
    Path: lambda s: Path(s).expanduser(),
    'read_text': read_text,
    'read_strip': lambda s: read_text(s).strip(),
    'read_bytes': lambda s: Path(s).expanduser().read_bytes(),
}
_type = type

# register resolved from strings
for _name, _function in TYPE_CONVERTER.items():
    if isinstance(_name, str):
        OmegaConf.register_new_resolver(_name, _function)  # type: ignore


def convert_to_type(value, type):
    """Converts a value to the given type.

    :param value: Any value
    :param type: A class or a callable used to convert the value
    :return: Result of the callable
    """
    if pydantic:
        if issubclass(type, pydantic.BaseModel):
            type.model_construct
            return type.model_validate(value)
        if isinstance(type, _type):
            return pydantic.TypeAdapter(type).validate_python(value)
    type = TYPE_CONVERTER.get(type, type)
    return type(value)
