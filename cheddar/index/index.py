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
    def get_projects(self):
        """
        Get the list of hosted projects.

        :returns: an iterable of project names
        """
        pass

    @abstractmethod
    def get_versions(self, name):
        """
        Get the list of versions for a project.

        :param name: the project name
        :returns: a dictionary mapping versions to paths
        """
        pass

    @abstractmethod
    def get_metadata(self, name, version):
        """
        Get metadata for a project version.

        :param name: the project name
        :param version: the project version
        :returns: a dictionary of metadata
        """
        pass

    @abstractmethod
    def get_distribution(self, location, **kwargs):
        """
        Get distribution for a project version.

        :param location: location of the distribution content
        :returns: a pair of content data and content type for a distribution
        """
        pass

    @abstractmethod
    def remove_version(self, name, version):
        """
        Remove all data for a project version.

        :param name: the project name
        :param version: the project version
        """
        pass

    @abstractmethod
    def validate_metadata(metadata):
        """
        Validate a distribution's metadata.

        At a minimum, this function must verify that the project name and version
        are present in the dictionary. Other entries may be required as well.

        :param metadata: a dictionary of key-value metadata
        :returns: whether the metadata was valid
        """
        pass

    @abstractmethod
    def upload_distribution(self, upload_file):
        """
        Upload a distribution for a project version.

        The project name and version are determined from the metadata
        in the uploade_file contents.

        :param upload_file: an instance of `werkezeug.datastructures.FileStorage`
        """
        pass
