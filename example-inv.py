#!/usr/bin/env python3
import logging

from invoke import Collection, task

import alphaconf.invoke


@task
def doit(ctx):
    logging.info('Hello')
    logging.info('backup %s', alphaconf.configuration().backup)


ns = Collection(doit)
alphaconf.setup_configuration({'backup': 'all'})
alphaconf.invoke.invoke_application(__name__, ns)
