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
    def register(self, **metadata):
        """
        Register a distribution.

        :param metadata: the distribution's metadata
        """
        pass

    @abstractmethod
    def upload(self, upload_file):
        """
        Upload a distribution.

        :param upload_file: the uploaded file
        """
        pass

    @abstractmethod
    def get_local_packages(self):
        """
        :returns: a list of locally available packages
        """
        pass

    @abstractmethod
    def get_available_releases(self, name):
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
