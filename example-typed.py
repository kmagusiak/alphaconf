#!/usr/bin/env python3
import logging
from datetime import date
from typing import Optional

import pydantic

import alphaconf.cli


class MyConfiguration(pydantic.BaseModel):
    name: Optional[str] = None
    """name variable"""
    dd: Optional[date] = None


alphaconf.setup_configuration({"c": MyConfiguration})


def main():
    """Typed configuration example"""
    logging.info('Got configuration name: %s', alphaconf.get('c.name'))
    c = alphaconf.get(MyConfiguration)
    logging.info("Found configuration object:", c)


if __name__ == '__main__':
    alphaconf.cli.run(main)
