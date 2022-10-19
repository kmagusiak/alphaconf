import pathlib

import pytest

from alphaconf import DictConfig, MissingMandatoryValue, select


@pytest.fixture(scope='function')
def container():
    return {
        'a': {'b': 3},
        'root': 'R',
        'b': True,
        'home': '/home',
    }


@pytest.fixture(scope='function')
def container_incomplete(container):
    return DictConfig(
        {
            'a': container['a'],
            'req': '???',
        }
    )


@pytest.mark.parametrize(
    "key,expected",
    [
        ('a', {'b': 3}),
        ('a.b', 3),
        ('z', None),
        ('b', True),
    ],
)
def test_select_dict(container, key, expected):
    assert select(container, key) == expected


def test_default(container):
    assert select(container, 'nonexistingkey', default=3) == 3


def test_cast(container):
    # cast bool into int
    assert select(container, 'b', int) == 1
    # cast Path
    assert isinstance(select(container, 'home', pathlib.Path), pathlib.Path)
    # cast inexisting and default
    assert select(container, 'nonexistingkey', int) is None
    assert select(container, 'nonexistingkey', int, default="abc") == "abc"


def test_cast_omega(container):
    conf = select(container, '', DictConfig)
    assert isinstance(conf, DictConfig)
    assert conf.a == {'b': 3}
    assert select(conf, '', DictConfig) is conf


def test_select_empty(container):
    assert select(container, '') == container


def test_select_required(container):
    cont = DictConfig(container)
    assert select(cont, 'z') is None
    with pytest.raises(MissingMandatoryValue):
        print(select(cont, 'z', required=True))
    assert select(cont, 'z', required=True, default='a') == 'a'


def test_select_required_incomplete(container_incomplete):
    cont = container_incomplete
    # when we have a default, return it
    assert select(cont, 'req', default='def') == 'def'
    # when required, raise missing
    with pytest.raises(MissingMandatoryValue):
        print(select(cont, 'req', required=True))
    # when required, even if a default is given, if req=???, raise
    with pytest.raises(MissingMandatoryValue):
        print(select(cont, 'req', required=True, default='def'))


def test_select_from_any():
    # for now, we allow selecting from anything that can be a container
    # OmegaConf.create() return the value to be selected
    assert select([1, 2, 3], '[0]') == 1
    assert select("[1, 2, 3]", '[0]') == 1
