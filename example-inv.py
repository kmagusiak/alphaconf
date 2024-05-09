import logging

from invoke import task

import alphaconf.invoke


@task
def doit(ctx, param=None):
    """Some documentation..."""
    logging.info('Hello')
    # get the default configuration
    logging.info('Backup: %s', alphaconf.get("backup", default=None))
    logging.info('Param: [%s]', param)


# add some default configuration and run/configure invoke's namespace
alphaconf.setup_configuration({'backup': 'all'})
# TODO just setup logging and load variables into ns?
alphaconf.invoke.run(__name__, globals())
