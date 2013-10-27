"""
Test controller behavior.
"""
from base64 import b64encode
from contextlib import contextmanager
from json import loads
from os import environ
from os.path import dirname, exists, join
from shutil import copyfile, rmtree
from tempfile import mkdtemp
from textwrap import dedent

from mock import patch
from mockredis import MockRedis
from nose.tools import assert_raises, eq_, ok_
from requests import codes

from cheddar.app import create_app


class TestControllers(object):

    def setup(self):
        self.config_dir = mkdtemp()
        self.config_file = join(self.config_dir, "cheddar.conf")
        self.local_cache_dir = mkdtemp()
        self.remote_cache_dir = mkdtemp()
        self.username = "username"
        self.password = "password"

        with open(self.config_file, "w") as file_:
            file_.write('LOCAL_CACHE_DIR = "{}"\n'.format(self.local_cache_dir))
            file_.write('REMOTE_CACHE_DIR = "{}"\n'.format(self.remote_cache_dir))

        self.previous_config_file = environ.get("CHEDDAR_SETTINGS")
        environ["CHEDDAR_SETTINGS"] = self.config_file

        with patch('cheddar.configure.Redis', MockRedis):
            self.app = create_app(testing=True)

        self.client = self.app.test_client()
        self.use_json = dict(accept="application/json; charset=UTF-8")
        self.use_auth = dict(authorization="Basic {}".format(b64encode("{}:{}".format(self.username,
                                                                                      self.password))))
        self.app.redis.set("cheddar.user.{}".format(self.username), self.password)

    def teardown(self):
        if self.previous_config_file is None:
            del environ["CHEDDAR_SETTINGS"]
        else:
            environ["CHEDDAR_SETTINGS"] = self.previous_config_file

        rmtree(self.local_cache_dir)
        rmtree(self.remote_cache_dir)
        rmtree(self.config_dir)

    def test_index_template_render(self):
        result = self.client.get("/")
        eq_(result.status_code, codes.ok)

    def test_index_template_json(self):
        result = self.client.get("/", headers=self.use_json)
        eq_(result.status_code, codes.ok)
        eq_(loads(result.data), dict())

    def test_simple_no_packages_template_render(self):
        result = self.client.get("/simple")
        eq_(result.status_code, codes.ok)

    def test_simple_no_packages_json(self):
        result = self.client.get("/simple", headers=self.use_json)
        eq_(result.status_code, codes.ok)
        eq_(loads(result.data), dict(packages=[]))

    def test_simple_two_packages_json(self):
        self.app.index.local._add(**{"name": "foo", "version": "1.0"})
        self.app.index.local._add(**{"name": "bar", "version": "1.1"})

        result = self.client.get("/simple", headers=self.use_json)
        eq_(result.status_code, codes.ok)
        eq_(loads(result.data), dict(packages=["bar", "foo"]))

    def test_list_releases_template_render(self):
        self.app.index.local._add(**{"name": "foo", "version": "1.0", "_filename": "foo-1.0.tar.gz"})
        self.app.index.local._add(**{"name": "foo", "version": "1.1", "_filename": "foo-1.1.tar.gz"})
        self.app.index.local._add(**{"name": "foo", "version": "1.0.dev1", "_filename": "foo-1.0.dev1.tar.gz"})

        with self._mocked_get("http://pypi.python.org/simple/foo", codes.ok) as mock_get:
            mock_get.return_value.text = dedent("""\
                <html>
                  <body>
                     <a href="../../packages/foo/foo-1.0c1.tar.gz">foo-1.0c1.tar.gz</a>
                  </body>
                </html>""")
            result = self.client.get("/simple/foo")

        eq_(result.status_code, codes.ok)
        iter_ = self.app.index.remote._iter_release_links(result.data)
        eq_(iter_.next(), ("foo-1.0.dev1.tar.gz", "/local/foo-1.0.dev1.tar.gz"))
        eq_(iter_.next(), ("foo-1.0c1.tar.gz", "/remote/packages/foo/foo-1.0c1.tar.gz"))
        eq_(iter_.next(), ("foo-1.0.tar.gz", "/local/foo-1.0.tar.gz"))
        eq_(iter_.next(), ("foo-1.1.tar.gz", "/local/foo-1.1.tar.gz"))
        with assert_raises(StopIteration):
            iter_.next()

    def test_list_releases_json(self):
        self.app.index.local._add(**{"name": "foo", "version": "1.0", "_filename": "foo-1.0.tar.gz"})
        self.app.index.local._add(**{"name": "foo", "version": "1.1", "_filename": "foo-1.1.tar.gz"})

        with self._mocked_get("http://pypi.python.org/simple/foo", codes.not_found):
            result = self.client.get("/simple/foo", headers=self.use_json)

        eq_(result.status_code, codes.ok)
        eq_(loads(result.data), dict(releases={"foo-1.0.tar.gz": "local/foo-1.0.tar.gz",
                                               "foo-1.1.tar.gz": "local/foo-1.1.tar.gz"}))

    def test_get_local_distribution(self):
        distribution = join(self.local_cache_dir, "releases", "example-1.0.tar.gz")
        copyfile(join(dirname(__file__), "data/example-1.0.tar.gz"), distribution)
        self.app.index.local._add(**{"name": "example", "version": "1.0", "_filename": distribution})

        result = self.client.get("/local/example-1.0.tar.gz")

        eq_(result.status_code, codes.ok)
        eq_(result.headers["Content-Type"], "application/x-gzip")
        eq_(result.headers["Content-Length"], "843")

    def test_get_remote_distribution(self):
        template = join(dirname(__file__), "data/example-1.0.tar.gz")

        with self._mocked_get("http://pypi.python.org/foo/example-1.0.tar.gz", codes.ok) as mock_get:
            with open(template) as file_:
                mock_get.return_value.content = file_.read()
            mock_get.return_value.headers = {"Content-Type": "application/x-gzip",
                                             "Content-Length": "843"}
            result = self.client.get("/remote/foo/example-1.0.tar.gz")

        eq_(result.status_code, codes.ok)
        eq_(result.headers["Content-Type"], "application/x-gzip")
        eq_(result.headers["Content-Length"], "843")

    def test_get_remote_distribution_cached(self):
        template = join(dirname(__file__), "data/example-1.0.tar.gz")
        distribution = join(self.remote_cache_dir, "releases", "example-1.0.tar.gz")
        copyfile(template, distribution)

        result = self.client.get("/remote/foo/example-1.0.tar.gz")

        eq_(result.status_code, codes.ok)
        eq_(result.headers["Content-Type"], "application/x-gzip")
        eq_(result.headers["Content-Length"], "843")

    def test_delete_requires_auth(self):
        result = self.client.delete("/simple/example/1.0")
        eq_(result.status_code, codes.unauthorized)

    def test_delete_package(self):
        distribution = join(self.local_cache_dir, "releases", "example-1.0.tar.gz")
        copyfile(join(dirname(__file__), "data/example-1.0.tar.gz"), distribution)
        self.app.index.local._add(**{"name": "example", "version": "1.0", "_filename": distribution})

        eq_(self.app.redis.smembers("cheddar.local"), set(["example"]))
        eq_(self.app.redis.smembers("cheddar.local.example"), set(["1.0"]))
        eq_(self.app.redis.hlen("cheddar.local.example-1.0"), 3)
        eq_(self.app.redis.hget("cheddar.local.example-1.0", "name"), "example")
        eq_(self.app.redis.hget("cheddar.local.example-1.0", "version"), "1.0")
        ok_(exists(distribution))

        result = self.client.delete("/simple/example/1.0", headers=self.use_auth)
        eq_(result.status_code, codes.ok)

        eq_(self.app.redis.smembers("cheddar.local"), set())
        ok_(not self.app.redis.exists("cheddar.local.example"))
        ok_(not self.app.redis.exists("cheddar.local.example-1.0"))
        ok_(not exists(distribution))

    def test_register_missing_required_parameters(self):
        result = self.client.post("/pypi", data={})
        eq_(result.status_code, codes.bad_request)

    def test_register_ok(self):
        result = self.client.post("/pypi", data={"name": "example",
                                                 "version": "1.0"})
        eq_(result.status_code, codes.ok)

    def test_upload_requires_auth(self):
        with open(join(dirname(__file__), "data/example-1.0.tar.gz")) as file_:
            result = self.client.post("/pypi", data={"file": (file_, "example-1.0.tar.gz")})
        eq_(result.status_code, codes.unauthorized)

    def test_upload_bad_filename(self):
        with open(join(dirname(__file__), "data/example-1.0.tar.gz")) as file_:
            result = self.client.post("/pypi",
                                      data={"file": (file_, "example-1.1.tar.gz")},
                                      headers=self.use_auth)
        eq_(result.status_code, codes.bad_request)

    def test_upload_ok(self):
        with open(join(dirname(__file__), "data/example-1.0.tar.gz")) as file_:
            result = self.client.post("/pypi",
                                      data={"file": (file_, "example-1.0.tar.gz")},
                                      headers=self.use_auth)
        eq_(result.status_code, codes.ok)

    @contextmanager
    def _mocked_get(self, url, status_code):
        with patch("cheddar.remote.get") as mock_get:
            mock_get.return_value.status_code = status_code

            yield mock_get

            mock_get.assert_called_with(url,
                                        timeout=self.app.config["GET_TIMEOUT"])
