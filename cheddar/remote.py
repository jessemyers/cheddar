"""
Implements a remote (proxy) package index.
"""
from json import dumps, loads
from os.path import abspath, join
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
        self.logger = app.logger

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
        self.logger.info("Getting available remote releases")

        url = "{}/{}".format(self.index_url, name)
        response = get(url, timeout=self.get_timeout)
        if response.status_code != codes.ok:
            self.logger.info("Available remote releases not found")
            self.logger.debug(codes.not_found)
            abort(codes.not_found)
        soup = BeautifulSoup(response.text)

        releases = {node.text: "remote" + get_absolute_path(self.index_url, node["href"]) for node in soup.findAll("a")}
        self.logger.debug(releases)
        return releases

    def get_release(self, path, local):
        """
        Request distribution data for path on the index server.
        """
        self.logger.info("Getting remote release")
        response = get(make_absolute_url(self.index_url, path), timeout=self.get_timeout)
        if response.status_code != codes.ok:
            self.logger.info("Release not found")
            self.logger.debug(codes.not_found)
            abort(codes.not_found)
        self.logger.debug(response.content)
        return response.content, response.headers["Content-Type"]

    def remove_release(self, name, version):
        """
        Unsupported.
        """
        pass


class CachedRemoteIndex(RemoteIndex):
    """
    Cache remote package data.

    - Since release data may change frequently, it is cached in Redis for simple expiration.
    - Distribution data is saved to the file system for easy inspection and backup.
    """
    def __init__(self, app):
        super(CachedRemoteIndex, self).__init__(app)
        self.redis = app.redis
        self.storage = app.remote_storage
        self.releases_ttl = app.config["RELEASES_TTL"]
        self.logger = app.logger

    def get_available_releases(self, name):
        """
        Adds redis caching to available releases data.

        Currently, does not implement negative caching.
        """
        self.logger.info("Getting available cached releases")
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
            self.logger.critical("error computing releases", exc_info=True)
            raise
        else:
            self.redis.setex(key, dumps(computed_releases), self.releases_ttl)
        self.logger.debug(computed_releases)
        return computed_releases

    def get_release(self, path, local):
        """
        Adds pip "download cache" style caching to content data and content type.
        """
        cached = self.storage.read(path)
        if cached is not None:
            return cached

        content_data, content_type = super(CachedRemoteIndex, self).get_release(path, local)
        self.storage.write(path, content_data)
        self.logger.debug("Remote releases list", content_data, content_type)
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
