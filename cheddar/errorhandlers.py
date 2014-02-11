"""
Error handler registration.
"""
from requests import codes

from cheddar.exceptions import BadRequestError, ConflictError, NotFoundError


def create_errorhandlers(app):

    @app.errorhandler(BadRequestError)
    def bad_request(error):
        return error.message, codes.bad_request

    @app.errorhandler(ConflictError)
    def conflict(error):
        return error.message, codes.conflict

    @app.errorhandler(NotFoundError)
    def not_found(error):
        return error.message, codes.not_found
