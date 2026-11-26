# Agent Foundry · 智能体工坊

给 Codex 一个业务目标，在一个独立项目内把原问做成可运行的智能体，再沿真实证据迭代。开发者维护业务工具、系统提示词和运行时 Skill；框架随包提供运行时、金标驱动、开发 Skill、两个只读 reviewer 和接续入口。

## 第一次使用

在已安装 uv 0.12.2 的终端，从发行目录执行下面三步。初次同步会获取 CPython 3.12.13 和锁定的公共依赖，已有缓存时可离线使用。

```bash
uv sync --locked
uv run --locked python -m foundry init ../dispatch-agent --example dispatch
cd ../dispatch-agent
uv run --locked python -m foundry doctor
uv run --locked python -m foundry eval --fixture
```

最后一条命令通过真实 Deep Agents 图、工具和 Skill 运行两道合成金标。模型由受控替身提供。终端输出本次运行目录，打开 run.json 和各 attempt 下的 trace.jsonl、delivery.json 可核对全过程。输入、判分与模型可见内容分开保存。

要运行真实模型，在当前环境设置 FOUNDRY_MODEL、OPENAI_API_KEY，使用兼容服务时再设置 OPENAI_BASE_URL。执行 `uv run --locked python -m foundry chat` 可在同一进程内连续对话；执行 `uv run --locked python -m foundry eval` 使用同一个业务入口和独立 Oracle。

## 开发自己的智能体

回到发行目录，执行 `uv run --locked python -m foundry init ../my-agent`。在新目录打开 Codex 并描述任务，例如「做一个样品预约预审助手，先用合成单据打通预审与补正，核对权限、写出首批金标，按实际失败迭代」。Codex 从 AGENTS.md 选择开发 Skill，读取业务 Spec 和 Checklist。新业务模板不带示例政策或金标答案。

| 文件 | 用途 |
| --- | --- |
| business/system.md、tools.py、skills/ | 用户能使用的业务智能体 |
| SPEC.md、evals/cases.json、evals/oracle.py | 业务契约、冻结场景和独立判据 |
| AGENTS.md、.agents/skills/、.codex/agents/ | Codex 入口、开发方法与项目级 reviewer |
| CHECKLIST.md、.runs/ | 接续工作、复查原始失败和候选证据 |
| foundry-release.json、uv.lock | 初始化时写入的框架版本与摘要、环境依赖 |

## Codex 如何自检和修复

在业务目录打开 Codex，可直接输入：

> 根据 SPEC 和 Checklist 运行已授权的金标。用真链 Skill 找出第一次出现错误的输入、决策或回执，按七维评分区分责任。只修有证据的责任层，保留冻结用例和首次失败，用原题和相邻反例复验，请 spec_delivery_reviewer 独立核对，再更新 Checklist。

随包有 [开发 Skills](.agents/skills/) 和 [项目 reviewer](.codex/agents/)。三个 Foundry 入口负责导航；目标对齐、代码架构、真链排障、七维评分与复杂交接五项方法来自原开发资产，包含对应的参考资料。两份 reviewer 配置保留原评审判据并限制为只读。发行版将工作区专属规则入口和跨 Skill 引用改为项目路径。日常进度仍由 Checklist 管理。

例如在班次示例中，若第二轮提案带了新日期、工具却返回前一天的班次，先沿该调用对准工具输入与回执，再检查数据选择条件。修正后分别核验第二轮实际站点与日期、交付时段和未发布场景。完整对话质量与真实模型稳定性仍需单独验收。模型与数据均获准时使用 live 模式，fixture 仅用于可重复的受控对照。

## 按场景使用开发 Skill

- 对已有系统做架构体检时，在 Codex 中输入「用 $improve-codebase-architecture 检查这条链路为什么反复返工，给出最值得做的一项修改和复验条件」。该入口适合已有代码的专项审查。[架构审查方法](.agents/skills/improve-codebase-architecture/SKILL.md)
- 有 Web 交互的业务项目可从发行目录使用 `uv run --locked python -m foundry init ../my-agent --frontend`。该选项为 Codex 安装通用前端审查 Skill。随后可输入「用 $web-design-guidelines 检查这个确认表单的键盘操作、失败提示和刷新恢复」。规则已固定，评审时可离线使用。[前端扩展与来源](extensions/web-design-guidelines/SKILL.md)
- 已有业务项目可在并行升级时加 `--frontend` 开启扩展；此前已启用的项目会自动保留。普通 CLI 项目继续使用默认初始化。

## 验收、发行与升级

在发行源码根目录运行：

```bash
uv run --locked python -m unittest discover -s tests
uv run --locked python -m scripts.prove_iteration
uv run --locked python scripts/package_release.py
```

第二条命令在临时目录构造一个可复现的业务工具缺陷和正确候选，保留两次独立运行。预期原题 fail → pass，相邻场景 pass → pass。它演示故障注入、归因取证和复验，开放式语义质量由真实模型单独验收。第三条命令在 dist/ 生成源码发行 ZIP 与 SHA-256。

升级时从新发行目录执行 `uv run --locked python -m foundry upgrade ../my-agent ../my-agent-candidate`，用两边相同的冻结用例重新验证。当前面向可信开发者单机使用，无页面。详见 [使用与升级](docs/operations.md)、[框架宪法](docs/constitution.md)、[独立复核](docs/review.md)。

v0.1.3 支持对每次运行分别登记业务结果与用户正文的复核意见。用 `python -m foundry review RUN` 从新会话打开待判用例，使用 `compare BASE CANDIDATE --require-review` 验证候选自动检查与逐题复核均通过。登记格式与接手流程见 [独立评审](docs/review.md)。
