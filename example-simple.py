#!/usr/bin/env python3
import logging

import alphaconf

alphaconf.setup_configuration(
    """
server:
  url: http://default
  user: ${oc.env:USER}
"""
)


def main():
    logging.info('The app is running...', extra={'other': 'othervalue'})
    print('app:', alphaconf.configuration().application.name)
    print('server.user:', alphaconf.get('server.user'))
    if alphaconf.get('exception'):
        try:
            raise RuntimeError("Asked to raise something")
        except Exception:
            logging.error("Just log something", exc_info=True)


if __name__ == '__main__':
    alphaconf.Application(
        name='example',
        version='0.1',
    ).run(main)
