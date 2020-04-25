from aiohttp import web

from ...utils.span import TestSpan


async def hello(request):
    return web.Response(text="Hello, world")


async def test_server_request(aiohttp_client, spans):
    app = web.Application()
    app.router.add_get("/hi", hello)
    client = await aiohttp_client(app)
    resp = await client.get("/hi")
    assert resp.status == 200
    text = await resp.text()
    assert "Hello, world" in text
    assert len(spans) == 1

    TestSpan(spans[0]).assert_matches(
        service="aiohttp.server",
        resource="GET /hi",
    )
