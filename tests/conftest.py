import pytest


@pytest.fixture(scope='function')
def app():
    from alphaconf import Application

    return Application()
