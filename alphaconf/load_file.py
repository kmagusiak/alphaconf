import datetime
from typing import Any, Tuple

from omegaconf import OmegaConf

SUPPORTED_EXTENSIONS = ['yaml', 'json']

try:
    # since python 3.11 (tomllib is available)
    import toml

    class TomlDecoderPrimitive(toml.TomlDecoder):
        def load_value(self, v: str, strictly_valid: bool = True) -> Tuple[Any, str]:
            value, itype = super().load_value(v, strictly_valid)
            # convert date, datetime, time using isoformat()
            if itype in ('date', 'time'):
                itype = 'str'
                if isinstance(value, datetime.datetime):
                    value = value.isoformat(' ')
                else:
                    value = value.isoformat()
            return value, itype

    SUPPORTED_EXTENSIONS.append('toml')
except ImportError:
    toml = None  # type: ignore


def read_configuration_file(path: str):
    """Read a configuration file and return a configuration"""
    if path.endswith('.toml') and toml:
        config = toml.load(path, decoder=TomlDecoderPrimitive())
        return OmegaConf.create(config)
    return OmegaConf.load(path)
