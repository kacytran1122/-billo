import ast
import asyncio
from pathlib import Path
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[3]


def test_core_reuses_one_client_and_refreshes_trace_headers_without_cross_request_data():
    tree = ast.parse((ROOT / "backend/fetch.ai/common/core.py").read_text())
    tree.body = [node for node in tree.body if not (isinstance(node, ast.ImportFrom) and node.level)]
    env = {"CORE_URL": "https://core.test", "INTERNAL_TOKEN": "test-only", "carry": lambda: {"sentry-trace": "trace-1"}}
    exec(compile(tree, "core.py", "exec"), env)
    created, requests = [], []
    class FakeClient:
        is_closed = False

        async def get(self, path, *, headers, params, **kwargs):
            request = httpx.Request("GET", "https://core.test" + path, headers=headers, params=params)
            requests.append(request)
            return httpx.Response(200, request=request, json={"ok": True})

        async def post(self, path, *, headers, json, **kwargs):
            request = httpx.Request("POST", "https://core.test" + path, headers=headers, json=json)
            requests.append(request)
            return httpx.Response(200, request=request, json={"ok": True})

        async def aclose(self):
            self.is_closed = True

    def factory(**kwargs):
        instance = FakeClient()
        created.append(instance)
        return instance

    async def exercise():
        with patch.object(httpx, "AsyncClient", factory):
            try:
                await env["core_get"]("/first", q="synthetic")
                env["carry"] = lambda: {"sentry-trace": "trace-2"}
                await env["core_post"]("/second", {"case_id": "synthetic"})
                await env["core_get"]("/third")
                assert len(created) == 1
                assert requests[0].headers["sentry-trace"] == "trace-1"
                assert requests[1].headers["sentry-trace"] == "trace-2"
                assert not requests[2].url.query
                assert requests[2].content == b""
            finally:
                for instance in created:
                    await instance.aclose()

    asyncio.run(exercise())
