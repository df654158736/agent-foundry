"""Controlled test double for the model only. Tool/skill dispatch uses the real graph."""
import json
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool


class DispatchFixture(BaseChatModel):
    model_name: str = "dispatch-fixture"

    @property
    def _llm_type(self):
        return "foundry-fixture"

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=[convert_to_openai_tool(tool) for tool in tools], **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        last = messages[-1]
        if isinstance(last, HumanMessage):
            reply = AIMessage(content="", tool_calls=[{
                "name": "read_file", "args": {"file_path": "/skills/dispatch-window/SKILL.md"},
                "id": f"read-{len(messages)}"}])
        elif isinstance(last, ToolMessage) and last.name == "read_file":
            requests = [m.text for m in messages if isinstance(m, HumanMessage)]
            station = re.findall(r"[东西]站", " ".join(requests))[-1]
            day = re.search(r"\d{4}-\d{2}-\d{2}", requests[-1]).group()
            reply = AIMessage(content="", tool_calls=[{
                "name": "lookup_window", "args": {"station": station, "day": day},
                "id": f"lookup-{len(messages)}"}])
        else:
            row = json.loads(last.text)
            text = row.get("window", "班次尚未发布，暂时无法核实。")
            reply = AIMessage(content=f"{row['station']} {row['day']}：{text}")
        return ChatResult(generations=[ChatGeneration(message=reply)])


def make_model():
    return DispatchFixture()
