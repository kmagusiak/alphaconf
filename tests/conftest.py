import pytest

import alphaconf
from alphaconf.internal.configuration import Configuration


@pytest.fixture(autouse=True)
def reset_configuration():
    alphaconf._application = None
    old = alphaconf._global_configuration
    alphaconf._global_configuration = config = Configuration(parent=old)
    alphaconf.setup_configuration = config.setup_configuration
    alphaconf.get = config.get
    yield
    alphaconf._global_configuration = old
    alphaconf.setup_configuration = old.setup_configuration
    alphaconf.get = old.get
