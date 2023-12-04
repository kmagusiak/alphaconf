import string
from typing import Optional

import pytest

import alphaconf
import alphaconf.inject as inj


@pytest.fixture(scope="function")
def c():
    alphaconf.setup_configuration(dict(zip(string.ascii_letters, range(1, 11))))
    alphaconf.set_application(app := alphaconf.Application())
    return app.configuration


def mytuple(a: int, b=1, *, c, d=1, zz: int = 1):
    return (a, b, c, d, zz)


@pytest.fixture(scope="function")
def mytupledef():
    return inj.inject("a", lambda: 1)(inj.inject("c", lambda: 1)(mytuple))


def test_inject(c, mytupledef):
    assert mytuple(0, c=2) == (0, 1, 2, 1, 1)
    assert mytupledef() == (1, 1, 1, 1, 1)
    assert inj.inject("c", lambda: 5)(mytuple)(0) == (0, 1, 5, 1, 1)
    assert inj.inject("b", lambda: 5)(mytupledef)() == (1, 5, 1, 1, 1)


def test_inject_name(c, mytupledef):
    assert inj.inject('a', 'g')(mytuple)(c=0) == (7, 1, 0, 1, 1)


def test_inject_auto_lambda(c):
    assert inj.inject_auto()(lambda a: a + 1)() == 2
    assert inj.inject_auto()(lambda c: c + 1)() == 4


def test_inject_auto(c):
    assert inj.inject_auto()(mytuple)() == (1, 2, 3, 4, 1)


def test_inject_auto_ignore(c):
    assert inj.inject_auto(ignore={'b'})(mytuple)() == (1, 1, 3, 4, 1)


def test_inject_auto_missing():
    with pytest.raises(KeyError, match=": a"):
        inj.inject_auto()(mytuple)()


def test_inject_auto_prefix():
    def f1(name):
        return name

    alphaconf.setup_configuration({"mytest.name": "ok"})
    assert inj.inject_auto(prefix="mytest")(f1)() == "ok"


def test_inject_type_def(mytupledef):
    with pytest.raises(KeyError):
        inj.inject("a", "nothing")(mytupledef)()


def test_inject_type_cast(c):
    def f1(zz: str):
        return zz

    def f2(zz: str = "ok"):
        return zz

    def f3(zz: Optional[str] = None):
        return zz

    assert inj.inject('zz', 'g')(f1)() == "7"
    assert inj.inject('zz', 'nothing')(f2)() == "ok"
    assert inj.inject('zz', 'nothing')(f3)() is None
    assert inj.inject('zz', 'g')(f3)() == "7"
