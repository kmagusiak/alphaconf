import datetime
from pathlib import Path

TYPE_CONVERTER = {
    datetime.datetime: datetime.datetime.fromisoformat,
    datetime.date: lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(),
    Path: lambda s: Path(s).expanduser(),
}


def convert_to_type(value, type):
    """Converts a value to the given type.

    :param value: Any value
    :param type: A class or a callable used to convert the value
    :return: Result of the callable
    """
    type = TYPE_CONVERTER.get(type, type)
    return type(value)
