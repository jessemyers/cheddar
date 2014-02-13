"""
Shared exception.
"""


class BadRequestError(Exception):
    pass


class ConflictError(Exception):
    pass


class NotFoundError(Exception):

    def __init__(self, status_code=None):
        self.status_code = status_code

