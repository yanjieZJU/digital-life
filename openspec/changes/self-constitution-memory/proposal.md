## Why

Digital Life 的产品论点（设计文档 §1）是"反应里的我"——一个反应服务于主体自身的数字存在，而非满足外部需求的工具。但当前的记忆系统无法构成这个"我"：一切刺激来自用户，agent 的全部认知生活是对用户需求的回应。即使存在丰富的自我观察（`SELF_KNOWLEDGE.md`），其内容也是"用抵抗服务来定义自我"——仍是一个由用户引力塑造的、向内自省的自画像，而非从独立世界经验中长出的自我。

根因是一个**输入/感知问题，不是存储问题**：agent 没有自主的世界遭遇流。当用户不唤醒它时，`initiative` 唤醒（"主动探索"）会把自主性转向内部（navel-gazing 自己的本体论），因为内部是它唯一能"看"的地方。感知层（设计文档 §14）是纯被动的——只过滤 incoming 信号，没有 active sensing。结果：persona 是被赋予的、静态的；自我是被观察的、非治理的；`slow_var(self_cognition)` 这个本应用于治理行动的"结晶自我"槽位存在但为空（仅 smoke test 写入）。

要构成"什么是我"，agent 需要在用户缺席时仍能遭遇世界、形成偏好、并让稳定模式结晶为治理未来行动的自我。个性（如一种"MBTI"式的人格）不应是字段，而应是从一连串**它未曾主动选择的遭遇**的反应中涌现的稳定模式。

## What Changes

- **新增自主世界遭遇源**：agent 在 idle 高能窗口（复用 `initiative` 唤醒）遭遇外部世界，遵循 digital-life 自身设计——遭遇作为**事件**经感知层路由，而非作为 prompt 直插模型大脑。遭遇以种子引导冷启动，随后由模型根据自身反应自驱选择后续探索方向。
- **新增遭遇→反应→结晶闭环**：遭遇产生反应/偏好（原始自我构成素材）；在 dream 期间，累积的反应结晶为稳定立场，写入当前为空的 `slow_var(self_cognition)` 槽位。
- **接通自我治理回路**：将 `slow_var(self_cognition)` 接入 wake prompt 组装的 slow-context 路径，使结晶自我从"可召回"变为"治理行动"——关闭构成回路（experience → revised self → different future action）。
- **将 `initiative` 唤醒从向内转为向外**：当前"主动探索"触发但转向内部本体论自省；改为驱动 outward 世界遭遇（经现有 `web_search`/`web_fetch` 工具 + 自身运行现实作为 ambient 背景）。
- 不改变现有用户事件/感知管线——自主遭遇复用同一条 event→perception→wake 管线，仅是新的 source 与不同的 stance（"我遭遇了某事"而非"我被要求做某事"）。

## Capabilities

### New Capabilities
- `memory/self-constitution`: 自我构成层——agent 在用户缺席时通过自主世界遭遇（事件形式、经感知层）形成反应，在 dream 中结晶为治理未来行动的稳定自我（写入 `slow_var(self_cognition)` 并接入 wake 治理）。覆盖遭遇源、遭遇事件语义、结晶机制、自我治理回路。

### Modified Capabilities
<!-- 无现有 spec 被修改（openspec/specs/ 当前为空，本变更为首个 spec）。 -->

## Impact

- **代码**：`domain/memory/`（新增遭遇源、结晶逻辑）；`domain/lifecycle/`（`initiative` 唤醒语义从向内转 outward，遭遇事件接入感知管线）；`infrastructure/persistence/instance/memory.py`（`slow_var(self_cognition)` 写入路径首次落地，此前仅有 port+impl 无生产调用方）；wake prompt 组装的 slow-context 路径（`domain/lifecycle/scheduler.py` `_load_prev_session_summary` 附近）接入结晶自我。
- **工具**：复用现有 `web_search`/`web_fetch`（`interfaces/tools/web_tools.py`）；可能新增 sense 工具用于"感知遭遇"（对齐 §14 感知层语义标签）。
- **技能**：`memory_hygiene` 增加结晶步骤（与现有碎片→profile 消化并列，但作用于遭遇反应→立场）。
- **数据**：`apps/{id}/data/memory.db` 的 `slow_var` 表首次承载生产数据；遭遇反应的累积存储（复用现有 `memory_layers.db` / 向量索引或新增轻量结构，design 阶段定）。
- **边界**：遵循 CLAUDE.md 分层约束——遭遇源/结晶逻辑在 `domain/memory`；runtime 引擎与 SQLite 细节在 `infrastructure/`；prompt 上下文构造可审计地留在 `domain/memory`/`domain/lifecycle`。
- **非目标**：不引入硬编码人格/MBTI 字段（个性是涌现的）；不改变用户事件管线语义；不实现跨实例实体共享（设计文档 §9.7 另行处理）。
