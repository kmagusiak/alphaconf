import logging

from invoke import Collection, task

import alphaconf.invoke


@task
def doit(ctx, param=None):
    logging.info('Hello')
    # get the default configuration
    logging.info('Backup: %s', alphaconf.configuration().backup)
    # if we have a parameter, let's run some code within a context
    # where we use this parameter in the configuration
    if param:
        with alphaconf.application.get().update_configuration({'param': param}):
            logging.info('Param: [%s] and in alphaconf [%s]', param, alphaconf.get('param'))
    else:
        logging.warning('No parameter')


# add some default configuration and run/configure invoke's namespace
ns = Collection(doit)
alphaconf.setup_configuration({'backup': 'all'})
alphaconf.invoke.invoke_application(__name__, ns)
