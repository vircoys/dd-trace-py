# -*- coding: utf-8 -*-
import json

from flask import abort
from flask import jsonify
from flask import make_response

from ddtrace.contrib.flask.patch import flask_version
from ddtrace.internal.compat import PY2
from ddtrace.propagation._utils import get_wsgi_header
from ddtrace.propagation.http import HTTP_HEADER_PARENT_ID
from ddtrace.propagation.http import HTTP_HEADER_TRACE_ID
from tests.utils import snapshot

from . import BaseFlaskTestCase


base_exception_name = "builtins.Exception"
if PY2:
    base_exception_name = "exceptions.Exception"


class FlaskRequestTestCase(BaseFlaskTestCase):
    @snapshot(ignores=["meta.flask.version"])
    def test_request(self):
        """
        When making a request
            We create the expected spans
        """

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_route_params_request(self):
        """
        When making a request to an endpoint with non-string url params
            We create the expected spans
        """

        @self.app.route("/route_params/<first>/<int:second>/<float:third>/<path:fourth>")
        def route_params(first, second, third, fourth):
            return jsonify(
                {
                    "first": first,
                    "second": second,
                    "third": third,
                    "fourth": fourth,
                }
            )

        res = self.client.get("/route_params/test/100/5.5/some/sub/path")
        self.assertEqual(res.status_code, 200)
        if isinstance(res.data, bytes):
            data = json.loads(res.data.decode())
        else:
            data = json.loads(res.data)

        assert data == {
            "first": "test",
            "second": 100,
            "third": 5.5,
            "fourth": "some/sub/path",
        }

    @snapshot(ignores=["meta.flask.version"])
    def test_request_query_string_trace(self):
        """Make sure when making a request that we create the expected spans and capture the query string."""

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        with self.override_http_config("flask", dict(trace_query_string=True)):
            self.client.get("/?foo=bar&baz=biz")

    @snapshot(
        ignores=[
            "meta.flask.version",
        ]
    )
    def test_request_query_string_trace_encoding(self):
        """Make sure when making a request that we create the expected spans and capture the query string with a non-UTF-8
        encoding.
        """

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        with self.override_http_config("flask", dict(trace_query_string=True)):
            self.client.get(u"/?foo=bar&baz=정상처리".encode("euc-kr"))

    @snapshot(ignores=["meta.flask.version"])
    def test_analytics_global_on_integration_default(self):
        """
        When making a request
            When an integration trace search is not event sample rate is not set and globally trace search is enabled
                We expect the root span to have the appropriate tag
        """

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        with self.override_global_config(dict(analytics_enabled=True)):
            res = self.client.get("/")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_analytics_global_on_integration_on(self):
        """
        When making a request
            When an integration trace search is enabled and sample rate is set and globally trace search is enabled
                We expect the root span to have the appropriate tag
        """

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        with self.override_global_config(dict(analytics_enabled=True)):
            with self.override_config("flask", dict(analytics_enabled=True, analytics_sample_rate=0.5)):
                res = self.client.get("/")
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_analytics_global_off_integration_default(self):
        """
        When making a request
            When an integration trace search is not set and sample rate is set and globally trace search is disabled
                We expect the root span to not include tag
        """

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        with self.override_global_config(dict(analytics_enabled=False)):
            res = self.client.get("/")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_analytics_global_off_integration_on(self):
        """
        When making a request
            When an integration trace search is enabled and sample rate is set and globally trace search is disabled
                We expect the root span to have the appropriate tag
        """

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        with self.override_global_config(dict(analytics_enabled=False)):
            with self.override_config("flask", dict(analytics_enabled=True, analytics_sample_rate=0.5)):
                res = self.client.get("/")
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_distributed_tracing(self):
        """
        When making a request
            When distributed tracing headers are present
                We create the expected spans
        """

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        # Default: distributed tracing enabled
        res = self.client.get(
            "/",
            headers={
                get_wsgi_header(HTTP_HEADER_PARENT_ID): "0",
                get_wsgi_header(HTTP_HEADER_TRACE_ID): "678910",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, b"Hello Flask")

        # Explicitly enable distributed tracing
        with self.override_config("flask", dict(distributed_tracing_enabled=True)):
            res = self.client.get(
                "/",
                headers={
                    get_wsgi_header(HTTP_HEADER_PARENT_ID): "0",
                    get_wsgi_header(HTTP_HEADER_TRACE_ID): "678910",
                },
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data, b"Hello Flask")

        # With distributed tracing disabled
        with self.override_config("flask", dict(distributed_tracing_enabled=False)):
            res = self.client.get(
                "/",
                headers={
                    get_wsgi_header(HTTP_HEADER_PARENT_ID): "0",
                    get_wsgi_header(HTTP_HEADER_TRACE_ID): "678910",
                },
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_request_query_string(self):
        """
        When making a request
            When the request contains a query string
                We create the expected spans
        """

        @self.app.route("/")
        def index():
            return "Hello Flask", 200

        res = self.client.get("/", query_string=dict(hello="flask"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, b"Hello Flask")

    @snapshot(ignores=["meta.flask.version"])
    def test_request_unicode(self):
        """
        When making a request
            When the url contains unicode
                We create the expected spans
        """

        @self.app.route(u"/üŋïĉóđē")
        def unicode():
            return "üŋïĉóđē", 200

        res = self.client.get(u"/üŋïĉóđē")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, b"\xc3\xbc\xc5\x8b\xc3\xaf\xc4\x89\xc3\xb3\xc4\x91\xc4\x93")

    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_request_404(self):
        """
        When making a request
            When the requested endpoint was not found
                We create the expected spans
        """
        res = self.client.get("/not-found")
        self.assertEqual(res.status_code, 404)

    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_request_abort_404(self):
        """
        When making a request
            When the requested endpoint calls `abort(404)`
                We create the expected spans
        """

        @self.app.route("/not-found")
        def not_found():
            abort(404)

        res = self.client.get("/not-found")
        self.assertEqual(res.status_code, 404)

    @snapshot(
        ignores=["meta.flask.version", "meta.error.stack"],
        variants={"1-0": flask_version < (1, 1), "": flask_version >= (1, 1)},
    )
    def test_request_500(self):
        """
        When making a request
            When the requested endpoint raises an exception
                We create the expected spans
        """

        @self.app.route("/500")
        def fivehundred():
            raise Exception("500 error")

        res = self.client.get("/500")
        self.assertEqual(res.status_code, 500)

    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_request_501(self):
        """
        When making a request
            When the requested endpoint calls `abort(501)`
                We create the expected spans
        """

        @self.app.route("/501")
        def fivehundredone():
            abort(501)

        res = self.client.get("/501")
        self.assertEqual(res.status_code, 501)

    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_request_error_handler(self):
        """
        When making a request
            When the requested endpoint raises an exception
                We create the expected spans
        """

        @self.app.errorhandler(500)
        def error_handler(e):
            return "Whoops", 500

        @self.app.route("/500")
        def fivehundred():
            raise Exception("500 error")

        res = self.client.get("/500")
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.data, b"Whoops")

    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_http_request_header_tracing(self):
        with self.override_http_config("flask", dict(trace_headers=["Host", "my-header"])):
            self.client.get(
                "/",
                headers={
                    "my-header": "my_value",
                },
            )

    @snapshot(
        ignores=["meta.flask.version", "meta.error.stack"],
        variants={"1-0": flask_version < (1, 1), "": flask_version >= (1, 1)},
    )
    def test_correct_resource_when_middleware_error(self):
        @self.app.route("/helloworld")
        @self.app.before_first_request
        def error():
            raise Exception()

        self.client.get("/helloworld")

    @snapshot(ignores=["meta.flask.version"])
    def test_http_response_header_tracing(self):
        @self.app.route("/response_headers")
        def response_headers():
            resp = make_response("Hello Flask")
            resp.headers["my-response-header"] = "my_response_value"
            return resp

        with self.override_http_config("flask", dict(trace_headers=["my-response-header"])):
            self.client.get("/response_headers")
