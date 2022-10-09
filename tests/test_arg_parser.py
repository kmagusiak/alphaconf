import pytest
from omegaconf import OmegaConf

import alphaconf.arg_parser as ap


@pytest.fixture(scope='function')
def parser():
    parser = ap.ArgumentParser()
    parser.add_argument(
        ap.VersionAction,
        '-V',
        '--version',
        help="Show the version",
    )
    parser.add_argument(
        ap.ConfigurationAction,
        metavar='key=value',
    )
    return parser


def test_parse_empty(parser):
    r = parser.parse_args([])
    assert isinstance(r, ap.ParseResult)


def test_version(parser, application):
    r = parser.parse_args(['-V'])
    print(r)
    assert isinstance(r.result, ap.VersionAction)
    with pytest.raises(ap.ExitApplication):
        r.result.run(application)


def test_parse_arguments(parser):
    other_arguments = ['other', 'arguments']
    r = parser.parse_args(['hello=world', 'test=123', '--'] + other_arguments)
    print(r)
    assert r.result is None
    conf = OmegaConf.merge(*r.configurations())
    print(conf)
    assert conf.hello == "world" and conf.test == 123
    assert r.rest == other_arguments


def test_parse_invalid(parser):
    with pytest.raises(ap.ArgumentError):
        parser.parse_args(['--hello-world'])
