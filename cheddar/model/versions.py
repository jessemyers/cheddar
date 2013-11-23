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

    for bad_extension in [".exe"]:
        if rest.endswith(bad_extension):
            # bad extension
            raise ValueError("Expected basename to have a valid package extension.")

    for extension in [".tar.gz", ".zip"]:
        if rest.endswith(extension):
            rest = rest[:- len(extension)]
            break

    name, version = rest.split("-", 1)
    if version[0].isdigit():
        # first split left
        return name, version
    else:
        # otherwise split right
        return rest.rsplit("-", 1)


def name_match(this, that):
    """
    Do two package names match?
    """
    def _normalize(name):
        return name.replace("_", "-").lower()

    return _normalize(this) == _normalize(that)


def is_pre_release(basename):
    """
    Determine whether the version is a pre-release.

    The existence of "patch levels" and other exotic versions make version analysis trick.
    PEP386's version improvements are also impractical because PyPi has to deal with actual
    versions seen in the wild...

    See: http://pythonhosted.org/setuptools/pkg_resources.html#parsing-utilities
    """
    parsed_version = sort_key(basename)

    def is_patch(part):
        # the tailing "-" is important here
        return part == "*final-"

    # strip out patch levels indicator and their successive qualifier
    parts = [part for index, part in enumerate(parsed_version)
             if not is_patch(part) and (index == 0 or not is_patch(parsed_version[index - 1]))]

    # check if the parsed version contains a non-numeric component
    #
    # 1.0.dev1 -> ('00000001', '00000000', '*@', '00000001', '*final')
    # 1.0c1    -> ('00000001', '00000000', '*c', '00000001', '*final')
    # 1.0      -> ('00000001', '00000000', '*final')
    # 1.0.1    -> ('00000001', '00000000', '00000001', '*final')
    try:
        [int(part) for part in parts if part != "*final"]
        return False
    except ValueError:
        return True
