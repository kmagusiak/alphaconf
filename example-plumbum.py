#!/usr/bin/env python3
import logging

import plumbum

import alphaconf.cli
from alphaconf.inject import inject_auto

alphaconf.setup_configuration({"cmd": "ls"})


@inject_auto()
def main(cmd: str):
    """Simple demo of alphaconf with plumbum"""
    log = logging.getLogger(__name__)
    cmd = plumbum.local[cmd]
    log.info("Running a command %s", cmd)
    return cmd.run_fg()


if __name__ == '__main__':
    alphaconf.cli.run(main)
