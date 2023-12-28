#!/usr/bin/env python3
import logging
from typing import Optional

from pydantic import BaseModel, Field

import alphaconf.cli
import alphaconf.logging_util


class Opts(BaseModel):
    show: Optional[str] = Field(None, description="The name of the selection to show")
    exception: bool = Field(False, description="If set, raise an exception")


# adding a default configuration
# these will be merged with the application
alphaconf.setup_configuration(Opts)
alphaconf.setup_configuration(
    {
        "server": {
            "name": "test_server",
            "user": "${oc.env:USER}",
        }
    }
)


app = alphaconf.cli.CliApplication(name='example', version='0.1')


@app.command()
def main():
    """Simple demo of alphaconf"""

    # get the application name from the configuration
    print('app:', alphaconf.get("application.name"))
    # shortcut version to get a configuration value
    print('server.name', alphaconf.get('server.name'))
    print('server.user:', alphaconf.get('server.user'))

    # you can set additional dynamic values in the logging
    context_value = ['init']
    alphaconf.logging_util.DynamicLogRecord.set_generator(lambda: context_value)
    # you can log extra values with formatters such as json, try:
    # ./example-simple.py logging.handlers.console.formatter=json
    logging.info('The app is running...', extra={'other': 'othervalue'})
    context_value = None

    logging.info('Just a log')
    # show configuration
    value = alphaconf.get('show', str, default=None)
    if value and (value := alphaconf.get(value, default=None)):
        print(value)
    # log an exception if we have it in the configuration
    if alphaconf.get('exception', default=False):
        try:
            raise RuntimeError("Asked to raise something")
        except Exception:
            logging.error("Just log something", exc_info=True)
    context_value = ['finished']


if __name__ == '__main__':
    app.run()
