#!/usr/bin/env python3
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

import alphaconf.cli


class Conn(BaseModel):
    url: str = Field("http://github.com", title="Some URL")
    home: Path = Path("~")


class MyConfiguration(BaseModel):
    name: Optional[str] = Field(None, title="Some name to show")
    some_date: Optional[date] = None
    connection: Optional[Conn] = None


alphaconf.setup_configuration(MyConfiguration, path="c")


def main():
    """Typed configuration example"""
    logging.info('Got configuration name: %s', alphaconf.get('c.name'))
    c = alphaconf.get(MyConfiguration)
    logging.info("Found configuration object: %s", c)
    if c.connection:
        logging.info(
            'connection.home: %s (%s)',
            alphaconf.get('c.connection.home', default='unset'),
            c.connection.home,
        )


if __name__ == '__main__':
    alphaconf.cli.run(main)
