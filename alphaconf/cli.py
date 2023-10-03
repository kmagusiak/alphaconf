import contextvars
import logging
import sys
from typing import Callable, List, Optional, TypeVar, Union

from omegaconf import MissingMandatoryValue, OmegaConf

# absolute import to make sure it's properly initialized
import alphaconf

from .internal import Application
from .internal.arg_parser import ArgumentError, ExitApplication

T = TypeVar('T')


def run(
    main: Callable[[], T],
    arguments: Union[bool, List[str]] = True,
    *,
    should_exit: bool = True,
    app: Optional[Application] = None,
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
    from .internal import application_log as log

    if 'setup_logging' not in config:
        config['setup_logging'] = True
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
    try:
        app.setup_configuration(arguments, **config)
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
    context = contextvars.copy_context()
    try:
        return context.run(__run_application, app=app, main=main, exc_info=should_exit)
    except Exception:
        if should_exit:
            log.debug('Exit application')
            sys.exit(1)
        raise


def __run_application(app: Application, main: Callable[[], T], exc_info=True) -> T:
    """Set the application and execute main"""
    alphaconf.configuration.set(app.configuration)
    app_log = logging.getLogger()
    if testing := alphaconf.get('testing'):
        app_log.info('Testing (%s: %s)', app.name, main.__qualname__)
        return testing
    # Run the application
    try:
        app_log.info('Start (%s: %s)', app.name, main.__qualname__)
        for missing_key in OmegaConf.missing_keys(alphaconf.configuration.get()):
            app_log.warning('Missing configuration key: %s', missing_key)
        result = main()
        if result is None:
            app_log.info('End.')
        else:
            app_log.info('End: %s', result)
        return result
    except Exception as e:
        # no need to log exc_info beacause the parent will handle it
        app_log.error('Failed (%s) %s', type(e).__name__, e, exc_info=exc_info)
        raise
