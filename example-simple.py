#!/usr/bin/env python3
import logging
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

import alphaconf
import alphaconf.logging_util


class Conn(BaseModel):
    url: str
    user: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='MY_PREFIX_', case_sensitive=False)

    foo: str = Field('xxx', alias='myal')
    bar: str = Field('xxx')

    c: Union[Conn, str] = Conn()
    d: Optional[PostgresDsn] = None


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

    print(Settings().model_dump())
    Settings.model_validate

    # get the application name from the configuration
    print('app:', alphaconf.configuration.get().application.name)
    # shortcut version to get a configuration value
    print('server.user:', alphaconf.get('server.user'))
    print('server.home', alphaconf.get('server.home', Path))

    # you can set additional dynamic values in the logging
    context_value = ['init']
    alphaconf.logging_util.DynamicLogRecord.set_generator(lambda: context_value)
    # you can log extra values with formatters such as json, try:
    # ./example-simple.py logging.handlers.console.formatter=json
    logging.info('The app is running...', extra={'other': 'othervalue'})
    context_value = None

    logging.info('Just a log')
    # show configuration
    value = alphaconf.get('show', str)
    if value and (value := alphaconf.get(value)):
        print(value)
    # log an exception if we have it in the configuration
    if alphaconf.get('exception'):
        try:
            raise RuntimeError("Asked to raise something")
        except Exception:
            logging.error("Just log something", exc_info=True)
    context_value = ['finished']


if __name__ == '__main__':
    # running with explicit parameters
    alphaconf.run(
        main,
        name='example',
        version='0.1',
    )
