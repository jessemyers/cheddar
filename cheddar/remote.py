"""
Implements a remote (proxy) package index.
"""
from json import dumps, loads
from os import makedirs
from os.path import abspath, exists, isdir, join
from urllib import quote
from urlparse import urlsplit, urlunsplit

from BeautifulSoup import BeautifulSoup
from flask import abort
from requests import codes, get
from werkzeug.exceptions import HTTPException

from cheddar.index import Index


class RemoteIndex(Index):
    """
    Access package data through a remote index server (e.g. pypi.python.org)
    """
    def __init__(self, app):
        self.index_url = app.config["INDEX_URL"]
        self.get_timeout = app.config["GET_TIMEOUT"]

    def register(self, name, version, data):
        """
        Unsupported.
        """
        pass

    def upload(self, file_):
        """
        Unsupported.
        """
        pass

    def get_local_packages(self):
        """
        No local packages because the index is remote.

        :returns: an empty list
        """
        return []

    def get_available_releases(self, name):
        """
        Request package data from remote index and parse HTML.
        """
        url = "{}/{}".format(self.index_url, name)
        response = get(url, timeout=self.get_timeout)
        if response.status_code != codes.ok:
            abort(codes.not_found)
        soup = BeautifulSoup(response.text)

        return {node.text: "remote" + get_absolute_path(self.index_url, node["href"]) for node in soup.findAll("a")}

    def get_release(self, path, local):
        """
        Request distribution data for path on the index server.
        """
        response = get(make_absolute_url(self.index_url, path), timeout=self.get_timeout)
        if response.status_code != codes.ok:
            abort(codes.not_found)
        return response.content, response.headers["Content-Type"]


class CachedRemoteIndex(RemoteIndex):
    """
    Cache remote package data.

    - Since release data may change frequently, it is cached in Redis for simple expiration.
    - Distribution data is saved to the file system for easy inspection and backup.
    """
    def __init__(self, app):
        super(CachedRemoteIndex, self).__init__(app)
        self.redis = app.redis
        self.releases_ttl = app.config["RELEASES_TTL"]
        self.cache_dir = app.config["REMOTE_CACHE_DIR"]
        # cache dirname should contain current username to minimize conflicts
        if not isdir(self.cache_dir):
            makedirs(self.cache_dir)

    def get_available_releases(self, name):
        """
        Adds redis caching to available releases data.

        Currently, does not implement negative caching.
        """
        key = "cheddar.remote.{}".format(name)

        # Check cache
        cached_releases = self.redis.get(key)

        if cached_releases is not None:
            return loads(cached_releases)

        try:
            computed_releases = super(CachedRemoteIndex, self).get_available_releases(name)
        except HTTPException as error:
            if error.code == codes.not_found:
                # Cache negative
                self.redis.setex(key, dumps({}), self.releases_ttl)
            raise
        else:
            self.redis.setex(key, dumps(computed_releases), self.releases_ttl)

        return computed_releases

    def get_release(self, path, local):
        """
        Adds pip "download cache" style caching to content data and content type.
        """
        key = quote(make_absolute_url(self.index_url, path), "")

        content_file = join(self.cache_dir, key)
        content_type_file = join(self.cache_dir, key + ".content-type")

        # Check cache
        if exists(content_file) and exists(content_type_file):
            with open(content_file) as content, open(content_type_file) as content_type:
                return content.read(), content_type.read()

        content_data, content_type = super(CachedRemoteIndex, self).get_release(path, local)

        # Write to cache
        with open(content_file, "wb") as content_file_, open(content_type_file, "w") as content_type_file_:
            content_file_.write(content_data)
            content_type_file_.write(content_type)

        return content_data, content_type


def get_absolute_path(url, path):
    """
    Given a URL and a relative path, compute the URL's absolute path.
    """
    url_parts = list(urlsplit(url))
    return abspath(join(url_parts[2], path))


def make_absolute_url(url, path):
    """
    Given a URL and an absolute path, construct a new URL with the new path.
    """
    url_parts = list(urlsplit(url))
    return urlunsplit(url_parts[:2] + [path] + url_parts[3:])
