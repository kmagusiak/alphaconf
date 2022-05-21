#!/usr/bin/env python3
import logging
from pathlib import Path

import alphaconf

# adding a default configuration
# these will be merged with the application
alphaconf.setup_configuration(
    """
server:
  url: http://default
  user: ${oc.env:USER}
  home: "~"
""",
    {"server": "Contains the arguments for the demo"},
)


def main():
    """Demo application"""
    # you can log extra values with formatters such as json, try:
    # ./example-simple.py logging.handlers.console.formatter=json
    logging.info('The app is running...', extra={'other': 'othervalue'})
    # get the application name from the configuration
    print('app:', alphaconf.configuration().application.name)
    # shortcut version to get a configuration value
    print('server.user:', alphaconf.get('server.user'))
    print('server.home', alphaconf.get('server.home', Path))
    # log an exception if we have it in the configuration
    if alphaconf.get('exception'):
        try:
            raise RuntimeError("Asked to raise something")
        except Exception:
            logging.error("Just log something", exc_info=True)


if __name__ == '__main__':
    alphaconf.Application(
        name='example',
        version='0.1',
        description="Simple demo of alphaconf",
    ).run(main)
