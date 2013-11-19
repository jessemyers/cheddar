"""
URL mappings for package index functionality.
"""
from collections import OrderedDict
from functools import wraps
from urlparse import urljoin

from flask import abort, jsonify, make_response, render_template, request

from cheddar.auth import check_authentication
from cheddar.model.versions import sort_key


def create_routes(app):

    def authenticated(func):
        """
        Basic Auth decorator.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not check_authentication(app.redis):
                response = make_response("", 401)
                response.headers["WWW-Authenticate"] = 'Basic realm="cheddar"'
                return response
            return func(*args, **kwargs)
        return wrapper

    @app.route("/")
    def index():
        """
        Index page.
        """
        app.logger.debug("Showing index page")
        return _render("index.html")

    @app.route("/simple/")
    @app.route("/simple")
    def list_project():
        """
        List all hosted projects.
        """
        app.logger.debug("Showing all projects")

        projects = sorted([project.name for project in app.index.get_projects()])

        return _render("simple.html", projects=projects)

    @app.route("/simple/<name>/")
    @app.route("/simple/<name>")
    def get_project(name):
        """
        List versions for a hosted project.
        """
        app.logger.info("Showing package index for: {}".format(name))

        versions = app.index.get_versions(name)

        if not versions:
            abort(404)

        sorted_versions = OrderedDict()
        for version in sorted(versions.keys(), key=sort_key):
            sorted_versions[version] = versions[version]

        return _render("project.html", project=name, versions=sorted_versions)

    @app.route("/simple/<name>/<version>/", methods=["GET", "DELETE"])
    @app.route("/simple/<name>/<version>", methods=["GET", "DELETE"])
    def handle_version(name, version):
        if request.method == "DELETE":
            return remove_version(name, version)
        else:
            return get_version(name, version)

    def get_version(name, version):
        """
        Get metadata for version.
        """
        app.logger.debug("Getting: {} {}".format(name, version))

        metadata = app.index.get_metadata(name, version)

        if metadata is None:
            abort(404)

        return _render("version.html", project=name, version=version, metadata=metadata)

    @authenticated
    def remove_version(name, version):
        """
        Delete all version data. Requires auth.
        """
        app.logger.debug("Removing: {} {}".format(name, version))
        app.index.remove_version(name, version)
        return ""

    @app.route("/local/<path:location>/")
    @app.route("/local/<path:location>")
    def get_local_distribution(location):
        """
        Local distribution download access.
        """
        app.logger.debug("Getting local distribution: {}".format(location))
        content_data, content_type = app.index.get_distribution(location, local=True)
        response = make_response(content_data)
        response.headers['Content-Type'] = content_type
        return response

    @app.route("/remote/<path:path>/")
    @app.route("/remote/<path:path>")
    def get_remote_distribution(path):
        """
        Remote distribution download access.

        Proxies and caches content.
        """
        # To account for redirects, we need to save the base url in the link URL along
        # with the path to the distribution. It's still a little awkward because the
        # urljoin logic happens here instead of within the remote index.
        location = urljoin(request.args["base"], path)

        app.logger.debug("Getting remote distribution: {}".format(location))
        content_data, content_type = app.index.get_distribution(location, local=False)
        response = make_response(content_data)
        response.headers['Content-Type'] = content_type
        return response

    @app.route("/pypi/", methods=["POST"])
    @app.route("/pypi", methods=["POST"])
    def pypi():
        """
        Register and upload endpoint for pip.
        """
        if request.files:
            return upload()
        else:
            return register()

    @authenticated
    def upload():
        """
        Upload a distribution. Requires auth.
        """
        app.logger.debug("Uploading distribution")

        _, upload_file = next(request.files.iterlists())
        app.index.upload_distribution(upload_file[0])

        return ""

    def register():
        """
        Register a distribution.

        The correct behavior for the `setuptools` register command is somewhat
        vague. The PEP 301 docs (for `distutils`) mostly cover user management,
        whereas `setuptools` CLI help says "register the distribution with the
        Python package index."

        Given this ambiguity and the fact that register does *NOT* send auth
        credentials, this operation simply validates the provided metadata.
        """
        app.logger.debug("Registering distribution")

        metadata = {key: values[0] for key, values in request.form.iterlists()}
        if not app.index.validate_metadata(metadata):
            abort(400)

        return ""

    def _render(template, **data):
        """
        Render response as either a template or just the raw JSON data.
        """
        if _wants_json():
            return jsonify(data)
        else:
            return render_template(template, **data)

    def _wants_json():
        """
        Should response use JSON?
        """
        for mime_type, _ in request.accept_mimetypes:
            # If we see a mime type that means HTML before JSON, return False
            if mime_type.startswith("text/html"):
                return False
            elif mime_type.startswith("application/xhtml"):
                return False
            # If we see JSON explicitly, return True
            elif mime_type.startswith("application/json"):
                return True
        # Default to False (HTML)
        return False
