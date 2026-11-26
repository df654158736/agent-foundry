# Agent Foundry · Codex 入口

目标是帮助开发者快速、高效、高质量地交付一个新场景的业务智能体。以真实用户任务的结果、完成时间和返工判断设计价值。

1. 读 `docs/constitution.md`。看到 `business/` 即处于单业务项目，读取本地 `SPEC.md` 和 `CHECKLIST.md` 找到已授权工作与上次停点。在发行源码目录开发新业务时先用 `python -m foundry init <新目录>` 初始化，然后在该目录工作。框架自身的源码和示例由发行维护者管理。
2. 按需读取仓库内 .agents/skills 下的 SKILL.md。新建能力用 foundry-build，场景与金标用 foundry-gold，调查失败或复验用 foundry-iterate。工具接线和依赖见 docs/operations.md。设计目标与权限取舍用 goal-aligned-design，接口与模块改造用 codebase-design；失败调查和分轴判定分别打开 debug-agent-reallink 与 agent-evaluation-scoring；复杂跨会话交接使用 session-handoff。优先从本项目 .agents/skills/<名称>/SKILL.md 打开当前发行版本。线上模型只能使用 business/ 下的业务材料与已注册工具。
需要对已有代码进行专项架构审查时，显式使用 `$improve-codebase-architecture`。启用了前端扩展的项目，在页面开发与评审时可使用 `$web-design-guidelines`。

3. 有明确目标和证据就推进。涉及新授权、业务定义冲突或不可逆操作时带依据请负责人决定。使用项目内的独立 reviewer 前核对角色可用性，见 docs/review.md。开发和发布授权分别确认。
4. 用当前版本、实际入口及独立依据验收。更新 Checklist 的证据位置和下一动作，使新会话可以直接续接。临时调查仅留在对应运行中。
