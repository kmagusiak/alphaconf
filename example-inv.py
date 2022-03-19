import logging

from invoke import Collection, task

import alphaconf.invoke


@task
def doit(ctx, param=None):
    logging.info('Hello')
    conf = alphaconf.configuration()
    logging.info('Backup: %s', conf.backup)
    if param:
        with alphaconf.application.get().update_configuration({'param': param}):
            logging.info('Param: [%s] and in alphaconf [%s]', param, alphaconf.get('param'))
    else:
        logging.warning('No parameter')


ns = Collection(doit)
alphaconf.setup_configuration({'backup': 'all'})
alphaconf.invoke.invoke_application(__name__, ns)
