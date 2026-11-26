"""Use the public provider adapter and business graph, with an in-process HTTP transport."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx
from langchain_openai import ChatOpenAI

from foundry.privacy import scrub
from foundry.project import initialize
from foundry.runtime import Session


class AdapterTests(unittest.TestCase):
    def test_new_domain_and_provider_wire(self):
        calls = []

        def respond(request):
            data = json.loads(request.content)
            calls.append(data)
            last = data["messages"][-1]
            if last["role"] == "tool":
                message = {"role": "assistant", "content": "Ready " + last["content"]}
            else:
                message = {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "wire-call-1", "type": "function", "function": {
                        "name": "stock", "arguments": json.dumps({"sku": "A4"})}}]}
            return httpx.Response(200, json={"id": "wire", "object": "chat.completion",
                "created": 1, "model": "foundry-test", "choices": [{"index": 0, "message": message,
                "finish_reason": "stop" if last["role"] == "tool" else "tool_calls"}]})

        with TemporaryDirectory() as tmp, httpx.Client(transport=httpx.MockTransport(respond)) as client:
            project = initialize(Path(tmp) / "supplies")
            (project / "business/system.md").write_text("Office supplies assistant.")
            (project / "business/tools.py").write_text(
                'def stock(sku: str) -> int:\n    """Read synthetic stock count by SKU."""\n'
                '    return {"A4": 17}[sku]\n\nTOOLS = [stock]\n'
            )
            model = ChatOpenAI(model="foundry-test", api_key="in-process-placeholder",
                               http_client=client, base_url="https://example.invalid/v1", max_retries=0)
            answer = Session(project, model).ask("How much A4 stock?")
        self.assertIn("17", answer)
        self.assertEqual(len(calls), 2)
        names = {t["function"]["name"] for t in calls[0]["tools"]}
        self.assertIn("stock", names)
        self.assertFalse(names & {"lookup_window", "execute", "task", "delete"})
        self.assertIn("Office supplies assistant.", json.dumps(calls[0]["messages"]))

    def test_scrub_credentials(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-demo-secret"}):
            saved = scrub({"content": "Bearer abc123 synthetic-demo-secret",
                           "payload": '{"password": "example"}', "access_token": "example"})
        self.assertNotIn("example", str(saved))
        self.assertNotIn("abc123", str(saved))
        self.assertNotIn("synthetic-demo-secret", str(saved))
