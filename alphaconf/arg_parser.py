import itertools
from typing import Dict, Iterable, List, Optional, Union, cast

from omegaconf import DictConfig, OmegaConf


def _split(value, char="="):
    vs = value.split(char, 1)
    if len(vs) < 2:
        vs.append(None)
    return vs


class ExitApplication(BaseException):
    """Signal to exit the application normally"""

    pass


class ArgumentError(RuntimeError):
    """Argument parsing error"""

    def __init__(self, message: str, *args: object, arg=None) -> None:
        if arg:
            message = f"{arg}: {message}"
        super().__init__(message, *args)


class Action:
    """Action for parsing"""

    def __init__(self, *, metavar=None, help=None) -> None:
        self.metavar = metavar
        self.help = help
        self.has_arg = bool(metavar)

    def check_argument(self, value):
        if not value and self.metavar:
            return "Required value"
        return None

    def handle(self, result, value):
        if result.result:
            return "Result is already set"
        result.result = self
        return 'stop'

    def run(self, app):
        raise ArgumentError(f"Cannot execute action {self}")

    def __str__(self) -> str:
        return type(self).__name__


class ShowConfigurationAction(Action):
    """Show configuration action"""

    def run(self, app):
        print(app.yaml_configuration())
        raise ExitApplication


class HelpAction(Action):
    """Help action"""

    def run(self, app):
        app.print_help()
        raise ExitApplication


class VersionAction(Action):
    """Version action"""

    def run(self, app):
        p = app.properties
        prog = p.get('name')
        version = p.get('version')
        print(f"{prog} {version}")
        desc = p.get('short_description')
        if desc:
            print(desc)
        raise ExitApplication


class ConfigurationAction(Action):
    """Configuration action"""

    def check_argument(self, value):
        if self.metavar and '=' in self.metavar and '=' not in value:
            return 'Argument should be in format ' + (self.metavar)
        return super().check_argument(value)

    def handle(self, result, value):
        result._add_config(value)


class ConfigurationFileAction(ConfigurationAction):
    """Load configuration file action"""

    def check_argument(self, value):
        if not value:
            return 'Missing filename for configuration file'
        return None

    def handle(self, result, value):
        result._add_config(OmegaConf.load(value))


class ConfigurationSelectAction(ConfigurationAction):
    """oc.select configuration action"""

    def check_argument(self, value):
        return Action.check_argument(self, value)

    def handle(self, result, value):
        key, value = _split(value)
        value = value or 'default'
        arg = "{key}=${{oc.select:base.{key}.{value}}}".format(key=key, value=value)
        return super().handle(result, arg)


class ParseResult:
    """The result of argument parsing"""

    result: Optional[Action]
    rest: List[str]
    _config: List[Union[str, DictConfig]]

    def __init__(self) -> None:
        """Initialize the result"""
        self.result = None
        self.rest = []
        self._config = []

    def _add_config(self, value: Union[List[str], DictConfig, Dict, str]):
        """Add a configuration item"""
        if isinstance(value, list):
            self._config.extend(value)
            return
        elif isinstance(value, DictConfig):
            pass
        elif isinstance(value, dict):
            value = OmegaConf.create(value)
        elif isinstance(value, str):
            pass
        else:
            raise ArgumentError(f"Invalid configuration type {type(value)}")
        self._config.append(value)

    def configurations(self) -> Iterable[DictConfig]:
        """List parsed configuration dicts"""
        configuration_list = self._config
        if not configuration_list:
            return
        for typ, conf in itertools.groupby(configuration_list, type):
            if issubclass(typ, DictConfig):
                yield from cast(Iterable[DictConfig], conf)
            else:
                yield OmegaConf.from_dotlist(list(cast(Iterable[str], conf)))

    def __repr__(self) -> str:
        return f"(result={self.result}, config={self._config}, rest={self.rest})"


