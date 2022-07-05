from flask import Blueprint

from tests.utils import snapshot

from . import BaseFlaskTestCase


class FlaskHookTestCase(BaseFlaskTestCase):
    def setUp(self):
        super(FlaskHookTestCase, self).setUp()

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        self.bp = Blueprint("bp", __name__)

        @self.bp.route("/bp")
        def bp():
            return "Hello Blueprint", 200

    @snapshot(ignores=["meta.flask.version"])
    def test_before_request(self):
        """
        When Flask before_request hook is registered
            We create the expected spans
        """

        @self.app.before_request
        def before_request():
            pass

        req = self.client.get("/")
        assert req.status_code == 200
        assert req.data == b"Hello Flask"

    @snapshot(ignores=["meta.flask.version"])
    def test_before_request_return(self):
        """
        When Flask before_request hook is registered
            When the hook handles the request
                We create the expected spans
        """

        @self.app.before_request
        def before_request():
            return "Not Allowed", 401

        req = self.client.get("/")
        assert req.status_code == 401
        assert req.data == b"Not Allowed"

    @snapshot(ignores=["meta.flask.version"])
    def test_before_first_request(self):
        """
        When Flask before_first_request hook is registered
            We create the expected spans
        """

        @self.app.before_first_request
        def before_first_request():
            pass

        req = self.client.get("/")
        assert req.status_code == 200
        assert req.data == b"Hello Flask"

    @snapshot(ignores=["meta.flask.version"])
    def test_after_request(self):
        """
        When Flask after_request hook is registered
            We create the expected spans
        """

        @self.app.after_request
        def after_request(response):
            return response

        req = self.client.get("/")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_after_request_change_status(self):
        """
        When Flask after_request hook is registered
            We create the expected spans
        """

        @self.app.after_request
        def after_request(response):
            response.status_code = 401
            return response

        req = self.client.get("/")
        self.assertEqual(req.status_code, 401)
        self.assertEqual(req.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_teardown_request(self):
        """
        When Flask teardown_request hook is registered
            We create the expected spans
        """

        @self.app.teardown_request
        def teardown_request(request):
            pass

        req = self.client.get("/")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_teardown_appcontext(self):
        """
        When Flask teardown_appcontext hook is registered
            We create the expected spans
        """

        @self.app.teardown_appcontext
        def teardown_appcontext(appctx):
            pass

        req = self.client.get("/")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_bp_before_request(self):
        """
        When Blueprint before_request hook is registered
            We create the expected spans
        """

        @self.bp.before_request
        def bp_before_request():
            pass

        self.app.register_blueprint(self.bp)
        req = self.client.get("/bp")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Blueprint")

    @snapshot(ignores=["meta.flask.version"])
    def test_bp_before_app_request(self):
        """
        When Blueprint before_app_request hook is registered
            We create the expected spans
        """

        @self.bp.before_app_request
        def bp_before_app_request():
            pass

        self.app.register_blueprint(self.bp)
        req = self.client.get("/")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_before_app_first_request(self):
        """
        When Blueprint before_first_request hook is registered
            We create the expected spans
        """

        @self.bp.before_app_first_request
        def bp_before_app_first_request():
            pass

        self.app.register_blueprint(self.bp)
        req = self.client.get("/")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_bp_after_request(self):
        """
        When Blueprint after_request hook is registered
            We create the expected spans
        """

        @self.bp.after_request
        def bp_after_request(response):
            return response

        self.app.register_blueprint(self.bp)
        req = self.client.get("/bp")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Blueprint")

    @snapshot(ignores=["meta.flask.version"])
    def test_bp_after_app_request(self):
        """
        When Blueprint after_app_request hook is registered
            We create the expected spans
        """

        @self.bp.after_app_request
        def bp_after_app_request(response):
            return response

        self.app.register_blueprint(self.bp)
        req = self.client.get("/")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_bp_teardown_request(self):
        """
        When Blueprint teardown_request hook is registered
            We create the expected spans
        """

        @self.bp.teardown_request
        def bp_teardown_request(request):
            pass

        self.app.register_blueprint(self.bp)
        req = self.client.get("/bp")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Blueprint")

    @snapshot(ignores=["meta.flask.version"])
    def test_bp_teardown_app_request(self):
        """
        When Blueprint teardown_app_request hook is registered
            We create the expected spans
        """

        @self.bp.teardown_app_request
        def bp_teardown_app_request(request):
            pass

        self.app.register_blueprint(self.bp)
        req = self.client.get("/")
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.data, b"Hello Flask")
