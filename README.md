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

## 验收、发行与升级

在发行源码根目录运行：

```bash
uv run --locked python -m unittest discover -s tests
uv run --locked python -m scripts.prove_iteration
uv run --locked python scripts/package_release.py
```

第二条命令在临时目录构造一个可复现的业务工具缺陷和正确候选，保留两次独立运行。预期原题 fail → pass，相邻场景 pass → pass。它演示故障注入、归因取证和复验，开放式语义质量由真实模型单独验收。第三条命令在 dist/ 生成源码发行 ZIP 与 SHA-256。

升级时从新发行目录执行 `uv run --locked python -m foundry upgrade ../my-agent ../my-agent-candidate`，用两边相同的冻结用例重新验证。当前面向可信开发者单机使用，无页面。详见 [使用与升级](docs/operations.md)、[框架宪法](docs/constitution.md)、[独立复核](docs/review.md)。
