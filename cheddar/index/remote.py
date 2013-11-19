"""
Implements a remote (proxy) package index.
"""
from json import dumps, loads
from os.path import abspath, join
from urllib import quote
from urlparse import urlsplit, urlunsplit

from BeautifulSoup import BeautifulSoup
from flask import abort
from requests import codes, get
from werkzeug.exceptions import HTTPException

from cheddar.index.index import Index
from cheddar.model.versions import guess_name_and_version


class RemoteIndex(Index):
    """
    Access package data through a remote index server (e.g. pypi.python.org)
    """
    def __init__(self, app):
        self.index_url = app.config["INDEX_URL"]
        self.get_timeout = app.config["GET_TIMEOUT"]
        self.logger = app.logger

    def get_projects(self):
        """
        Unsupported.
        """
        raise NotImplementedError("get_projects")

    def get_versions(self, name):
        """
        Request version data from remote index and parse HTML.
        """
        self.logger.info("Getting remote version listing for: {}".format(name))

        url = "{}/{}".format(self.index_url, name)
        response = get(url, timeout=self.get_timeout)
        if response.status_code != codes.ok:
            self.logger.info("Remote version listing not found: {}".format(response.status_code))
            abort(codes.not_found)

        # Record the actual hostname used in case of redirection
        location = get_request_location(response, url)
        self.logger.debug("Index location was: {}".format(location))

        def build_remote_path(path, location):
            """
            Embed the index location into the link. If there was an #md5= fragment, it must
            come after the query string, so a little bit of gymnastics happens here.
            """
            if "#" in path:
                base, fragment = path.split("#", 1)
                return "/remote{}?base={}#{}".format(base, quote(get_base_url(location), ""), fragment)
            else:
                return "/remote{}?base={}".format(path, quote(get_base_url(location), ""))

        versions = {name: build_remote_path(path, location)
                    for name, path in self._iter_version_links(response.text, location)}

        self.logger.debug("Obtained remote version listing for: {}: {}".format(name, versions))
        return versions

    def get_metadata(self, name, version):
        """
        Unsupported.
        """
        pass

    def get_distribution(self, location, **kwargs):
        """
        Request distribution data for remote location.
        """
        self.logger.info("Getting remote distribution: {}".format(location))

        response = get(location, timeout=self.get_timeout)
        if response.status_code != codes.ok:
            self.logger.info("Distribution not found for: {}: {}".format(location, response.status_code))
            abort(codes.not_found)

        # don't log binary distribution content (.tar.gz, .zip, etc.), even at debug
        return response.content, response.headers["Content-Type"]

    def remove_version(self, name, version):
        """
        Unsupported.
        """
        raise NotImplementedError("remove_version")

    def validate_metadata(self, metadata):
        """
        Unsupported.
        """
        raise NotImplementedError("validate_metadata")

    def upload_distribution(self, file_):
        """
        Unsupported.
        """
        raise NotImplementedError("upload_distribution")

    def _iter_version_links(self, html, location):
        """
        Iterate through version links (in order), filtering out links that
        don't "look" like versions.
        """
        soup = BeautifulSoup(html)
        for node in soup.findAll("a"):
            try:
                name, version = guess_name_and_version(node.text)
            except ValueError:
                # couldn't parse name and version, probably the wrong kind of link
                continue
            yield node.text, get_absolute_path(location, node["href"])


class CachedRemoteIndex(RemoteIndex):
    """
    Cache remote package data.

    - Since version data may change frequently, it is cached in Redis for simple expiration.
    - Distribution files are saved to the file system for easy inspection and backup.
    """
    def __init__(self, app):
        super(CachedRemoteIndex, self).__init__(app)
        self.redis = app.redis
        self.storage = app.remote_storage
        self.versions_ttl = app.config["VERSIONS_TTL"]
        self.logger = app.logger

    def get_versions(self, name):
        """
        Adds redis caching to versions listing.

        Currently, does not implement negative caching.
        """
        self.logger.info("Checking for cached versions listing for: {}".format(name))
        key = "cheddar.remote.{}".format(name)

        # Check cache
        cached_versions = self.redis.get(key)

        if cached_versions is not None:
            self.logger.debug("Found cached versions listing for: {}".format(name))
            return loads(cached_versions)

        try:
            computed_versions = super(CachedRemoteIndex, self).get_versions(name)
        except HTTPException as error:
            if error.code == codes.not_found:
                # Cache negative
                self.logger.debug("Caching negative versions listing for: {}".format(name))
                self.redis.setex(key, time=int(self.versions_ttl), value=dumps({}))
            else:
                self.logger.warn("Unexpected error querying remote versions listing", exc_info=True)
            raise
        else:
            self.logger.debug("Caching positive versions listing for: {}".format(name))
            self.redis.setex(key, time=int(self.versions_ttl), value=dumps(computed_versions))

        self.logger.debug(computed_versions)
        return computed_versions

    def get_distribution(self, location, **kwargs):
        """
        Cache distribution data.
        """
        cached = self.storage.read(location)
        if cached is not None:
            self.logger.debug("Found cached distribution for: {}".format(location))
            return cached

        content_data, content_type = super(CachedRemoteIndex, self).get_distribution(location, **kwargs)

        self.logger.debug("Caching distribution for: {}".format(location))
        self.storage.write(location, content_data)

        return content_data, content_type


def get_absolute_path(url, path):
    """
    Given a URL and a relative path, compute the URL's absolute path.
    """
    url_parts = list(urlsplit(url))
    return abspath(join(url_parts[2], path))


def get_base_url(url):
    """
    Given a URL, strip everything except the protocol and hostname.
    """
    url_parts = list(urlsplit(url))
    return urlunsplit(url_parts[:2] + [""] * 3)


def get_request_location(response, url):
    """
    Extract the request location from an HTTP response.
    """
    url_parts = urlsplit(url)
    # parse the request url
    scheme, netloc, path = url_parts.scheme, url_parts.netloc, url_parts.path

    # walk the list of redirects and update the url parts
    for redirect in response.history or [response]:
        if "location" not in redirect.headers:
            continue
        redirect_parts = urlsplit(redirect.headers["location"])
        if redirect_parts.scheme:
            scheme = redirect_parts.scheme
        if redirect_parts.netloc:
            netloc = redirect_parts.netloc
        if redirect_parts.path:
            path = redirect_parts.path

    # reconstruct the url (minus query string and fragments)
    return urlunsplit([scheme, netloc, path] + [""] * 2)
