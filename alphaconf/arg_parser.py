import functools
import itertools
from typing import Callable, Dict, Iterable, List, Union

from omegaconf import DictConfig, MissingMandatoryValue, OmegaConf


class InvalidArgumentError(Exception):
    """Invalid argument on command line"""

    pass


class OptionHandler:
    """Handling an option"""

    arg: List[str]
    handler: Callable
    help: str

    def __init__(self, arg: Union[str, List[str]], handler: Callable, help='', help_arg='') -> None:
        """Initialize option handler"""
        self.arg = arg if isinstance(arg, list) else [arg]
        self.handler = handler
        self.help = help or ''
        self._help_arg = help_arg or ''

    @property
    def help_arg(self):
        """Text for the help line"""
        if self._help_arg:
            return self._help_arg
        return ', '.join(self.arg)

    @help_arg.setter
    def help_arg(self, value):
        self._help_arg = value

    def __repr__(self) -> str:
        return "%s: %s" % (self.arg, self.handler)


class ArgumentParser:
    """Simple argument parsers for alphaconf"""

    app_properties: Dict
    parse_result: str
    configuration_list: List[Union[str, DictConfig]]
    other_arguments: List[str]
    _option_handler_dict: Dict[str, OptionHandler]
    _option_handler_list: List[OptionHandler]
    help_descriptions: Dict[str, str]

    def __init__(self, app_properties: Dict) -> None:
        """Initialze the parser with an application"""
        self.app_properties = app_properties
        self._option_handler_list = []
        self._option_handler_dict = {}
        self.help_descriptions = {}
        self.reset()

    @functools.wraps(OptionHandler.__init__)
    def add_option_handler(self, *a, **kw):
        """Add an option to the parser (passed to OptionHandler)"""
        opt = OptionHandler(*a, **kw)
        self._option_handler_list.append(opt)
        for arg in opt.arg:
            self._option_handler_dict[arg] = opt
        return opt

    def reset(self):
        """Reset the parser"""
        self.parse_result = ''
        self.configuration_list = []
        self.other_arguments = []

    def configurations(self) -> Iterable[DictConfig]:
        """List parsed configuration dicts"""
        for typ, conf in itertools.groupby(self.configuration_list, type):
            if issubclass(typ, DictConfig):
                yield from conf
            else:
                yield OmegaConf.from_dotlist(list(conf))

    def parse_arguments(self, args: List[str]) -> None:
        """Parse arguments

        Parsing rules:
        - "--" indicates end of arguments, rest is put into other arguments
        - "ABC=DEF" is considered as argument ABC and value DEF to load into configuration
        - If the argument starts with a "-", it is handled as an option
        - If the option handling misses an argument, it may raise MissingMandatoryValue
        - The handling is either a special code or a list of "key=value"; see handle_option()

        :param args: List of arguments to parse
        """
        parse_result = ''
        skip = 0
        for i, arg in enumerate(args):
            if skip:
                skip -= 1
                continue
            # Split argument on '=' sign
            arg_split = arg.split('=', 1)
            value = None
            if len(arg_split) > 1:
                arg, value = arg_split
            # Handle option
            try:
                if value is not None and arg[:1] != '-':
                    result = ["%s=%s" % (arg, value)]
                else:
                    result = self.handle_option(arg, value)
            except MissingMandatoryValue:
                if len(args) <= i + 1 and value is None:
                    raise
                value = args[i + 1]
                skip = 1
                result = self.handle_option(arg, value)
            # Handle result option
            if isinstance(result, DictConfig):
                self.configuration_list.append(result)
            elif isinstance(result, list):
                self.configuration_list.extend(result)
            elif result == "stop":
                self.other_arguments += args[i:]
                break
            elif result == 'skip':
                pass
            elif result == 'skip_next':
                skip += 1
            elif result == 'exit':
                parse_result = 'exit'
            elif result.startswith('result:') and not parse_result:
                parse_result = result[7:]
            else:
                raise RuntimeError('Invalid result of handling option')
        try:
            self.handle_other_arguments()
        except InvalidArgumentError:
            if not bool(parse_result):
                raise
            # otherwise skip argument errors since we have a result
        self.parse_result = parse_result or 'ok'

    def handle_option(self, arg: str, value: str) -> Union[str, List[str], DictConfig]:
        """Handle an option found in the arguments

        May rise InvalidArgumentError if the argument is unrecognized.
        Special string values that may be returned:
        - stop: Stop parsing the rest of the arguments and send them to other (default for '--')
        - skip: No-op
        - skip_next: Skip parsing the next argument
        - "result:*": Set the parse result value

        :param arg: The argument
        :param value: The name of the argument (or None)
        """
        if arg == '--':
            return 'stop'
        handler = self._option_handler_dict.get(arg)
        if handler:
            return handler.handler(value)
        raise InvalidArgumentError('Unexpected argument: %s' % arg)

    def handle_other_arguments(self):
        """Handle other unparsed or skipped arguments"""
        other = self.other_arguments
        if other and other[0] != '--':
            raise InvalidArgumentError('Unparsed arguments: %s' % other)

    def print_help(self, brief: str = None):
        """Print the help with options

        :param brief: Whether to print a brief summary ("version" for version only)
        """
        app = self.app_properties
        if brief == 'version':
            print(f"{app.get('name')} {app.get('version', '(no-version)')}")
            return
        # Header
        first_line = f"Usage: {app.get('name')} [ options ]"
        description = app.get('description', '')
        short_description = app.get(
            'short_description',
            description if 0 < len(description) < 50 else "",
        )
        if short_description:
            first_line += (
                " - " if len(first_line) + len(short_description) < 75 else "\n"
            ) + short_description
        print(first_line)
        if brief:
            return
        # Description
        if description and description != short_description:
            print()
            print(description)
        # Options
        print()
        line_format = '  {arg:32s}  {description}'
        for handler in self._option_handler_list:
            print(line_format.format(arg=handler.help_arg, description=handler.help))
        print(line_format.format(arg='key=value', description="Load a configuration key-value"))
        for name, description in sorted(self.help_descriptions.items()):
            print(line_format.format(arg=name, description=description))


def add_default_option_handlers(parser: ArgumentParser, *, add_help_version=True) -> None:
    """Add default options to the parser

    - help
    - version
    - configuration: show it
    - config-file: load the file
    - select: shortcut
    """

    def help(brief=None):
        parser.print_help(brief)
        return 'exit'

    def load_configuration(value):
        if value is None:
            raise MissingMandatoryValue('Missing filename for configuration file')
        return OmegaConf.load(value)

    def select_option(value):
        if value is None or '=' not in value:
            raise MissingMandatoryValue('--select requires an argument with an equal sign')
        value_split = value.split('=', 1)
        value = value_split[1] if len(value_split) > 1 else 'default'
        return ["{key}=${{oc.select:base.{key}.{value}}}".format(key=value_split[0], value=value)]

    if add_help_version:
        parser.add_option_handler(
            ['-h', '-?', '--help'],
            lambda _: help(),
            help="Print help message",
            help_arg='-h, --help',
        )
        parser.add_option_handler(
            ['-V', '--version'],
            lambda _: help('version'),
            help="Print the version",
        )
    parser.add_option_handler(
        ['-C', '--configuration'],
        lambda _: "result:show_configuration",
        help="Show the configuration",
    )
    parser.add_option_handler(
        ['-f', '--config', '--config-file'],
        load_configuration,
        help="Load configuration from file",
        help_arg='-f, --config[-file] path',
    )
    parser.add_option_handler(
        ['--select'],
        select_option,
        help="Shortcut to select a base configuration",
        help_arg="--select key=base_template",
    )
