"""
Test remote index.
"""
from mock import MagicMock
from nose.tools import eq_

from cheddar.index.remote import get_request_location


def test_get_request_location_no_history_no_headers():
    """
    Request location defaults to the request url.
    """
    url = "http://pypi.python.org/simple/foo"
    response = MagicMock()
    response.history = []
    response.headers = {}
    eq_(get_request_location(response, url), url)


def test_get_request_location_no_history():
    """
    Request location follows response location header.
    """
    url = "http://pypi.python.org/simple/foo"
    response = MagicMock()
    response.history = []
    response.headers = {"location": "http://pypi.python.org/simple/foo/"}
    eq_(get_request_location(response, url), "http://pypi.python.org/simple/foo/")


def test_get_request_location_history():
    """
    Request location follows redirect history.
    """
    url = "http://pypi.python.org/simple/foo"

    redirect = MagicMock()
    redirect.headers = {"location": "https://pypi.python.org/simple/foo"}

    response = MagicMock()
    response.history = [redirect]
    response.headers = {}
    eq_(get_request_location(response, url), "https://pypi.python.org/simple/foo")


def test_get_request_location_multiple_history():
    """
    Request location follows redirect history across multiple redirects.
    """
    url = "http://pypi.python.org/simple/foo"

    redirect1 = MagicMock()
    redirect1.headers = {"location": "https://pypi.python.org/simple/foo"}

    redirect2 = MagicMock()
    redirect2.headers = {"location": "https://pypi.python.org/simple/foo/"}

    response = MagicMock()
    response.history = [redirect1, redirect2]
    response.headers = {}
    eq_(get_request_location(response, url), "https://pypi.python.org/simple/foo/")


def test_get_request_location_multiple_history_partial():
    """
    Request location follows redirect history across multiple redirects
    with partial paths.
    """
    url = "http://pypi.python.org/simple/foo-bar"

    redirect1 = MagicMock()
    redirect1.headers = {"location": "https://pypi.python.org/simple/foo-bar"}

    redirect2 = MagicMock()
    redirect2.headers = {"location": "/simple/foo-bar/"}

    redirect3 = MagicMock()
    redirect3.headers = {"location": "/simple/foo_bar"}

    redirect4 = MagicMock()
    redirect4.headers = {"location": "/simple/foo_bar/"}

    response = MagicMock()
    response.history = [redirect1, redirect2, redirect3, redirect4]
    response.headers = {}
    eq_(get_request_location(response, url), "https://pypi.python.org/simple/foo_bar/")
