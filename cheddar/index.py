"""
Abstraction around a package index.
"""
from abc import ABCMeta, abstractmethod


class Index(object):
    """
    Abstract interface for managing PyPI data.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def validate_metadata(self, **metadata):
        """
        Validate a distribution's metadata.

        :param metadata: the distribution's metadata
        :returns: whether the metadata was valid
        """
        pass

    @abstractmethod
    def upload_distribution(self, upload_file):
        """
        Upload a distribution.

        :param upload_file: an instance of `werkezeug.datastructures.FileStorage`
        """
        pass

    @abstractmethod
    def get_packages(self):
        """
        Get the list of locally available packages.

        :returns: an iterable of package names
        """
        pass

    @abstractmethod
    def get_releases(self, name):
        """
        :param name: the distribution name
        :returns: a dictionary mapping releases to paths
        """
        pass

    @abstractmethod
    def get_release(self, path, local):
        """
        :param path: location of the release content
        :returns: a pair of content data and content type for a release
        """
        pass

    @abstractmethod
    def remove_release(self, name, version):
        """
        :param name: the distribution name
        :param version: the distribution version
        :returns: a pair of content data and content type for a release
        """
        pass
