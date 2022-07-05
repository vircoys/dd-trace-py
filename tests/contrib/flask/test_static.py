from tests.utils import snapshot

from . import BaseFlaskTestCase


class FlaskStaticFileTestCase(BaseFlaskTestCase):
    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_serve_static_file(self):
        """
        When fetching a static file
            We create the expected spans
        """
        # DEV: By default a static handler for `./static/` is configured for us
        res = self.client.get("/static/test.txt")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, b"Hello Flask\n")

    @snapshot(ignores=["meta.flask.version", "meta.error.stack"])
    def test_serve_static_file_404(self):
        """
        When fetching a static file
            When the file does not exist
                We create the expected spans
        """
        # DEV: By default a static handler for `./static/` is configured for us
        res = self.client.get("/static/unknown-file")
        self.assertEqual(res.status_code, 404)
