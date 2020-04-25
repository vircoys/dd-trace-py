import pytest

from ddtrace import Pin
from ddtrace.contrib.aiohttp import patch

from ...utils.span import TracerSpanContainer
from ...utils.tracer import DummyTracer


# `pytest` automatically calls this function once when tests are run.
def pytest_configure():
    patch()


@pytest.fixture(autouse=True)
def patch_aiohttp(tracer):
    import aiohttp
    pin = Pin.get_from(aiohttp.web_app.Application)
    original_tracer = pin.tracer
    Pin.override(aiohttp, tracer=tracer)

    yield

    Pin.override(aiohttp.web_app.Application, tracer=original_tracer)


@pytest.fixture
def tracer():
    tracer = DummyTracer()
    yield tracer
    tracer.writer.pop()


@pytest.fixture
def spans(tracer):
    container = TracerSpanContainer(tracer)
    yield tracer.writer.spans
    container.reset()
