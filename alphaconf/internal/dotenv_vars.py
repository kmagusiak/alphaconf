import logging
import os
from typing import Optional

log = logging.getLogger(__name__)
_loaded: bool = False


def try_dotenv(load_dotenv: Optional[bool] = None):
    """Load dotenv variables (optionally)"""
    global _loaded
    if load_dotenv is False or (_loaded and load_dotenv is None):
        return
    _loaded = True
    try:
        import dotenv
    except ModuleNotFoundError:
        if load_dotenv:
            raise
        log.debug('dotenv is not installed')
        return
    path = dotenv.find_dotenv(usecwd=True)
    log.debug('Loading dotenv: %s', path or '(none)')
    if not path:
        return
    dotenv.load_dotenv(path)
    # check local overrides
    path += '.local'
    if os.path.isfile(path):
        log.debug('Loading dotenv: %s', path)
        dotenv.load_dotenv(path)
