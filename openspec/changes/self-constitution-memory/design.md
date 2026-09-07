## Context

当前记忆系统有自我*描述*（`SELF_KNOWLEDGE.md`）而无自我*构成*。代码层证据（见 proposal.md - Why）：

- `slow_var` 表 + port（`domain/persistence/__init__.py:103`）+ impl（`infrastructure/persistence/instance/memory.py:204`）已存在，docstring 明列"自我认知 / 社交关系 / 任务板"，但**唯一调用方是 smoke test**——治理行动的"结晶自我"槽位空置。
- wake 的 slow-context 注入在 `domain/lifecycle/scheduler.py:1144`（`slow_ctx = _load_prev_session_summary`），目前只装 session digest（"我做了什么"），无"我是谁"。
- `initiative` 唤醒（"主动探索"，`scheduler.py:452`）idle 触发，但当前转向内部本体论自省——因为内部是唯一能"看"的地方。
- `web_search`/`web_fetch` 工具已存在（`interfaces/tools/web_tools.py`），但无自驱回路使用它们遭遇外部世界。
- 感知层（设计文档 §14）：`action_prompt` + `_sys_tool` 语义标签，过滤所有 incoming 信号——但纯被动，无 active sensing。
- dream = `memory_hygiene` skill，nightly，已有 7.5e 碎片→profile 消化作为"工程确定性 + 模型判断"的范式参照。

约束（CLAUDE.md）：遭遇源/结晶逻辑落 `domain/memory`；runtime 引擎与 SQLite 细节落 `infrastructure/`；prompt 上下文构造可审计留在 `domain/memory`/`domain/lifecycle`；`domain/` 只规划不执行。

## Goals / Non-Goals

**Goals:**
- 让 agent 在用户缺席时仍遭遇世界、形成反应，并让稳定模式结晶为治理 wake 的自我。
- 复用已有 event→perception→wake 管线与 `slow_var` 槽位，最小新增机械。
- 关闭构成回路（experience → revised self → different future action）。

**Non-Goals:**
- 不硬编码人格/MBTI 字段（个性是涌现的）。
- 不改变用户事件管线语义。
- 不实现跨实例实体共享（§9.7 另行处理）。
- 不替换 persona 或 session digest——自我构成层与之并存。

## Decisions

### D1: 遭遇作为事件，复用感知管线（不建并行系统）

遭遇源产生一个事件 → 经感知层（`action_prompt` + 新 `_sys_tool` 语义标签 `world_encounter`）编码 → 进入生命周期队列 → wake 中 agent 经 sense 感知。新增一个语义标签，不新增管线。

- **为何**：保留"反应里的我"。遭遇若作为 prompt 直插，会重演"被告知我是谁"——正是本设计要修复的。复用管线 = 主体感知而非外部指令。
- **替代**：直接 prompt 注入——拒绝（重演服务姿态）；新建并行感知通道——拒绝（违背"工程做确定性、最小机械"且割裂语义）。

### D2: 种子引导 + 自驱延续

种子（每实例一个，如 `apps/{id}/data/memories/CURIOSITY_SEED.md` 或结构化清单）提供初始遭遇目标，外部来源以打破向内引力。agent 对种子遭遇反应后，经工具（新增 `seek_encounter` 或复用 `web_search` 自选 query）自驱选定后续目标。种子贡献权重随自驱历史增长而衰减。

遭遇实现：外部经 `web_search`/`web_fetch`；agent 自身运行现实（日志、记忆、其他实例）作为 ambient 背景。

- **为何**：纯 ambient 无种子无法冷启动（向内引力会把 idle 变成 navel-gazing）；纯 curated feed 不够自驱。种子 + 衰减 = 既破冷启动又让自我自驱生长。
- **替代**：人工 curated feed——拒绝（不自驱）；纯 agent-free ambient——拒绝（冷启动失败）。

### D3: 反应作为新 layer，复用 consolidation 存储

