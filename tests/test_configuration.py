from pathlib import Path

import pytest
from omegaconf import DictConfig

from alphaconf import Configuration


@pytest.fixture(scope='function')
def config():
    c = {
        'a': {'b': 3},
        'root': 'R',
        'b': True,
        'num': 5,
        'home': '/home',
        'with_underscore': "/_\\",
    }
    conf = Configuration()
    conf.setup_configuration(c)
    return conf


@pytest.fixture(scope='function')
def config_req(config):
    config.setup_configuration({'req': '???'})
    return config


@pytest.mark.parametrize(
    "key,expected",
    [
        ('a', {'b': 3}),
        ('a.b', 3),
        ('b', True),
        ('num', 5),
    ],
)
def test_select_dict(config, key, expected):
    assert config.get(key) == expected


def test_default(config):
    assert config.get('nonexistingkey', default=3) == 3


def test_cast(config):
    # cast bool into int
    assert config.get('b') is True
    assert config.get('b', int) == 1
    # cast Path
    assert isinstance(config.get('home', Path), Path)


def test_cast_inexisting(config):
    assert config.get('nonexistingkey', int, default=None) is None
    assert config.get('nonexistingkey', int, default="abc") == "abc"


def test_cast_omega(config):
    conf = config.get('', DictConfig)
    assert isinstance(conf, DictConfig)
    assert conf.a == {'b': 3}
    assert config.get('', DictConfig) is conf


def test_select_empty(config):
    result = config.get("")
    assert all(k in result for k in config.c)


def test_select_required(config):
    assert config.get('z', default=None) is None
    with pytest.raises(ValueError):
        print(config.get('z'))
    assert config.get('z', default='a') == 'a'


def test_select_required_incomplete(config_req):
    # when we have a default, return it
    assert config_req.get('req', default='def') == 'def'
    # when required, raise missing
    with pytest.raises(ValueError):
        print(config_req.get('req'))


@pytest.mark.parametrize(
    "name,expected",
    [
        ('a.b', 'a.b'),
        ('unknown', 'unknown'),
        ('a.b.zz', 'a.b.zz'),
        ('b', 'b'),
    ],
)
def test_env_find_name_simple(config, name, expected):
    assert Configuration._find_name(name.split('.'), config.c) == expected


def test_env_find_name_complex():
    config = Configuration()
    config.setup_configuration(
        {
            'a': {'b': 1},
            'my_test': {'a': 2},
            'test_test': {
                'x': 3,
                'my_test': 4,
            },
        }
    )
    c = config.c
    assert Configuration._find_name(['a', 'b'], c) == 'a.b'
    assert Configuration._find_name(['my', 'test'], c) == 'my_test'
    assert Configuration._find_name(['my', 'test', 'a'], c) == 'my_test.a'
    assert Configuration._find_name(['test', 'test', 'my', 'test'], c) == 'test_test.my_test'


def test_config_setup_dots(config):
    config.setup_configuration(
        {
            'a.b': {
                'c.d': 1,
                'two': 2,
                'c.x': 'x',
            },
        }
    )
    assert config.get('a.b.c.d') == 1
    assert config.get('a.b.c.x') == 'x'
    assert config.get('a.b.two') == 2


def test_config_setup_path(config):
    config.setup_configuration({'test': 954}, path='a.b')
    assert config.get('a.b.test') == 954
