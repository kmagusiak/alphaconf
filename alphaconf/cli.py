import argparse
import logging
import sys
from collections.abc import Sequence
from typing import Callable, Optional, TypeVar, Union

from omegaconf import MissingMandatoryValue, OmegaConf

from . import initialize, setup_configuration
from .internal.load_file import read_configuration_file

T = TypeVar('T')
__all__ = ["run"]
log = logging.getLogger(__name__)


class ConfigAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print(option_string, values)
        if option_string:
            config = read_configuration_file(values)
        else:
            config = OmegaConf.create(values[0])
        setup_configuration(config)


class SelectConfigAction(ConfigAction):
    def __call__(self, parser, namespace, values, option_string=None):
        key, value = values.split('=')  # XXX _split(value)
        value = value or 'default'
        arg = f"{key}=${{oc.select:base.{key}.{value}}}"
        return super().__call__(parser, namespace, [arg], option_string)


class ShowConfigurationAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        from . import _global_configuration

        config = _global_configuration
        print(config.c)
        parser.exit()


def parser_create(method, add_arguments=True, **args):
    from .internal import application

    args.setdefault('prog', args.pop('name', None) or application.get_current_application_name())
    if method:
        args.setdefault('description', method.__doc__)
    args.setdefault('epilog', 'powered by alphaconf')
    parser = argparse.ArgumentParser(**args)
    if add_arguments:
        parser_add_arguments(parser)
    return parser


def parser_add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument(
        '--config',
        '--config-file',
        '-f',
        action=ConfigAction,
        metavar="path",
        help="load a configuration file",
    )
    parser.add_argument(
        '--select',
        action=SelectConfigAction,
        metavar="key=base_template",
        help="select a configuration template",
    )
    parser.add_argument(
        '--configuration',
        '-C',
        nargs=0,
        action=ShowConfigurationAction,
        help="show the configuration",
    )
    # TODO does not support -x a=5 -y b=5
    parser.add_argument('key=value', nargs='*', action=ConfigAction, help="add configuration")


def run(
    main: Callable[[], T],
    arguments: Union[bool, Sequence[str]] = True,
    *,
    should_exit: bool = True,
    setup_logging: bool = True,
    **config,
) -> Optional[T]:
    """Run a function/application

    If an application is not given, a new one will be created with configuration properties
    taken from the config. Also, by default logging is set up.

    :param main: The main function to call
    :param arguments: List of arguments (default: True to read sys.argv)
    :param should_exit: Whether an exception should sys.exit (default: True)
    :param config: Arguments passed to Application.__init__() and Application.setup_configuration()
    :return: The result of main
    """
    from . import _global_configuration, get

    arg_parser = parser_create(main, **config, exit_on_error=should_exit)
    try:
        initialize(app_name=arg_parser.prog, setup_logging=False, force=True)
        if arguments is True:
            arguments = sys.argv[1:]
        if not isinstance(arguments, list):
            arguments = []
        args = arg_parser.parse_args(arguments)
        # args = arg_parser.parse_intermixed_args(arguments)  # XXX NOT WHAT I WANT
        print(args)  # TODO
        if setup_logging:
            from .logging_util import setup_application_logging

            setup_application_logging(get('logging', default=None))
    except MissingMandatoryValue as e:
        log.error(e)
        if should_exit:
            sys.exit(99)
        raise
    """
    except ArgumentError as e:
        log.error(e)
        if should_exit:
            sys.exit(2)
        raise
    except ExitApplication:
        log.debug('Normal application exit')
        if should_exit:
            sys.exit()
        return None
    """

    # Run the application
    if get('testing', bool, default=False):
        log.info('Testing (%s: %s)', arg_parser.prog, main.__qualname__)
        return None
    try:
        log.info('Start (%s: %s)', arg_parser.prog, main.__qualname__)
        for missing_key in OmegaConf.missing_keys(_global_configuration.c):
            log.warning('Missing configuration key: %s', missing_key)
        result = main()
        if result is None:
            log.info('End.')
        else:
            log.info('End: %s', result)
        return result
    except Exception as e:
        # no need to log exc_info beacause the parent will handle it
        log.error('Failed (%s) %s', type(e).__name__, e, exc_info=should_exit)
        raise
