"""
Test version functions
"""
from os.path import dirname, join

from nose.tools import eq_

from cheddar.model.versions import (guess_name_and_version,
                                    is_pre_release,
                                    name_match,
                                    read_metadata,
                                    sort_key)


def test_parse_name_and_version():
    path = join(dirname(__file__), "../data/example-1.0.tar.gz")
    metadata = read_metadata(path)

    eq_(metadata,
        dict(author="Location Labs",
             author_email="info@locationlabs.com",
             description=None,
             home_page="http://www.locationlabs.com",
             keywords=None,
             license=None,
             metadata_version="1.0",
             name="example",
             platforms=["UNKNOWN"],
             summary="Example distribution",
             supported_platforms=(),
             version="1.0"))


def test_guess_name_and_version():

    def validate_guess(basename, expected_name, expected_version):
        name, version = guess_name_and_version(basename)
        eq_(name, expected_name)
        eq_(version, expected_version)

    cases = [("foo-1.0.tar.gz", "foo", "1.0"),
             ("foo-1.0c1.zip", "foo", "1.0c1"),
             ("foo-1.0.dev1", "foo", "1.0.dev1"),
             # hypenated names are a bad idea!
             ("foo-bar-1.0.tar.gz", "foo-bar", "1.0"),
             # weird versions extensions are also a bad idea (but may be required when forking)
             ("foo-1.0-bar.tar.gz", "foo", "1.0-bar")]
    for basename, expected_name, expected_version in cases:
        yield validate_guess, basename, expected_name, expected_version


def test_sort_key():
    versions = ["foo-1.1",
                "foo-1.0.1",
                "foo-1.0",
                "foo-1.0c1",
                "foo-1.0.dev10",
                "foo-1.0.dev9"]

    eq_(sorted(versions, key=sort_key),
        list(reversed(versions)))


def test_name_match():

    def validate_name_match(this, that, expected):
        eq_(name_match(this, that), expected)

    cases = [("foo", "Foo", True),
             ("foo", "bar", False),
             ("foo-bar", "foo_bar", True),
             ("foo-bar", "foobar", False),
             ]
    for this, that, expected in cases:
        yield validate_name_match, this, that, expected


def test_is_pre_release():

    def validate_is_pre_release(basename, expected):
        eq_(is_pre_release(basename), expected)

    cases = [("foo-1.1", False),
             ("foo-1.0.1", False),
             ("foo-1.0", False),
             ("foo-1.0a", True),
             ("foo-1.0b", True),
             ("foo-1.0c", True),
             ("foo-1.0c1", True),
             ("foo-1.0pre", True),
             ("foo-1.0preview", True),
             ("foo-1.0rc", True),
             ("foo-1.0.dev10", True),
             ("foo-1.0.dev9", True),
             ("foo-1.0-alpha", True),
             ("foo-1.0-beta", True),
             ("foo-1.0-c", True),
             ("foo-1.0-rc1", True),
             ("foo-1.0-dev", True),
             ("foo-1.0-xx", False),
             ("foo-1.0-xx.dev1", True),
             ("foo-1.0-1", False)]
    for basename, expected in cases:
        yield validate_is_pre_release, basename, expected
