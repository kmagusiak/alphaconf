#!/usr/bin/env python3
import logging

import plumbum

import alphaconf.cli

alphaconf.setup_configuration({"cmd": "ls"})

app = alphaconf.cli.CliApplication()


@app.command()
def main():
    """Simple demo of alphaconf with plumbum"""
    log = logging.getLogger(__name__)
    cmd = plumbum.local[alphaconf.get("cmd")]
    log.info("Running a command %s", cmd)
    return cmd.run_fg()


if __name__ == '__main__':
    app.run()
