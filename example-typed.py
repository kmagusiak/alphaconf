#!/usr/bin/env python3
import logging
from dataclasses import dataclass
from typing import Optional

from omegaconf import OmegaConf

import alphaconf


@dataclass
class MyConfiguration:
    name: Optional[str] = None


alphaconf.setup_configuration({'c': OmegaConf.structured(MyConfiguration)})


def main():
    """Typed configuration example"""
    logging.info('Got configuration name: %s', alphaconf.get('c.name'))


if __name__ == '__main__':
    alphaconf.run(main)
