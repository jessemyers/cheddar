"""
Version and metadata utilities.
"""
from pkg_resources import parse_version

from pkginfo import SDist


def read_metadata(path):
    """
    Extract package metadata from source distribution.

    :param path: path to source distribution
    :returns: dict of meta data
    """
    distribution = SDist(path)
    return {key: getattr(distribution, key) for key in distribution.iterkeys()}


def sort_key(basename):
    """
    Define a sort key suitable for use in `sorted`
    that leverages the parsed version.
    """
    _, version = guess_name_and_version(basename)
    return parse_version(version)


def guess_name_and_version(basename):
    """
    Guess the distribution's name and version from its filename.
    """
    rest = basename
    for extension in [".tar.gz", ".zip"]:
        if rest.endswith(extension):
            rest = rest[:- len(extension)]
    return rest.split("-", 1)


def is_pre_release(basename):
    """
    Determine whether the version is a pre-release.
    """
    parsed_version = sort_key(basename)

    # check if the parsed version contains a non-numeric component
    #
    # 1.0.dev1 -> ('00000001', '00000000', '*@', '00000001', '*final')
    # 1.0c1    -> ('00000001', '00000000', '*c', '00000001', '*final')
    # 1.0      -> ('00000001', '00000000', '*final')
    # 1.0.1    -> ('00000001', '00000000', '00000001', '*final')
    try:
        [int(part) for part in parsed_version if part != "*final"]
        return False
    except ValueError:
        return True
