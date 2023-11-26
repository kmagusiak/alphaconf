from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pydantic
import pytest

from alphaconf import Configuration


class Person(pydantic.BaseModel):
    first_name: str
    last_name: str

    @property
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])


class TypedConfig(pydantic.BaseModel):
    x_path: Path = Path('~')
    x_date: Optional[date] = None
    x_datetime: Optional[datetime] = None
    x_name: str = pydantic.Field('me', description="Some name")
    x_num: int = 0
    x_person: Optional[Person] = None


@pytest.fixture(scope='function')
def config_typed():
    c = Configuration()
    c.setup_configuration(TypedConfig)
    return c


@pytest.fixture(scope='function')
def config_changed(config_typed):
    config_typed.setup_configuration(
        {
            'x_num': 1,
            'x_name': 'test',
            'x_date': '2023-05-06',
            'x_datetime': '2023-08-06 00:00:00',
        }
    )
    return config_typed


@pytest.mark.parametrize(
    "key,expected",
    [
        ('x_num', 0),
        ('x_name', "me"),
        ('x_date', None),
        ('x_person', None),
    ],
)
def test_get_default(config_typed, key, expected):
    v = config_typed.get(TypedConfig)
    assert getattr(v, key) == expected


@pytest.mark.parametrize(
    "key,expected",
    [
        ('x_num', 1),
        ('x_name', "test"),
        ('x_date', date(2023, 5, 6)),
        ('x_datetime', datetime(2023, 8, 6)),
        ('x_person', None),
    ],
)
def test_get_changed(config_changed, key, expected):
    v = config_changed.get(TypedConfig)
    assert getattr(v, key) == expected


def test_get_path(config_typed):
    v = config_typed.get(TypedConfig)
    assert isinstance(v.x_path, Path)


def test_set_person(config_typed):
    config_typed.setup_configuration(
        {
            'x_person': {
                'first_name': 'A',
                'last_name': 'B',
            }
        }
    )
    person = config_typed.get('x_person', Person)
    assert person
    assert person.full_name == 'A B'


def test_set_person_type(config_typed):
    config_typed.setup_configuration(Person(first_name='A', last_name='T'), path='x_person')
    person = config_typed.get(Person)
    assert person.full_name == 'A T'
