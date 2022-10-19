import pytest

import alphaconf


@pytest.fixture(autouse=True)
def reset_context_configuration():
    config = alphaconf.configuration.get()
    yield
    alphaconf.configuration.set(config)
