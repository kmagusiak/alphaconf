import logging

import pytest

import alphaconf
import alphaconf.logging_util


@pytest.fixture(scope='function')
def application():
    return alphaconf.Application(name='test_logging')


@pytest.fixture(scope='function')
def log(application):
    application.setup_configuration(arguments=False, setup_logging=True)
    alphaconf.set_application(application)
    return logging.getLogger()


def test_log_ok(log, caplog):
    log.debug('tdebug')
    log.info('tinfo')
    log.warning('twarn')
    print(caplog.records)
    assert len(caplog.records) == 2  # should not capture debug by default
    assert 'tinfo' == caplog.records[0].message
    assert 'twarn' == caplog.records[1].message


def test_log_exception(log, caplog):
    log.error('terror')
    assert caplog.records[0].message == 'terror'
    caplog.clear()
    try:
        raise ValueError('tvalue')
    except ValueError:
        log.error('err', exc_info=True)
    rec = caplog.records[0]
    exc_type, exc, tb = rec.exc_info
    assert exc_type == ValueError and str(exc) == 'tvalue' and tb


def test_log_format(log, caplog):
    # date hour INFO root [pid,MainThread]: tinfo
    formatter = log.handlers[0].formatter
    assert isinstance(formatter, alphaconf.logging_util.ColorFormatter)
    format_str = formatter._fmt
    assert (
        format_str
        == r'%(asctime)s %(levelname)s %(name)s [%(process)s,%(threadName)s]: %(message)s'
    )
