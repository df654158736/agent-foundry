"""Business-only graph. Evaluation and developer assets stay outside its filesystem."""
import os
from uuid import uuid4

from deepagents import (FilesystemPermission, GeneralPurposeSubagentProfile, HarnessProfile,
                        create_deep_agent, register_harness_profile)
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from .project import extension


def inspect_business_skills(root):
    # Use the discovery implementation of our pinned Deep Agents release.
    from deepagents.middleware.skills import _list_skills_with_errors

    directory = root / "business/skills"
    loaded, error = _list_skills_with_errors(FilesystemBackend(root_dir=directory, virtual_mode=True), "/")
    if error:
        raise ValueError(error)
    paths = {s["path"].lstrip("/") for s in loaded}
    skipped = sorted(str(p.relative_to(directory)) for p in directory.glob("*/SKILL.md")
                     if p.relative_to(directory).as_posix() not in paths)
    return sorted(s["name"] for s in loaded), skipped


def live_model():
    if not os.getenv("FOUNDRY_MODEL") or not os.getenv("OPENAI_API_KEY"):
        raise ValueError("请设置 FOUNDRY_MODEL 和 OPENAI_API_KEY，或运行 eval --fixture")
    return ChatOpenAI(model=os.environ["FOUNDRY_MODEL"], timeout=60, max_retries=1,
                      base_url=os.getenv("OPENAI_BASE_URL"))


class Session:
    def __init__(self, root, model, callbacks=()):
        business = root / "business"
        tools = extension(business / "tools.py").TOOLS
        skill_root = business / "skills"
        # Read verified Skill assets only. All scratch writes stay in the graph.
        backend = CompositeBackend(default=StateBackend(), routes={
            "/skills/": FilesystemBackend(root_dir=skill_root, virtual_mode=True)
        })
        profile = HarnessProfile(
            excluded_tools=frozenset({"execute", "task", "delete"}),
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        )
        register_harness_profile(f"{model._get_ls_params()['ls_provider']}:{model.model_name}", profile)
        self.graph = create_deep_agent(
            model=model, tools=tools, system_prompt=(business / "system.md").read_text(),
            skills=["/skills/"], backend=backend, subagents=[], checkpointer=InMemorySaver(),
            permissions=[FilesystemPermission(operations=["write"], paths=["/skills", "/skills/**"], mode="deny")],
        )
        self.config = {"configurable": {"thread_id": uuid4().hex}, "callbacks": list(callbacks),
                       "recursion_limit": 32}

    def ask(self, prompt):
        result = self.graph.invoke({"messages": [{"role": "user", "content": prompt}]}, self.config)
        final = result["messages"][-1]
        if not isinstance(final, AIMessage) or final.tool_calls or not final.text.strip():
            raise ValueError("当前轮没有可交付的模型正文")
        return final.text
