"""
Test remote index.
"""
from textwrap import dedent

from mock import MagicMock
from nose.tools import assert_raises, eq_

from cheddar.index.remote import (build_remote_path,
                                  get_absolute_path,
                                  get_base_url,
                                  get_request_location,
                                  iter_version_links)


def test_get_absolute_path():
    """
    Relative and absolute URL paths are converted to absolute paths.
    """
    eq_(get_absolute_path("http://foo.com/bar/baz", "../foo"), "/bar/foo")
    eq_(get_absolute_path("http://foo.com/bar/baz", "/foo"), "/foo")


def test_get_base_url():
    """
    Base URL preserves scheme, host, and port.
    """
    eq_(get_base_url("http://foo.com/bar/baz"), "http://foo.com")
    eq_(get_base_url("https://foo.com:443/foo/bar"), "https://foo.com:443")


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


def test_build_remote_path():
    """
    Remote path incorporates path, base_url, and md5 fragmnt.
    """
    cases = [("../../packages/2.4/m/mock/mock-0.4.0-py2.4.egg#md5=e948e25b46f75d343a7fcdf24a36005c",
              "https://pypi.python.org/simple/mock/",
              "/remote/packages/2.4/m/mock/mock-0.4.0-py2.4.egg?base=https%3A%2F%2Fpypi.python.org#md5=e948e25b46f75d343a7fcdf24a36005c"),  # noqa
             ("http://effbot.org/media/downloads/PIL-1.1.7a2-py2.5-macosx10.5.mpkg.zip",
              "http://effbot.org/downloads/",
              "/remote/media/downloads/PIL-1.1.7a2-py2.5-macosx10.5.mpkg.zip?base=http%3A%2F%2Feffbot.org"),
             ("http://effbot.org/media/downloads/PIL-1.1.7.tar.gz",
              "http://effbot.org/downloads/",
              "/remote/media/downloads/PIL-1.1.7.tar.gz?base=http%3A%2F%2Feffbot.org")]

    def _validate(href, location, path):
        eq_(build_remote_path(href, location), path)

    for href, location, path in cases:
        yield _validate, href, location, path


def test_iter_version_links():
    """
    Versions links are correctly parsed.
    """
    HTML = dedent("""\
        <html>
          <body>
          <a href="../../packages/foo-1.0.tar.gz"/>foo-1.0.tar.gz</a>
          <a href="../../packages/bar-1.0.tar.gz"/>bar-1.0.tar.gz</a>
          <a href="http://foo.com/foo" rel="download"/>foo download link</a>
          <a href="http://foo.com/files/foo-0.1.0.zip" rel="download">0.1.0 download_url</a><br/>
          </body>
        </html>""")

    iter_ = iter_version_links(HTML, "foo")
    eq_(next(iter_), ("foo-1.0.tar.gz", "../../packages/foo-1.0.tar.gz"))
    eq_(next(iter_), "http://foo.com/foo")
    eq_(next(iter_), ("foo-0.1.0.zip", "http://foo.com/files/foo-0.1.0.zip"))

    with assert_raises(StopIteration):
        next(iter_)
