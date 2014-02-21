"""
Test remote index.
"""
from logging import getLogger
from textwrap import dedent

from mock import patch, MagicMock
from nose.tools import assert_raises, eq_, ok_
from requests import codes, ConnectionError, Timeout

from cheddar.exceptions import NotFoundError
from cheddar.index.remote import (build_remote_path,
                                  fetch_url,
                                  get_absolute_path,
                                  get_base_url,
                                  get_request_location,
                                  iter_version_links)
from cheddar.tests.fixtures import setup


TIMEOUT = 10


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


def test_fetch_url_ok():
    """
    200 status codes succeed.
    """
    with patch("cheddar.index.remote.get") as mocked:
        mocked.return_value = MagicMock()
        mocked.return_value.status_code = codes.ok
        response = fetch_url("http://example.com", TIMEOUT, getLogger())
        eq_(codes.ok, response.status_code)


def test_fetch_url_not_ok():
    """
    Non-200 status codes are treated as NotFoundErrors.
    """
    with patch("cheddar.index.remote.get") as mocked:
        mocked.return_value = MagicMock()
        mocked.return_value.status_code = codes.bad_request
        with assert_raises(NotFoundError):
            fetch_url("http://example.com", TIMEOUT, getLogger())


def test_fetch_url_timeout():
    """
    Timeouts are treated as NotFoundErrors.
    """
    with patch("cheddar.index.remote.get") as mocked:
        mocked.side_effect = Timeout
        with assert_raises(NotFoundError):
            fetch_url("http://example.com", TIMEOUT, getLogger())


def test_fetch_url_connection_error():
    """
    Connection errors are treated as NotFoundErrors.
    """
    with patch("cheddar.index.remote.get") as mocked:
        mocked.side_effect = ConnectionError
        with assert_raises(NotFoundError):
            fetch_url("http://example.com", TIMEOUT, getLogger())


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
    cases = [("../../packages/2.4/m/mock/mock-0.4.0-py2.4.egg#md5=e948e25b46f75d343a7fcdf24a36005c",  # noqa
              "https://pypi.python.org/simple/mock/",
              "/remote/packages/2.4/m/mock/mock-0.4.0-py2.4.egg?base=https%3A%2F%2Fpypi.python.org#md5=e948e25b46f75d343a7fcdf24a36005c"),  # noqa
             ("http://effbot.org/media/downloads/PIL-1.1.7a2-py2.5-macosx10.5.mpkg.zip",
              "http://effbot.org/downloads/",
              "/remote/media/downloads/PIL-1.1.7a2-py2.5-macosx10.5.mpkg.zip?base=http%3A%2F%2Feffbot.org"),  # noqa
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
          <a/>
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


class TestCachedRemoteIndex(object):

    def setup(self):
        setup(self)
        self.index = self.app.index.remote

    def test_key(self):
        eq_(self.index._key("foo"), "cheddar.remote.foo")

    def test_is_expired(self):
        """
        Verify expiration calculation.
        """
        ok_(self.index.versions_long_ttl > self.index.versions_short_ttl)

        eq_(self.index._is_expired(-2), False)
        eq_(self.index._is_expired(-1), False)

        eq_(self.index._is_expired(0), True)
        eq_(self.index._is_expired(self.index.versions_short_ttl), True)
        eq_(self.index._is_expired(self.index.versions_long_ttl - self.index.versions_short_ttl), True)  # noqa

        eq_(self.index._is_expired(self.index.versions_long_ttl - self.index.versions_short_ttl + 1), False)  # noqa
        eq_(self.index._is_expired(self.index.versions_long_ttl), False)

    def test_cached_index_not_cached(self):
        eq_(self.index._get_cached_index("foo"), (None, False))

    def test_cached_index_cached(self):
        versions = {"foo-1.0.tar.gz": "../../packages/foo-1.0.tar.gz"}
        self.index._save_index("foo", versions)
        eq_(self.index._get_cached_index("foo"), (versions, False))

    def test_cached_index_negative_cached(self):
        self.index._save_negative_index("foo")
        eq_(self.index._get_cached_index("foo"), ({}, False))

    def test_cached_index_cached_expired(self):
        versions = {"foo-1.0.tar.gz": "../../packages/foo-1.0.tar.gz"}
        self.index._save_index("foo", versions)
        with patch.object(self.index, "_is_expired", lambda ttl: True):
            eq_(self.index._get_cached_index("foo"), (versions, True))

    def test_get_versions_cached(self):
        """
        Return cached results if not expired.
        """
        versions = {"foo-1.0.tar.gz": "../../packages/foo-1.0.tar.gz"}
        self.index._save_index("foo", versions)
        with patch("cheddar.index.remote.get") as mocked:
            result = self.index.get_versions("foo")
            eq_(result, versions)
            eq_(mocked.call_count, 0)

    def test_get_versions_cached_expired_found(self):
        """
        Return new results if cache is expired.
        """
        versions = {"foo-1.0.tar.gz": "/remote/packages/foo-1.0.tar.gz?base=http%3A%2F%2Fpypi.python.org"}  # noqa

        HTML = dedent("""\
            <html>
              <body>
                 <a href="../../packages/foo-1.0.tar.gz"/>foo-1.0.tar.gz</a>
              </body>
            </html>""")

        ok_(not self.app.redis.exists(self.index._key("foo")))
        self.index._save_index("foo", versions)
        with patch.object(self.index, "_is_expired", lambda ttl: True):
            with patch("cheddar.index.remote.get") as mocked:
                mocked.return_value = MagicMock()
                mocked.return_value.status_code = codes.ok
                mocked.return_value.headers = {"content-type": "text/html"}
                mocked.return_value.text = HTML
                result = self.index.get_versions("foo")
                eq_(result, versions)
                eq_(mocked.call_count, 1)
                ok_(self.app.redis.exists(self.index._key("foo")))

    def test_get_versions_cached_expired_not_found(self):
        """
        Reraise error if new results are not found and cache is expired and save negative value.
        """
        versions = {"foo-1.0.tar.gz": "../../packages/foo-1.0.tar.gz"}
        self.index._save_index("foo", versions)
        with patch.object(self.index, "_is_expired", lambda ttl: True):
            with patch("cheddar.index.remote.get") as mocked:
                mocked.return_value = MagicMock()
                mocked.return_value.status_code = codes.not_found
                with assert_raises(NotFoundError):
                    self.index.get_versions("foo")
                eq_(mocked.call_count, 1)
                eq_(self.app.redis.get(self.index._key("foo")), "{}")

    def test_get_versions_cached_expired_connectivity_error(self):
        """
        Return expired results on connectivity error.
        """
        versions = {"foo-1.0.tar.gz": "../../packages/foo-1.0.tar.gz"}
        self.index._save_index("foo", versions)
        with patch.object(self.index, "_is_expired", lambda ttl: True):
            with patch("cheddar.index.remote.get") as mocked:
                mocked.return_value = MagicMock()
                mocked.return_value.status_code = codes.gateway_timeout
                result = self.index.get_versions("foo")
                eq_(result, versions)
                eq_(mocked.call_count, 1)

    def test_get_versions_not_cached_connectivity_error(self):
        """
        Reraise error on connectivity error if no cached results.
        """
        with patch.object(self.index, "_is_expired", lambda ttl: True):
            with patch("cheddar.index.remote.get") as mocked:
                mocked.return_value = MagicMock()
                mocked.return_value.status_code = codes.gateway_timeout
                with assert_raises(NotFoundError):
                    self.index.get_versions("foo")
                eq_(mocked.call_count, 1)