遭遇反应存入现有 `memory_layers.db`，新增 `layer='encounter_reaction'`（runtime ALTER 模式，项目已有先例）。每条带遭遇来源 + stance 标签。反应是结晶输入，不与 lesson 混同。

- **为何**：避免 DB 增殖；反应天然是 dream 可读的累积素材，与现有 consolidation 读取路径一致。
- **替代**：新 DB——拒绝（增殖）；写入 entity_index——拒绝（实体索引是外部实体倒排，反应是内部立场，语义不同）。

### D4: dream 中结晶，写入 slow_var(self_cognition)

在 `memory_hygiene` 增加一步（与 7.5e 碎片→profile 消化并列）：读近期 encounter_reaction，由**模型判断**哪些呈现稳定立场模式，`set_slow_var(kind="self_cognition", ...)` 写入。这是 `slow_var` 的**首个生产写入方**。无稳定模式则不写。

- **为何**：对齐"工程做确定性（recall + write 工具），模型做判断（什么结晶了）"。dream 是既有代谢点，集中结晶避免实时噪音。
- **替代**：实时连续结晶——拒绝（premature、noisy、与 dream 节奏冲突）。

### D5: 接通自我治理回路

将 `slow_var(self_cognition)` 注入 `scheduler.py:1144` 的 slow-context 路径，**与 session digest 并存**（非替换）。first-thought 同时携带"我做了什么"（digest）与"我是谁"（self-cognition）。空槽位优雅回退。

- **为何**：这是回路闭合点——结晶自我从"可召回"变"治理"。与 digest 并存因任务连续性仍需保留。
- **替代**：替换 digest——拒绝（丢失任务连续性）；仅靠 sense 工具按需获取——拒绝（自我仍非 grounding，重演现状）。

### D6: initiative 唤醒从向内转 outward

`initiative` 唤醒在无未完成用户任务时，其 perception 包含一个 world_encounter 事件（来自种子/自驱队列），而非留 agent 自由 navel-gaze。这是触发绑定——把既有"主动探索"机制从内部指向外部。

## Risks / Trade-offs

- **[遭遇质量/噪音]** 无焦点 web 探索产出噪音 → 反应只是素材，未结晶不治理；dream 仅保留稳定模式；种子限定初始范围。
- **[成本/token]** idle 遭遇消耗能量与 token → 能量阈值门控；遵循 dream 预算纪律（既有 ≤50K ideal）；遭遇 wake 有界。
- **[自我漂移]** 涌现自我可能漂向不良立场 → persona 作初始参数保留；结晶保守（仅稳定模式）；不自动覆写 persona。
- **[向内引力残留]** agent 可能仍把遭遇转回内部 → `world_encounter` stance 标签 + 种子外部性 + 反应归"构成素材"非"自省"。
- **[slow_var 首个生产方]** 新写入路径无既有消费约束 → 先实现读（D5 注入）与写（D4 结晶）成对，避免写而不用重演 `last_accessed` 写路径冗余（commit b88f624 已清的同类反模式）。

## Migration Plan

1. `slow_var` 表已存在，无 schema 迁移。
2. `memory_layers.db` 新增 `layer='encounter_reaction'`（runtime ALTER 先例已有）。
3. 种子文件 opt-in per instance；缺失则不产生遭遇（优雅空转），待种子提供或自驱建立。
4. 回滚：禁用遭遇源；`slow_var` 保持空；wake 回退至 digest-only（D5 空槽位回退已保证）。

## Open Questions

- 种子的具体格式与内容（per-instance？谁 curate？）——可在 task 阶段定，不改变 spec 行为。
- 遭遇 cadence（idle 期间频率）——可调，起步保守。
- 遭遇反应是否也向量化以支持跨反应联想——可 defer，不影响核心回路。
- 自驱"next curiosity"用新工具还是复用 `web_search`——task 阶段定。