class ArgumentParser:
    """Parses arguments for alphaconf"""

    _opt_actions: Dict[str, Action]
    _pos_actions: List[Action]
    help_messages: Dict[str, str]

    def __init__(self) -> None:
        self._opt_actions = {}
        self._pos_actions = []
        self.help_messages = {}

    def parse_args(self, arguments: List[str]) -> ParseResult:
        """Parse the argument"""
        result = ParseResult()
        arguments = list(arguments)
        arguments.reverse()
        while arguments:
            arg = arguments.pop()
            if arg == '--':
                break
            value = None
            is_opt = arg.startswith('-')
            if is_opt and '=' in arg:
                # arg is -xxx=yyy, split it
                arg, value = _split(arg)
                if not arg.startswith('--') and len(arg) != 2:
                    raise ArgumentError("Short option must be alone with a value", arg=arg)
            if is_opt:
                # parse option arguments
                action = self._opt_actions.get(arg)
                if not action:
                    raise ArgumentError('Unrecognized option', arg=arg)
                if value is None and action.has_arg:
                    if not arguments:
                        raise ArgumentError(f"No more arguments to read {action.metavar}", arg=arg)
                    value = arguments.pop()
                elif value is not None and not action.has_arg:
                    raise ArgumentError("Action has no arguments", arg=arg)
                error = action.check_argument(value)
                if error:
                    raise ArgumentError(error, arg=arg)
                action_result = action.handle(result, value)
            else:
                # parse positional arguments
                if value is None:
                    value = arg
                arg = None  # type: ignore
                action_result = f"Unrecognized argument: {value}"
                for action in self._pos_actions:
                    if not action.check_argument(value):
                        action_result = action.handle(result, value)
                        break
            # check result
            if action_result == 'stop':
                break
            if action_result:
                raise ArgumentError(action_result, arg=arg)
        # set the rest of the arguments
        arguments.reverse()
        result.rest += arguments
        return result

    def add_argument(self, action_class, *names, **kw):
        """Add an argument handler

        :param action_class: Action(kw) will be added as a handler
        :param names: Option or positional argument name
        """
        action = action_class(**kw)
        is_opt = False
        for name in names:
            if not name.startswith('-'):
                continue
            self._opt_actions[name] = action
            is_opt = True
        if not is_opt:
            if 'metavar' not in kw:
                raise ArgumentError(f"Missing metavar for action {action}")
            self._pos_actions.append(action)

    def print_help(self):
        """Print the help"""
        lines = []
        tpl = "  {:<27} {}"
        if self._opt_actions:
            lines.append('options:')
            visited = set()
            for action in self._opt_actions.values():
                if action in visited:
                    continue
                visited.add(action)
                opts = [o for o, a in self._opt_actions.items() if a == action]
                option_line = ', '.join(opts)
                if action.metavar:
                    option_line += ' ' + action.metavar
                if len(option_line) > 27:
                    lines.append(tpl.format(option_line, ''))
                    if action.help:
                        lines.append((30 * ' ') + action.help)
                else:
                    lines.append(tpl.format(option_line, action.help or ''))
            lines.append('')
        if self._pos_actions:
            lines.append('positional arguments:')
            for action in self._pos_actions:
                lines.append(tpl.format(action.metavar or '', action.help or ''))
        if self.help_messages:
            for name, help in self.help_messages.items():
                lines.append(tpl.format(name, help))
        print(*lines, sep='\n')


def configure_parser(parser: ArgumentParser, *, app=None):
    """Add argument parsing for alphaconf"""
    parser.add_argument(
        ConfigurationAction,
        metavar='key=value',
        help='Configuration items',
    )
    parser.add_argument(
        HelpAction,
        '-h',
        '--help',
        help="Show the help",
    )
    if app and app.properties.get('version'):
        parser.add_argument(
            VersionAction,
            '-V',
            '--version',
            help="Show the version",
        )
    parser.add_argument(
        ShowConfigurationAction,
        '-C',
        '--configuration',
        help="Show the configuration",
    )
    parser.add_argument(
        ConfigurationFileAction,
        '-f',
        '--config',
        '--config-file',
        metavar='path',
        help="Load configuration from file",
    )
    parser.add_argument(
        ConfigurationSelectAction,
        '--select',
        help="Shortcut to select a base configuration",
        metavar="key=base_template",
    )
