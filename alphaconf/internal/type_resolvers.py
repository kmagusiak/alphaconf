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


def _parse_bool(value) -> bool:
    if isinstance(value, str):
        value = value.strip().lower()
        if value in ('no', 'false', 'n', 'f', 'off', 'none', 'null', 'undefined', '0'):
            return False
    return bool(value)


TYPE_CONVERTER = {
    bool: _parse_bool,
    datetime.datetime: datetime.datetime.fromisoformat,
    datetime.date: lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(),
    datetime.time: datetime.time.fromisoformat,
    Path: lambda s: Path(str(s)).expanduser(),
    str: lambda v: str(v),
    'read_text': lambda s: Path(s).expanduser().read_text(),
    'read_strip': lambda s: Path(s).expanduser().read_text().strip(),
    'read_bytes': lambda s: Path(s).expanduser().read_bytes(),
}

# register resolved from strings
for _name, _function in TYPE_CONVERTER.items():
    if isinstance(_name, str):
        OmegaConf.register_new_resolver(_name, _function)  # type: ignore


def convert_to_type(value, type):
    """Converts a value to the given type.

    :param value: Any value
    :param type: A class used to convert the value
    :return: Result of the callable
    """
    if isinstance(type, str):
        return TYPE_CONVERTER[type](value)
    # assert isinstance(type, globals().type)
    if pydantic and issubclass(type, pydantic.BaseModel):
        return type.model_validate(value)
    if isinstance(value, type):
        return value
    if type in TYPE_CONVERTER:
        return TYPE_CONVERTER[type](value)
    if pydantic:
        return pydantic.TypeAdapter(type).validate_python(value)
    return type(value)
