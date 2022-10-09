import pathlib

import pytest

import alphaconf


@pytest.fixture(scope='function')
def container():
    return {
        'a': {'b': 3},
        'root': 'R',
        'b': True,
        'home': '/home',
    }


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
    assert alphaconf.select(container, key) == expected


def test_default(container):
    assert alphaconf.select(container, 'nonexistingkey', default=3) == 3


def test_cast(container):
    # cast bool into int
    assert alphaconf.select(container, 'b', int) == 1
    # cast Path
    assert isinstance(alphaconf.select(container, 'home', pathlib.Path), pathlib.Path)
    # cast inexisting and default
    assert alphaconf.select(container, 'nonexistingkey', int) is None
    assert alphaconf.select(container, 'nonexistingkey', int, default="abc") == "abc"
