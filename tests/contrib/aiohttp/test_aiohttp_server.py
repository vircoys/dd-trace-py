from aiohttp import web

from ...utils import span
from . import utils


async def test_server_request_200(aiohttp_client, spans):
    app = web.Application()
    app.router.add_get("/hi", utils.hello)
    client = await aiohttp_client(app)
    resp = await client.get("/hi")
    assert resp.status == 200
    text = await resp.text()
    assert "Hello, world" in text
    assert len(spans)

    span.TestSpan(spans[0]).assert_matches(
        name="aiohttp.request",
        service="aiohttp.server",
        resource="GET /hi",
        error=0,
        meta={
            "http.method": "GET",
            "http.status_code": "200",
        }
    ).assert_is_measured()


async def test_server_request_500(aiohttp_client, spans):
    app = web.Application()
    app.router.add_get("/err", utils.error)
    client = await aiohttp_client(app)
    resp = await client.get("/err")
    assert resp.status == 500
    assert len(spans)

    span.TestSpan(spans[0]).assert_matches(
        name="aiohttp.request",
        service="aiohttp.server",
        resource="GET /err",
        error=1,
        meta={
            "error.msg": "Failed!",
            "http.method": "GET",
            "http.status_code": "500",
        }
    ).assert_is_measured()

