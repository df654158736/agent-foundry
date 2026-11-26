---
name: web-design-guidelines
description: 审查 Web 界面的可访问性、表单、键盘与焦点、布局、导航和交互状态。适合有页面的业务项目开展前端实现自检或 UI review。
---

# Web 界面审查

从用户指定的页面或流程开始，读[随包规则](references/command.md)，再读实际处理该交互的页面和组件。根据当前产品的用户、语言、技术栈和已有设计系统，选择适用条目。例如服务端渲染应用要核对 hydration；键盘焦点、控件标签和错误反馈适用于多种框架。

以可复现的操作组织发现。给出代码位置、用户动作、可观察的结果、修复建议及复验办法。源码能证明的违约直接指出；焦点移动、窄屏溢出、浏览器后退和刷新恢复等行为应从实际页面确认。无法运行页面时标明静态审查的范围。

业务智能体含确认或工具执行时，选择与用户工作相关的一条路径做跨层核验。例如提交后刷新页面，检查同一任务能否恢复、执行结果是否真实可见、重复点击是否造成重复操作。必要时用项目的 debug-agent-reallink 沿交互定位到回执或状态。仅在获得实施授权时修改页面。

## 来源

本目录为 Agent Foundry 的中文接入。审查规则取自 [Vercel Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines/blob/434b7f91364665f2f733b310ec54809bf8f37937/command.md)，与 [Vercel 官方 Skill](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines) v1.1.0 所标注的快照一致。规则文件 SHA-256 为 `d246b026f4f29b5823a9cc857f9edf3d2507002e055e32040cadeaf3b38e0234`。参见[上游 MIT 许可证](LICENSE)。更新快照时重新核对原始提交、许可证和文件摘要。
