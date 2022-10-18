import collections
import json
import logging
import traceback
from logging import Formatter, LogRecord
from typing import Any, Callable

try:
    import colorama
except ImportError:
    colorama = None

"""Colors used by Colorama (if installed)"""
LOG_COLORS = {}
if colorama:
    colorama.init()
    # default color scheme
    LOG_COLORS = {
        logging.CRITICAL: colorama.Fore.BLUE,
        logging.ERROR: colorama.Fore.RED,
        logging.WARNING: colorama.Fore.YELLOW,
        logging.INFO: colorama.Fore.GREEN,
        # logging.DEBUG: colorama.Fore.LIGHTBLACK_EX,
        -1: colorama.Style.RESET_ALL,  # reset
    }

"""Fields of a default log record"""
_LOG_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__.keys())


def set_gmt(enable=True):
    """Set GMT time for logging formatters

    :param enable: Whether to set GMT or localtime
    """
    import time

    Formatter.converter = time.gmtime if enable else time.localtime


class DynamicLogRecord(logging.LogRecord):
    """LogRecord which pre-pends a string from a generator function

    You can set a generator function that will return a context_value that
    will be available in the LogRecord.
    """

    value_generator: Callable = lambda: ''

    @classmethod
    def set_generator(cls, generator: Callable, set_as_factory=True):
        """Set the generator and LogRecordFactory

        :param generator: A function to produce the string value
        :param set_as_factory: Set the class as a log factory (default: true)
        """
        cls.value_generator = generator
        if set_as_factory:
            logging.setLogRecordFactory(cls)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        value = type(self).value_generator()
        if value is None:
            self.context_value = ''
        else:
            self.context_value = value

    def getMessage(self) -> str:  # noqa: N802
        msg = super().getMessage()
        if self.context_value:
            msg = "%s %s" % (self.context_value, msg)
        return msg


class ColorFormatter(Formatter):
    """Colorize message based on log level"""

    def formatMessage(self, record):  # noqa: N802
        # we can change the message because each call to format() resets it
        if record.levelno in LOG_COLORS:
            record.message = LOG_COLORS[record.levelno] + record.message + LOG_COLORS[-1]
        return super().formatMessage(record)


class JSONFormatter(Formatter):
    """Format the log message as a single-line JSON dict"""

    def format(self, record: LogRecord) -> str:
        d: collections.OrderedDict[str, Any] = collections.OrderedDict()
        if self.usesTime():
            d['time'] = self.formatTime(record, self.datefmt)
        d['level'] = record.levelname
        d['message'] = self.formatMessage(record)
        d['location'] = {
            label: getattr(record, key, None)
            for label, key in [
                ('path_name', 'pathname'),
                # ('file_name', 'filename'),
                ('module', 'module'),
                ('line', 'lineno'),
                ('function', 'funcName'),
            ]
        }
        if record.process:
            d['process'] = {'id': record.process, 'name': record.processName}
        if record.thread:
            d['thread'] = {'id': record.thread, 'name': record.threadName}
        if record.exc_info:
            d['exception'] = self.formatException(record.exc_info)
        if record.stack_info:
            d['stack_info'] = self.formatStack(record.stack_info)
        other = {k: v for k, v in record.__dict__.items() if k not in _LOG_RECORD_FIELDS}
        if other:
            d['context'] = other
        return json.dumps(d, check_circular=False, default=lambda v: str(v))

    def usesTime(self) -> bool:  # noqa: N802
        return True

    def formatMessage(self, record: LogRecord) -> str:  # noqa: N802
        return record.getMessage()

    def formatException(self, ei):  # noqa: N802
        if ei:
            return {
                'type': ei[0].__name__,
                'message': str(ei[1]),
                'detail': traceback.format_exception(*ei),
            }
        return {}
