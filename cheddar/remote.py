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
from cheddar.versions import guess_name_and_version


class RemoteIndex(Index):
    """
    Access package data through a remote index server (e.g. pypi.python.org)
    """
    def __init__(self, app):
        self.index_url = app.config["INDEX_URL"]
        self.get_timeout = app.config["GET_TIMEOUT"]
        self.logger = app.logger

    def register(self, **metadata):
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
        self.logger.info("Getting remote releases listing for: {}".format(name))

        url = "{}/{}".format(self.index_url, name)
        response = get(url, timeout=self.get_timeout)
        if response.status_code != codes.ok:
            self.logger.info("Remote releases listing not found: {}".format(response.status_code))
            abort(codes.not_found)

        releases = {name: "remote{}".format(path) for name, path in self._iter_release_links(response.text)}

        self.logger.debug("Obtained remote releases listing for: {}: {}".format(name, releases))
        return releases

    def get_release(self, path, local):
        """
        Request distribution data for path on the index server.
        """
        self.logger.info("Getting remote release: {}".format(path))

        response = get(make_absolute_url(self.index_url, path), timeout=self.get_timeout)
        if response.status_code != codes.ok:
            self.logger.info("Release not found for: {}: {}".format(path, response.status_code))
            abort(codes.not_found)

        # don't log binary release content (.tar.gz, .zip, etc.), even at debug
        return response.content, response.headers["Content-Type"]

    def remove_release(self, name, version):
        """
        Unsupported.
        """
        pass

    def _iter_release_links(self, html):
        """
        Iterate through release links (in order), filtering out links that
        don't "look" like releases.
        """
        soup = BeautifulSoup(html)
        for node in soup.findAll("a"):
            try:
                name, version = guess_name_and_version(node.text)
            except ValueError:
                # couldn't parse name and version, probably the wrong kind of link
                continue
            yield node.text, get_absolute_path(self.index_url, node["href"])


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
        self.logger.info("Getting available cached releases for: {}".format(name))
        key = "cheddar.remote.{}".format(name)

        # Check cache
        cached_releases = self.redis.get(key)

        if cached_releases is not None:
            self.logger.debug("Found cached releases for: {}".format(name))
            return loads(cached_releases)

        try:
            computed_releases = super(CachedRemoteIndex, self).get_available_releases(name)
        except HTTPException as error:
            if error.code == codes.not_found:
                # Cache negative
                self.logger.debug("Caching negative releases listing for: {}".format(name))
                self.redis.setex(key, time=int(self.releases_ttl), value=dumps({}))
            else:
                self.logger.warn("Unexpected error querying remote releases", exc_info=True)
            raise
        else:
            self.logger.debug("Caching positive releases listing for: {}".format(name))
            self.redis.setex(key, time=int(self.releases_ttl), value=dumps(computed_releases))
        self.logger.debug(computed_releases)
        return computed_releases

    def get_release(self, path, local):
        """
        Cache content data.
        """
        cached = self.storage.read(path)
        if cached is not None:
            self.logger.debug("Found cached release for: {}".format(path))
            return cached

        content_data, content_type = super(CachedRemoteIndex, self).get_release(path, local)

        self.logger.debug("Caching release for: {}".format(path))
        self.storage.write(path, content_data)

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
