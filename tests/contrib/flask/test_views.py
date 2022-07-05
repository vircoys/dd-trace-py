from flask.views import MethodView
from flask.views import View

from ddtrace.contrib.flask.patch import flask_version
from ddtrace.internal.compat import PY2
from tests.utils import snapshot

from . import BaseFlaskTestCase


base_exception_name = "builtins.Exception"
if PY2:
    base_exception_name = "exceptions.Exception"


class FlaskViewTestCase(BaseFlaskTestCase):
    @snapshot(ignores=["meta.flask.version"], variants={"1_0": flask_version < (1, 1), "": flask_version >= (1, 1)})
    def test_view_handler(self):
        """
        When using a flask.views.View
            We create spans as expected
        """

        class TestView(View):
            methods = ["GET"]

            def dispatch_request(self, name):
                return "Hello {}".format(name)

        self.app.add_url_rule("/hello/<name>", view_func=TestView.as_view("hello"))

        res = self.client.get("/hello/flask")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, b"Hello flask")

    @snapshot(
        ignores=["meta.flask.version", "meta.error.stack"],
        variants={"1_0": flask_version < (1, 1), "": flask_version >= (1, 1)},
    )
    def test_view_handler_error(self):
        """
        When using a flask.views.View
            When it raises an exception
                We create spans as expected
        """

        class TestView(View):
            methods = ["GET"]

            def dispatch_request(self, name):
                raise Exception("an error")

        self.app.add_url_rule("/hello/<name>", view_func=TestView.as_view("hello"))

        res = self.client.get("/hello/flask")
        self.assertEqual(res.status_code, 500)

    @snapshot(ignores=["meta.flask.version"], variants={"1_0": flask_version < (1, 1), "": flask_version >= (1, 1)})
    def test_method_view_handler(self):
        """
        When using a flask.views.MethodView
            We create spans as expected
        """

        class TestView(MethodView):
            def get(self, name):
                return "Hello {}".format(name)

        self.app.add_url_rule("/hello/<name>", view_func=TestView.as_view("hello"))

        res = self.client.get("/hello/flask")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, b"Hello flask")

    @snapshot(
        ignores=["meta.flask.version", "meta.error.stack"],
        variants={"1_0": flask_version < (1, 1), "": flask_version >= (1, 1)},
    )
    def test_method_view_handler_error(self):
        """
        When using a flask.views.View
            When it raises an exception
                We create spans as expected
        """

        class TestView(MethodView):
            def get(self, name):
                raise Exception("an error")

        self.app.add_url_rule("/hello/<name>", view_func=TestView.as_view("hello"))

        res = self.client.get("/hello/flask")
        self.assertEqual(res.status_code, 500)
