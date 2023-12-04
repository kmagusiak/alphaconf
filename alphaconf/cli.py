import sys
from typing import Callable, Optional, Sequence, TypeVar, Union

from omegaconf import MissingMandatoryValue, OmegaConf

from . import set_application
from .internal.application import Application
from .internal.arg_parser import Action, ArgumentError, ExitApplication

T = TypeVar('T')
__all__ = ["run"]


class CommandAction(Action):
    pass  # TODO just read a function name, parse rest with this one


class CliApplication(Application):
    pass


def run(
    main: Callable[[], T],
    arguments: Union[bool, Sequence[str]] = True,
    *,
    should_exit: bool = True,
    app: Optional[Application] = None,
    setup_logging: bool = True,
    **config,
) -> Optional[T]:
    """Run this application

    If an application is not given, a new one will be created with configuration properties
    taken from the config. Also, by default logging is set up.

    :param main: The main function to call
    :param arguments: List of arguments (default: True to read sys.argv)
    :param should_exit: Whether an exception should sys.exit (default: True)
    :param config: Arguments passed to Application.__init__() and Application.setup_configuration()
    :return: The result of main
    """
    # Create the application if needed
    if app is None:
        properties = {
            k: config.pop(k)
            for k in ['name', 'version', 'description', 'short_description']
            if k in config
        }
        # if we don't have a description, get it from the function's docs
        if 'description' not in properties and main.__doc__:
            description = main.__doc__.strip().split('\n', maxsplit=1)
            if 'short_description' not in properties:
                properties['short_description'] = description[0]
            if len(description) > 1:
                import textwrap

                properties['description'] = description[0] + '\n' + textwrap.dedent(description[1])
            else:
                properties['description'] = properties['short_description']
        app = Application(**properties)
    log = app.log

    # Setup the application
    try:
        if arguments is True:
            arguments = sys.argv[1:]
        if not isinstance(arguments, list):
            arguments = []
        app.setup_configuration(arguments=arguments, **config)
        set_application(app)
        configuration = app.configuration
        if setup_logging:
            from .logging_util import setup_application_logging

            setup_application_logging(configuration.get('logging', default=None))
    except MissingMandatoryValue as e:
        log.error(e)
        if should_exit:
            sys.exit(99)
        raise
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

    # Run the application
    if configuration.get('testing', bool, default=False):
        log.info('Testing (%s: %s)', app.name, main.__qualname__)
        return None
    try:
        log.info('Start (%s: %s)', app.name, main.__qualname__)
        for missing_key in OmegaConf.missing_keys(configuration.c):
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
