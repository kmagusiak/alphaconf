import pytest
from omegaconf import DictConfig, OmegaConf

import alphaconf


@pytest.fixture(scope='function')
def application():
    return alphaconf.Application(name='test', version='1.0.0', description='test description')


def test_default_configuration():
    config = alphaconf.configuration.get()
    assert isinstance(config, DictConfig)
    assert 'base' in config
    assert 'logging' in config


def test_run():
    result = 'result'
    r = alphaconf.run(lambda: result, arguments=False, should_exit=False)
    assert r is result


def test_run_application_init():
    name = 'testinit'
    assert alphaconf.get('application') is None
    r = alphaconf.run(lambda: alphaconf.get('application.name'), arguments=False, name=name)
    assert name == r


def test_run_application_help(capsys):
    alphaconf.setup_configuration({'helptest': 1}, {'helptest': 'HELPER_TEST'})
    application = alphaconf.Application(name='myapp', description='my test description')
    r = alphaconf.run(lambda: 1, app=application, arguments=['--help'], should_exit=False)
    assert r is None
    captured = capsys.readouterr()
    out = captured.out.splitlines()
    assert len(out) > 4
    assert 'usage:' in out[0]
    assert application.name in out[0]
    desc = '\n'.join(out[1:5])
    assert application.description in desc
    assert 'HELPER_TEST' in captured.out


def test_run_application_version(capsys, application):
    alphaconf.run(lambda: 'n', app=application, arguments=['--version'], should_exit=False)
    captured = capsys.readouterr()
    out = captured.out
    assert (application.name + ' ' + application.version) in out


def test_run_application_show_configuration(capsys, application):
    alphaconf.run(lambda: 'n', app=application, arguments=['--configuration'], should_exit=False)
    captured = capsys.readouterr()
    out = captured.out
    data = OmegaConf.to_container(OmegaConf.create(out))
    app = data.get('application')
    assert isinstance(app, dict)
    assert app['name'] == application.name


def test_run_application_set_argument():
    r = alphaconf.run(lambda: alphaconf.get('a.b'), arguments=['a.b=36'])
    assert r == 36


def test_run_application_select_logging():
    log = alphaconf.run(lambda: alphaconf.get('logging'), arguments=['--select', 'logging=none'])
    assert isinstance(log, dict)


def test_set_application(application):
    token = alphaconf.configuration.set(OmegaConf.create())
    try:
        alphaconf.set_application(application)
        assert alphaconf.configuration.get() == application.configuration
    finally:
        alphaconf.configuration.reset(token)


def test_setup_configuration():
    alphaconf.setup_configuration({'setup': 'config'}, helpers={'setup': 'help1'})
    assert alphaconf.get('setup') == 'config'
    helpers = alphaconf.Application().argument_parser.help_messages
    assert helpers.get('setup') == 'help1'


def test_setup_configuration_invalid():
    with pytest.raises(ValueError):
        # invalid configuration (must be non-empty)
        alphaconf.setup_configuration(None)
    with pytest.raises(ValueError):
        # invalid helper
        alphaconf.setup_configuration({'invalid': 5}, helpers={'help': 'help1'})


def test_set():
    # test that the set() is active only within the block
    value = '124'
    default = '125-def'
    assert alphaconf.get('value', default=default) is default
    with alphaconf.set(value=value):
        assert alphaconf.get('value') is value
    assert alphaconf.get('value', default=default) is default


def test_secret_masks():
    masks = list(alphaconf.SECRET_MASKS)
    try:
        secret = 's3cret'
        alphaconf.setup_configuration(
            {
                'a': {'mypassword': secret},
                'list': [{'password': '???', 'private_key': '123'}],
            }
        )
        conf = alphaconf.Application().masked_configuration()
        assert conf['a']['mypassword'] != secret
        assert conf['list'][0]['password'] == '???'
        assert conf['list'][0]['private_key'] != secret
    finally:
        alphaconf.SECRET_MASKS.clear()
        alphaconf.SECRET_MASKS.extend(masks)
