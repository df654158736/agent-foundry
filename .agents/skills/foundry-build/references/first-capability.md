# 从空包接入第一项能力

在业务项目根目录操作，以下为合成的备件库存例子。将用户、数据来源和权限换成当前业务。在 SPEC.md 写下第一道原问，以及能够独立验证结果的依据。这里承诺按物料编码返回可领用数量；缺少台账记录与数量为零要能区分。

**1. 接工具。** 将下段写入 business/tools.py。已有工具时追加到 TOOLS。正式接入时在函数内部按已授权身份查数据源，凭据由进程提供。

```python
from langchain_core.tools import tool

@tool
def available_parts(code: str) -> dict:
    """按物料编码查询当前台账可领用件数，未收录时返回 unknown。"""
    ledger = {"P-7": 12, "P-8": 0}
    if code not in ledger:
        return {"status": "unknown", "code": code}
    return {"status": "listed", "code": code, "count": ledger[code]}

TOOLS = [available_parts]
```

**2. 写运行时 Skill。** 创建 business/skills/parts-count/SKILL.md，保留开头的 YAML 分隔符。description 写清适用请求，正文写业务口径、来源和受阻时如何解释。项目的 .agents/skills/ 供开发侧 Codex 使用。

```markdown
---
name: parts-count
description: 当用户询问物料可领用件数或库存状态时，解释台账结果。
---
物料管理员维护可领用件数，以工具返回的当前台账为准。listed 且 count 为 0 表示已收录、当前无可领用件。unknown 表示台账未收录该编码，可请用户核对编码。
```

**3. 接系统提示并验证。** 在 business/system.md 说明助手帮助谁完成什么工作、允许什么动作，例如“帮助领料员按物料编码查询可领用件数。根据已核实的台账结果回答，权限为只读。” 框架会装配模型、工具、Skill 目录和会话。

运行 `uv run --locked python -m foundry doctor`，检查 tools 中有 available_parts、skills 中有 parts-count、skipped_skills 为空。有获准的模型与数据时设置 FOUNDRY_MODEL、OPENAI_API_KEY 和兼容端点 OPENAI_BASE_URL，然后运行 `uv run --locked python -m foundry chat 'P-7 可以领多少件？'`。该例应返回 12 件。按业务需要再查 P-8 和未收录编码，避免把两者都报成零。

按 [foundry-gold](../../foundry-gold/SKILL.md) 把原问和独立判据放到 evals/cases.json 与 evals/oracle.py，执行 `uv run --locked python -m foundry eval`。核对 trace.jsonl 里首次模型输入的工具 schema 和 Skill 描述、实际 read_file 及业务工具回执、用户最终答复。模型按需要选择 Skill；文件出现在目录中只能证明它可被发现。空项目要用 --fixture 时还须编写 evals/simulation.py 的 make_model()。从第一条真实失败进入 foundry-iterate。
