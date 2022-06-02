import itertools
from argparse import Action, ArgumentError
from argparse import ArgumentParser as PrivateArgumentParser
from typing import Dict, Iterable, List, Union

from omegaconf import DictConfig, OmegaConf


class ConfigurationAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            return
        if not isinstance(values, list):
            values = [values]
        for value in values:
            value = self.parse_value(value)
            if not value:
                continue
            self.add_config(namespace, value)

    def parse_value(self, value):
        return value

    def add_config(self, namespace, value):
        cfgs = getattr(namespace, self.dest)
        if not cfgs:
            cfgs = []
            setattr(namespace, self.dest, cfgs)
        if isinstance(value, list):
            value = OmegaConf.from_dotlist(value)
        elif isinstance(value, DictConfig):
            pass
        elif isinstance(value, dict):
            value = OmegaConf.create(value)
        elif isinstance(value, str):
            value = OmegaConf.from_dotlist([value])
        else:
            raise ArgumentError(self, 'Invalid configuration loaded %s' % type(value))
        cfgs.append(value)


class ConfigurationFileAction(ConfigurationAction):
    def parse_value(self, value):
        if not value or not isinstance(value, str):
            raise ArgumentError(self, 'Missing filename for configuration file')
        return OmegaConf.load(value)


class ConfigurationSelectAction(ConfigurationAction):
    def parse_value(self, value):
        if '=' not in value:
            raise ArgumentError(self, 'requires an argument with an equal sign')
        value_split = value.split('=', 1)
        value = value_split[1] if len(value_split) > 1 else 'default'
        return "{key}=${{oc.select:base.{key}.{value}}}".format(key=value_split[0], value=value)


class ArgumentParser:  # TODO use the argparse directly
    """Simple argument parsers for alphaconf"""

    app_properties: Dict
    parse_result: str
    configuration_list: List[Union[str, DictConfig]]
    other_arguments: List[str]  # TODO

    def __init__(self, app_properties: Dict) -> None:
        """Initialze the parser with an application"""
        self.app_properties = app_properties
        parser = PrivateArgumentParser(
            prog=app_properties.get('name') or None,
            description=app_properties.get('description')
            or app_properties.get('short_description'),
        )
        version = app_properties.get('version')
        if version:
            parser.add_argument(
                '-V',
                '--version',
                action='version',
                version='%(prog)s ' + version,
                help="show the version",
            )
        parser.add_argument(
            '-C',
            '--configuration',
            dest='result',
            action='store_const',
            const='show_configuration',
            help="show the configuration",
        )
        parser.add_argument(
            '-f',
            '--config',
            '--config-file',
            action=ConfigurationFileAction,
            metavar='path',
            help="Load configuration from file",
        )
        parser.add_argument(
            '--select',
            dest='config',
            action=ConfigurationSelectAction,
            help="Shortcut to select a base configuration",
            metavar="key=base_template",
        )
        self.parser = parser
        self.add_config_help('key=value', 'Configuration items')
        self.reset()

    def add_config_help(self, name, help):
        self.parser.add_argument(
            'config', action=ConfigurationAction, nargs='*', metavar=name, help=help
        )

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
        ns = self.parser.parse_args(args)
        print(ns)
        self.configuration_list = ns.config
        self.parse_result = ns.result or 'ok'
        return ns
