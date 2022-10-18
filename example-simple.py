#!/usr/bin/env python3
import logging
from pathlib import Path

import alphaconf
import alphaconf.logging_util

# adding a default configuration
# these will be merged with the application
alphaconf.setup_configuration(
    """
server:
  url: http://default
  user: ${oc.env:USER}
  home: "~"
show: false
exception: false
""",
    {
        "server": "Arguments for the demo",
        "show": "The name of the selection to show",
        "exception": "If set, raise an exception",
    },
)


def main():
    """Simple demo of alphaconf"""
    # you can set additional dynamic values in the logging
    context_value = ['init']
    alphaconf.logging_util.DynamicLogRecord.set_generator(lambda: context_value)
    # you can log extra values with formatters such as json, try:
    # ./example-simple.py logging.handlers.console.formatter=json
    logging.info('The app is running...', extra={'other': 'othervalue'})
    context_value = None

    # get the application name from the configuration
    print('app:', alphaconf.configuration.get().application.name)
    # shortcut version to get a configuration value
    print('server.user:', alphaconf.get('server.user'))
    print('server.home', alphaconf.get('server.home', Path))

    # show configuration
    value = alphaconf.get('show')
    if value and (value := alphaconf.get(value)):
        print(value)
    # log an exception if we have it in the configuration
    if alphaconf.get('exception'):
        try:
            raise RuntimeError("Asked to raise something")
        except Exception:
            logging.error("Just log something", exc_info=True)
    context_value = 'finished'


if __name__ == '__main__':
    alphaconf.run(
        main,
        name='example',
        version='0.1',
    )
