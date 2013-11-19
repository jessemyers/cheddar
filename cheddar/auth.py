"""
Authentication.
"""
from flask import request


def check_authentication(redis):
    """
    Authenticate a request using a Redis lookup.
    """
    if request.authorization is None:
        return False

    key = "cheddar.user.{}".format(request.authorization.username)
    expected = redis.get(key)
    return expected is not None and expected == request.authorization.password
