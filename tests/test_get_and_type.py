import pathlib

import pytest
from omegaconf import DictConfig

import alphaconf


@pytest.fixture(scope='function')
def container():
    c = {
        'a': {'b': 3},
        'root': 'R',
        'b': True,
        'home': '/home',
    }
    alphaconf.setup_configuration(c)
    return c


@pytest.fixture(scope='function')
def container_incomplete(container):
    c = DictConfig(
        {
            'a': container['a'],
            'req': '???',
        }
    )
    alphaconf.setup_configuration(c)
    return c


@pytest.mark.parametrize(
    "key,expected",
    [
        ('a', {'b': 3}),
        ('a.b', 3),
        ('b', True),
    ],
)
def test_select_dict(container, key, expected):
    assert alphaconf.get(key) == expected


def test_default(container):
    assert alphaconf.get('nonexistingkey', default=3) == 3


def test_cast(container):
    # cast bool into int
    assert alphaconf.get('b', int) == 1
    # cast Path
    assert isinstance(alphaconf.get('home', pathlib.Path), pathlib.Path)
    # cast inexisting and default
    assert alphaconf.get('nonexistingkey', int, default=None) is None
    assert alphaconf.get('nonexistingkey', int, default="abc") == "abc"


def test_cast_omega(container):
    conf = alphaconf.get('', DictConfig)
    assert isinstance(conf, DictConfig)
    assert conf.a == {'b': 3}
    assert alphaconf.get('', DictConfig) is conf


def test_select_empty(container):
    result = alphaconf.get("")
    assert all(k in result for k in container)


def test_select_required(container):
    assert alphaconf.get('z', default=None) is None
    with pytest.raises(ValueError):
        print(alphaconf.get('z'))
    assert alphaconf.get('z', default='a') == 'a'


def test_select_required_incomplete(container_incomplete):
    # when we have a default, return it
    assert alphaconf.get('req', default='def') == 'def'
    # when required, raise missing
    with pytest.raises(ValueError):
        print(alphaconf.get('req'))
