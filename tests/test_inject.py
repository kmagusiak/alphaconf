import alphaconf
from alphaconf.inject import Injector


def test_inject():
    alphaconf.setup_configuration({'a': 5})
    alphaconf.set_application(alphaconf.Application())
    v = Injector().inject('a').decorate(lambda a: a + 1)
    assert v() == 6
