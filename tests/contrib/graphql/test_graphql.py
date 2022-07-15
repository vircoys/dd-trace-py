import graphql
import pytest

from ddtrace import tracer
from ddtrace.contrib.graphql import graphql_version
from ddtrace.contrib.graphql import patch
from ddtrace.contrib.graphql import unpatch
from tests.utils import override_env
from tests.utils import snapshot


@pytest.fixture(autouse=True)
def enable_graphql_patching():
    with override_env(dict(DD_TRACE_GRAPHQL_RESOLVERS_ENABLED="true")):
        patch()
        yield
        unpatch()


@pytest.fixture
def test_schema():
    return graphql.GraphQLSchema(
        query=graphql.GraphQLObjectType(
            name="RootQueryType",
            fields={"hello": graphql.GraphQLField(graphql.GraphQLString, None, lambda obj, info: "friend")},
        )
    )


@pytest.fixture
def test_source_str():
    return "{ hello }"


@pytest.fixture
def test_source(test_source_str):
    return graphql.Source(test_source_str)


@pytest.mark.asyncio
async def test_graphql(test_schema, test_source_str, snapshot_context):
    with snapshot_context():
        if graphql_version < (3, 0):
            result = graphql.graphql(test_schema, test_source_str)
        else:
            result = await graphql.graphql(test_schema, test_source_str)
        assert result.data == {"hello": "friend"}


@pytest.mark.asyncio
async def test_graphql_error(test_schema, snapshot_context):
    with snapshot_context(ignores=["meta.error.type", "meta.error.msg"]):
        if graphql_version < (3, 0):
            result = graphql.graphql(test_schema, "{ invalid_schema }")
        else:
            result = await graphql.graphql(test_schema, "{ invalid_schema }")
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], graphql.error.GraphQLError)
        assert "Cannot query field" in result.errors[0].message


@snapshot(token_override="tests.contrib.graphql.test_graphql.test_graphql")
@pytest.mark.skipif(graphql_version >= (3, 0), reason="graphql version>=3.0 does not return a promise")
def test_graphql_v2_promise(test_schema, test_source_str):
    promise = graphql.graphql(test_schema, test_source_str, return_promise=True)
    result = promise.get()
    assert result.data == {"hello": "friend"}


@snapshot(
    token_override="tests.contrib.graphql.test_graphql.test_graphql_error",
    ignores=["meta.error.type", "meta.error.msg"],
)
@pytest.mark.skipif(graphql_version >= (3, 0), reason="graphql.graphql is NOT async in v2.0")
def test_graphql_error_v2_promise(test_schema):
    promise = graphql.graphql(test_schema, "{ invalid_schema }", return_promise=True)
    result = promise.get()
    assert len(result.errors) == 1
    assert isinstance(result.errors[0], graphql.error.GraphQLError)
    assert result.errors[0].message == 'Cannot query field "invalid_schema" on type "RootQueryType".'


@snapshot()
@pytest.mark.skipif(graphql_version >= (3, 0), reason="graphql.graphql is NOT async in v2.0")
def test_graphql_v2_with_document(test_schema, test_source_str):
    source = graphql.language.source.Source(test_source_str, "GraphQL request")
    document_ast = graphql.language.parser.parse(source)
    result = graphql.graphql(test_schema, document_ast)
    assert result.data == {"hello": "friend"}


@snapshot(token_override="tests.contrib.graphql.test_graphql.test_graphql")
@pytest.mark.skipif(graphql_version < (3, 0), reason="graphql.graphql_sync is NOT suppoerted in v2.0")
def test_graphql_sync(test_schema, test_source_str):
    result = graphql.graphql_sync(test_schema, test_source_str)
    assert result.data == {"hello": "friend"}


@snapshot()
def test_graphql_execute(test_schema, test_source_str):
    with tracer.trace("test-execute-instrumentation"):
        source = graphql.language.source.Source(test_source_str, "GraphQL request")
        ast = graphql.language.parser.parse(source)
        # execute() can be imported from two modules, ensure both are patched
        res1 = graphql.execute(test_schema, ast)
        res2 = graphql.execution.execute(test_schema, ast)
        assert res1.data == {"hello": "friend"}
        assert res2.data == {"hello": "friend"}


@snapshot(token_override="tests.contrib.graphql.test_graphql.test_graphql_execute")
@pytest.mark.skipif(graphql_version < (3, 1), reason="graphql.execute_sync is not supported in graphql<3.1")
def test_graphql_execute_sync(test_schema, test_source_str):
    with tracer.trace("test-execute-instrumentation"):
        source = graphql.language.source.Source(test_source_str, "GraphQL request")
        ast = graphql.language.parser.parse(source)
        # execute_sync() can be imported from two modules, ensure both are patched
        res1 = graphql.execute_sync(test_schema, ast)
        res2 = graphql.execution.execute_sync(test_schema, ast)
        assert res1.data == {"hello": "friend"}
        assert res2.data == {"hello": "friend"}
