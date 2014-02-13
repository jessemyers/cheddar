"""
Implements a remote (proxy) package index.
"""
from json import dumps, loads
from os.path import abspath, basename, join
from urllib import quote
from urlparse import urlsplit, urlunsplit

from BeautifulSoup import BeautifulSoup
from requests import codes, ConnectionError, get, Timeout

from cheddar.exceptions import NotFoundError
from cheddar.index.index import Index
from cheddar.model.versions import guess_name_and_version


class RemoteIndex(Index):
    """
    Access package data through a remote index server (e.g. pypi.python.org)
    """

    MAX_DEPTH = 2

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
        url = "{}/{}".format(self.index_url, name)

        versions = {name: build_remote_path(href, location)
                    for name, href, location in self._iter_listings(url, name)}

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

        response = fetch_url(location, self.get_timeout, self.logger)

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

    def _iter_listings(self, url, name, depth=0):
        """
        Iterate through remote listings.

        Interpret version links and either yield (name, href, location) tuples
        or recursively spider to new links.
        """
        self.logger.info("Getting remote version listing for: {}".format(name))

        response = fetch_url(url, self.get_timeout, self.logger)

        # Record the actual hostname used in case of redirection
        location = get_request_location(response, url)
        self.logger.debug("Index location was: {}".format(location))

        for link in iter_version_links(response.text, name):
            if isinstance(link, tuple):
                # Direct link
                name, href = link
                yield name, href, location
            else:
                # Recursive link
                if depth <= RemoteIndex.MAX_DEPTH:
                    try:
                        self.logger.info("Spidering to: {}".format(link))
                        for listing in self._iter_listings(link, name, depth + 1):
                            yield listing
                    except NotFoundError:
                        self.logger.debug("Unable to spider to: {}".format(link))
                else:
                    self.logger.info("Reached max depth; aborted spidering to: {}".format(link))


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
        self.versions_short_ttl = app.config["VERSIONS_SHORT_TTL"]
        self.versions_long_ttl = app.config["VERSIONS_LONG_TTL"]
        self.logger = app.logger

    def _key(self, name):
        return "cheddar.remote.{}".format(name)

    def _is_expired(self, ttl):
        """
        Is a cached index with a given ttl expired?
        """
        if ttl == -1:
            # no expiration
            return False
        if ttl == -2:
            # no key; let's call that "not expired"
            return False
        age = max(0, self.versions_long_ttl - ttl)
        return age >= self.versions_short_ttl

    def _get_cached_index(self, name):
        """
        Get the cached values of a distribution.

        :returns: a tuple of the cached value and whether it was expired
        """
        versions = self.redis.get(self._key(name))
        if versions is None:
            # not cached
            self.logger.debug("Cached index for: {} was not found".format(name))
            return None, False

        ttl = self.redis.ttl(self._key(name))
        self.logger.debug("Cached index for: {} has a ttl of: {}".format(name, ttl))
        expired = self._is_expired(ttl)
        self.logger.debug("Cached index for: {} was expired: {}".format(name, expired))

        return loads(versions), expired

    def _save_negative_index(self, name):
        """
        Save a negative result in the cache.

        Caching a negative result ensures that we don't keep querying the remote
        index for something that truly does not exist.
        """
        self.logger.debug("Caching negative versions listing for: {}".format(name))
        self.redis.setex(self._key(name), time=int(self.versions_long_ttl), value=dumps({}))

    def _save_index(self, name, versions):
        self.logger.debug("Caching positive versions listing for: {}".format(name))
        self.redis.setex(self._key(name), time=int(self.versions_long_ttl), value=dumps(versions))

    def get_versions(self, name):
        """
        Adds redis caching to versions listing.

        Currently, does not implement negative caching.
        """
        self.logger.info("Checking for cached versions listing for: {}".format(name))

        # check cache
        cached_versions, cached_expired = self._get_cached_index(name)

        # is it cached and recent enough?
        if cached_versions is not None and not cached_expired:
            # yes, return it
            self.logger.debug("Found cached versions listing for: {}".format(name))
            return cached_versions

        # need to refresh
        try:
            computed_versions = super(CachedRemoteIndex, self).get_versions(name)
        except NotFoundError as error:
            if error.status_code == codes.not_found:
                # no value
                self._save_negative_index(name)
                raise
            elif cached_versions is None:
                # no cached value
                raise
            else:
                # fall back to cached value
                self.logger.debug("Returning expired cached versions: {}".format(cached_versions))
                return cached_versions
        else:
            # found
            self._save_index(name, computed_versions)
            self.logger.debug("Returning new versions: {}".format(computed_versions))
            return computed_versions

    def get_distribution(self, location, **kwargs):
        """
        Cache distribution data.
        """
        cached = self.storage.read(location)
        if cached is not None:
            self.logger.debug("Found cached distribution for: {}".format(location))
            return cached

        content_data, content_type = super(CachedRemoteIndex, self).get_distribution(location,
                                                                                     **kwargs)

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


def build_remote_path(href, location):
    """
    Embed the index location into the link. If there was an #md5= fragment, it must
    come after the query string, so a little bit of gymnastics happens here.
    """
    if has_scheme(href):
        path = get_absolute_path(href, "")
        base_url = get_base_url(href)
    else:
        path = get_absolute_path(location, href)
        base_url = get_base_url(location)

    if "#" in path:
        base, fragment = path.split("#", 1)
        return "/remote{}?base={}#{}".format(base, quote(base_url, ""), fragment)
    else:
        return "/remote{}?base={}".format(path, quote(base_url, ""))


def has_scheme(url):
    """
    Does the input have a URL scheme?
    """
    try:
        url_parts = urlsplit(url)
        return bool(url_parts.scheme)
    except:
        return False


def iter_version_links(html, name):
    """
    Iterate through version links (in order) within HTML.

    Filtering out links that don't "look" like versions.

    Either yields hrefs to be recursively searches or tuples of (name, href)
    that match the given name.
    """
    soup = BeautifulSoup(html)
    for node in soup.findAll("a"):
        if node.get("href") is None:
            continue
        try:
            guessed_name, _ = guess_name_and_version(node.text)
        except ValueError:
            href = node["href"]
            for extension in [".tar.gz", ".zip"]:
                if href.endswith(extension):
                    yield basename(href), href
                    break
            else:
                if node.get("rel") == "download":
                    # Might be a recursive link.
                    yield href
            # else couldn't parse name and version, probably the wrong kind of link
        else:
            if guessed_name.replace("_", "-").lower() != name.replace("_", "-").lower():
                continue
            yield node.text, node["href"]


def fetch_url(url, timeout, logger):
    """
    Get a URL, handling timeouts and connection errors.

    :raises: NotFoundError: if get fails to return 200
    """
    try:
        response = get(url, timeout=timeout)
    except Timeout:
        logger.info("Timed out getting url: {}".format(url))
        raise NotFoundError()
    except ConnectionError:
        logger.info("Unable to connect to url: {}".format(url))
        raise NotFoundError()

    if response.status_code != codes.ok:
        logger.info("Unexpected status code: {} getting url: {}".format(response.status_code, url))
        raise NotFoundError(response.status_code)

    return response
