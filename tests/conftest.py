import pytest

import alphaconf


@pytest.fixture(scope='function')
def application():
    from alphaconf import Application

    return Application(name='test', version='1.0.0', description='test description')


@pytest.fixture(autouse=True)
def reset_context_configuration():
    config = alphaconf.configuration.get()
    yield
    alphaconf.configuration.set(config)
