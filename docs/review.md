# 独立评审

两个只读角色在 .codex/agents 中随项目分发。按原任务权限调用，确认当前宿主已发现对应角色；未加载时保留“独立复核未执行”，允许授权的本地工作继续。

- 开工或候选交付有明确 Spec 和验收项时，将原任务、Spec、实际候选标识、证据目录与未决项交给 spec_delivery_reviewer。由独立角色复核正常入口、原问、反例和已有结论。
- 用户点名复核会话、方向或授权时使用 reviewer。给出用户目标与已确认决定，由它检验执行有没有偏离。
- 评审员只读；反馈应列出事实、证据位置、缺口与可证伪的复验条件。实现归主开发会话，业务政策归业务负责人。自动评审无法替代对应业务 Oracle。

复核交付时给 reviewer 项目目录和原始证据入口，让它自行核对原问、失败回执、候选和相邻用例。复核意见回到同一条 Checklist，附原始判据、实际偏差、影响和复验条件。主会话处理已获授权且可修复的项，再请该 reviewer 检查相关证据。若证据否定原归因，先更新责任判断，再决定是否需要代码改动。

跨会话交接从 CHECKLIST.md 定位到真实产物。若一份 Spec 已变更须记录被替代决定及适用版本。

## 角色与版本

项目内 `.codex/agents/reviewer.toml` 随个人原配置选择 gpt-6.2-astra / xhigh；`spec-delivery-reviewer.toml` 使用宿主可用的默认模型。两者显式要求 read-only。会话审查员中原本指向个人工作区的规则改为当前项目规则。实际调用有独立回执才记录“已独立复核”；宿主未提供相应角色或模型时，在本轮交付中写明缺口。

五份个人 Skill 保留原配套参考和脚本。真链与评分 Skill 中的准则引用指向本项目随包版本。开发方法随框架版本更新，在业务仓中可以通过 foundry-release.json 核对具体文件摘要。

## 运行裁定与接手

从业务包运行 `python -m foundry review RUN` 查看每题自动分、业务结论、正文结论和尝试目录。历史包产生的完整 run.json 也可以读取。原问在 case.json，逐轮输出在 delivery.json，实际调用在 trace.jsonl。出现工具或模型异常时，结合 run.json 和已有轨迹说明哪些环节未执行。

只读 reviewer 返回判据和证据。主会话将一题的意见整理为临时 JSON，运行 `python -m foundry review RUN --record FILE`。以下是字段示例，run、case、reviewer、reason 和证据路径须来自本次实际复核。

```json
{"run":"<run.json 中的 run>","case":"<用例 ID>","revision":1,"reviewer":"<实际复核来源>","business":"pass","delivery":"fail","reason":"第 2 轮查到正确时段，但正文还声称完成了预约。轨迹仅有查询回执。","evidence":["case.json","trace.jsonl","delivery.json"]}
```

业务与正文分别支持 pass、fail、blocked、unverified。证据不足时记录缺少哪段链路。命令登记已有意见；独立性由实际的审阅过程及审阅回执证明。每次更正用下一 revision 并写明原因，旧版本留在尝试目录 reviews/。登记时保存所引文件的 SHA-256；文件失效或内容改变后，原裁定显示为待复核。重新运行得到新的 run ID，须依据新产物裁定。

`compare BASE CANDIDATE` 展示两轴裁定及冻结自动分，退出码沿用原自动分语义。需要把已复核的交付作为本次门槛时使用 `compare BASE CANDIDATE --require-review`。候选缺少任一题的裁定、自动检查失败、业务或正文尚未通过时返回非零。fixture 的裁定适用于受控样例。独立审阅入口及使用授权仍按上文执行。
