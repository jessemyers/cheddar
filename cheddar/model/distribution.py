"""
Distribution model manipulation functions.
"""
from json import dumps, loads


class Projects(object):
    """
    Collection of hosted projects.
    """

    def __init__(self, redis, logger, prefix=""):
        self.redis = redis
        self.logger = logger
        self.prefix = prefix
        self.key = "{}cheddar.local".format(self.prefix)

    def list_projects(self):
        """
        Get all hosted projects.
        """
        return [Project(self, name) for name in self.redis.smembers(self.key)]

    def get_project(self, name):
        """
        Get a hosted project.
        """
        if self.redis.sismember(self.key, name):
            return Project(self, name)
        return None

    def add_project(self, name):
        """
        Add a hosted projects.
        """
        self.redis.sadd(self.key, name)
        return Project(self, name)

    def remove_project(self, name):
        """
        Remove a hosted projects.
        """
        self.redis.srem(self.key, name)

    def get_metadata(self, name, version):
        project = self.get_project(name)
        if project is None:
            return None

        project_version = project.get_version(version)
        if project_version is None:
            return None

        return project_version.get_metadata()

    def add_metadata(self, metadata):
        """
        Add a project, a version, and metadata.
        """
        name, version = metadata["name"], metadata["version"]

        self.logger.debug("Saving distribution: {} {}".format(name, version))

        project = self.add_project(name)
        project_version = project.add_version(version)
        project_version.set_metadata(metadata)

    def remove_metadata(self, name, version):
        """
        Remove metadata, version, and (maybe) project.
        """
        # Here be race conditions...
        project = Project(self, name)
        project_version = Version(project, version)

        project_version.remove_metadata()
        project.remove_version(version)

        if project.num_versions() == 0:
            project.remove()
            self.remove_project(name)


class Project(object):
    """
    A single hosted project.
    """
    def __init__(self, projects, name):
        self.redis = projects.redis
        self.logger = projects.logger
        self.prefix = projects.prefix
        self.name = name
        self.key = "{}cheddar.local.{}".format(self.prefix, self.name)

    def get_versions(self):
        """
        Get all versions for the project.
        """
        return [Version(self, version) for version in self.redis.smembers(self.key)]

    def num_versions(self):
        """
        Get the number of versions for a project.
        """
        return self.redis.scard(self.key)

    def get_version(self, version):
        """
        Add a version to a project.
        """
        if self.redis.sismember(self.key, version):
            return Version(self, version)
        return None

    def add_version(self, version):
        """
        Add a version to a project.
        """
        self.redis.sadd(self.key, version)
        return Version(self, version)

    def remove_version(self, version):
        """
        Remove a version from a project.
        """
        self.redis.srem(self.key, version)

    def remove(self):
        """
        Remove a project.
        """
        self.redis.delete(self.key)


class Version(object):
    """
    A single hosted project version.
    """

    FILENAME = "_filename"

    def __init__(self, project, version):
        self.redis = project.redis
        self.logger = project.logger
        self.prefix = project.prefix
        self.name = project.name
        self.version = version
        self.key = "{}cheddar.local.{}-{}".format(self.prefix, self.name, self.version)

    def get_metadata(self):
        """
        Get the version's metadata.
        """
        raw_metadata = self.redis.get(self.key)

        if raw_metadata is None:
            self.logger.debug("No metadata found for: {} {}".format(self.name, self.version))
            return None

        metadata = loads(raw_metadata)

        if Version.FILENAME not in metadata:
            self.logger.debug("Incomplete metadata for: {} {}".format(self.name, self.version))
            return None

        return metadata

    def set_metadata(self, metadata):
        """
        Set the version's metadata.
        """
        self.logger.debug("Saving metadata: {} for: {} {}".format(metadata, self.name, self.version))
        self.redis.set(self.key, dumps(metadata))

    def remove_metadata(self):
        """
        Remove the version's metadata.
        """
        self.redis.delete(self.key)
