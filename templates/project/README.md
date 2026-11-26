# 业务智能体

在本目录打开 Codex，给出一个业务目标，入口见 AGENTS.md。安装 uv 0.12.2 并运行 uv sync --locked。
用 python -m foundry doctor 检查接线（通过 uv run --locked 执行 Python）。
业务入口在 business/，验收依据在 evals/，当前进度在 CHECKLIST.md。命令与升级参见 docs/operations.md。

首次搭建时可直接告诉 Codex：“根据我的业务目标，按 foundry-build 写第一项工具和业务 Skill，运行 doctor，并用第一道原问核对实际交付。” 文件写法和命令见[首个能力接入示例](.agents/skills/foundry-build/references/first-capability.md)。
