import datetime
from typing import Any, Tuple

from omegaconf import DictConfig, OmegaConf

SUPPORTED_EXTENSIONS = ['yaml', 'json']

try:
    import toml

    class TomlDecoderPrimitive(toml.TomlDecoder):
        """toml loader which reads dates as strings for compitability with JSON"""

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


def read_configuration_file(path: str) -> DictConfig:
    """Read a configuration file and return a configuration

    The result is always a DictConfig.
    When the file contains a list, it's embedded in a Dict with a key 'config'.
    """
    if path.endswith('.toml') and toml:
        config = toml.load(path, decoder=TomlDecoderPrimitive())
        return OmegaConf.create(config)
    conf = OmegaConf.load(path)
    if not isinstance(conf, DictConfig):
        conf = OmegaConf.create({'config': conf})
    return conf
