"""Exercise the business authoring guide shipped inside an initialized empty project."""
from contextlib import redirect_stdout
from io import StringIO
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx
from langchain_openai import ChatOpenAI

from foundry.project import initialize
from foundry.__main__ import main
from foundry.runtime import inspect_business_skills


class BuildEntryTests(unittest.TestCase):
    def test_documented_tool_and_skill_reach_model(self):
        requests = []

        def respond(request):
            body = json.loads(request.content)
            requests.append(body)
            if len(requests) <= 2:
                tool, args = (("read_file", {"file_path": "/skills/parts-count/SKILL.md"}) if len(requests) == 1
                              else ("available_parts", {"code": "P-7"}))
                message = {"role": "assistant", "content": None, "tool_calls": [
                    {"id": f"call-{len(requests)}", "type": "function",
                     "function": {"name": tool, "arguments": json.dumps(args)}}]}
            else:
                count = json.loads(body["messages"][-1]["content"])["count"]
                message = {"role": "assistant", "content": f"可领用 {count} 件。"}
            return httpx.Response(200, json={"id": "test", "object": "chat.completion", "created": 1,
                "model": "test", "choices": [{"index": 0, "message": message,
                "finish_reason": "tool_calls" if "tool_calls" in message else "stop"}]})

        with TemporaryDirectory() as tmp, httpx.Client(transport=httpx.MockTransport(respond)) as client:
            root = initialize(Path(tmp) / "parts")
            guide = (root / ".agents/skills/foundry-build/references/first-capability.md").read_text()
            business = root / "business"
            (business / "tools.py").write_text(guide.split("```python\n")[1].split("```")[0])
            skill = business / "skills/parts-count/SKILL.md"
            skill.parent.mkdir()
            skill.write_text("# No frontmatter\n")
            self.assertEqual(inspect_business_skills(root), ([], ["parts-count/SKILL.md"]))
            skill.write_text(guide.split("```markdown\n")[1].split("```")[0])
            self.assertEqual(inspect_business_skills(root), (["parts-count"], []))
            (business / "system.md").write_text("帮助领料员查询件数。")
            model = ChatOpenAI(model="test", api_key="in-process-only", http_client=client,
                               base_url="https://example.invalid/v1", max_retries=0)
            with patch("foundry.runtime.live_model", return_value=model), patch.object(
                sys, "argv", ["foundry", "--project", str(root), "chat", "P-7 可以领多少件？"]
            ), redirect_stdout(StringIO()) as output:
                self.assertEqual(main(), 0)
            answer = output.getvalue().strip()
        self.assertEqual("可领用 12 件。", answer)
        self.assertIn("available_parts", [t["function"]["name"] for t in requests[0]["tools"]])
        self.assertIn("parts-count", json.dumps(requests[0]["messages"][0]["content"]))
        self.assertIn("物料管理员", requests[1]["messages"][-1]["content"])
        self.assertEqual({"code": "P-7", "status": "listed", "count": 12},
                         json.loads(requests[2]["messages"][-1]["content"]))
