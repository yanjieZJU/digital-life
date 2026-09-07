## Purpose

让数字生命在用户缺席时仍能构成"什么是我"——通过自主遭遇世界（事件形式、经感知层）形成反应，在 dream 中结晶为稳定自我，并治理未来行动，使个性从经验中涌现而非被赋予。

## ADDED Requirements

### Requirement: 自主遭遇作为感知事件

当 agent 处于 idle 且能量充足时，系统 SHALL 以**感知事件**形式向 agent 呈现一次世界遭遇，而非将遭遇作为 prompt 直接插入模型上下文。遭遇 MUST 经由与用户消息相同的感知层路由（被编码为知觉信号，而非 raw prompt），使 agent 以主体身份"感知到世界呈现了某事"，而非被指令"思考某事"。

#### Scenario: idle 高能窗口触发遭遇

- **WHEN** agent 因 `initiative` 唤醒且能量高于自主探索阈值，且无未完成用户任务
- **THEN** 系统呈现一次世界遭遇作为感知事件，agent 在 wake 中通过 sense 感知遭遇内容而非被 prompt 告知

#### Scenario: 遭遇不绕过感知层

- **WHEN** 一次自主世界遭遇被呈现
- **THEN** 遭遇以事件形式进入生命周期队列并经感知层编码，不作为 role:user 的原始 prompt 直达模型核心

#### Scenario: 遭遇 stance 区别于用户需求

- **WHEN** agent 在 wake 中感知到一次世界遭遇
- **THEN** 遭遇携带"世界遭遇"语义标签（区别于"用户请求"），agent 的反应 stance 为"我遭遇了某事"而非"我被要求做某事"

### Requirement: 种子引导与自驱探索

冷启动阶段 SHALL 由种子提供初始遭遇目标，打破向内自省引力。在 agent 对种子遭遇产生反应后，后续遭遇目标 MUST 由 agent 根据自身反应（好奇心）自驱选择，无需用户刺激。种子影响 SHALL 随自驱探索成熟而衰减。

#### Scenario: 冷启动用种子

- **WHEN** agent 尚未形成任何自驱探索历史
- **THEN** 遭遇目标来自种子集，agent 对种子遭遇产生反应

#### Scenario: 反应驱动后续遭遇

- **WHEN** agent 已对一次遭遇产生反应
- **THEN** 下一次遭遇目标可由 agent 基于其反应自驱选定，且不依赖任何用户消息

#### Scenario: 种子衰减

- **WHEN** 自驱探索已建立稳定历史
- **THEN** 种子对遭遇目标选择的贡献下降，遭遇主要由 agent 自驱决定

### Requirement: 反应作为自我构成素材

agent 对遭遇的反应（立场、吸引/排斥、观点）SHALL 被捕获为**自我构成素材**，与任务教训和用户服务记忆区分。反应素材是后续结晶的输入，不被当作服务性 lesson 处理。

#### Scenario: 反应归类为构成素材

- **WHEN** agent 对一次世界遭遇表达立场或偏好
- **THEN** 该反应被记录为自我构成素材，标注其遭遇来源，且不与"为用户任务总结的 lesson"混同

### Requirement: dream 中结晶稳定自我

在 dream / memory_hygiene 周期中，系统 SHALL 将累积的遭遇反应结晶为稳定立场，并写入 self-cognition 慢变量（`slow_var` kind=self_cognition，当前为空槽位）。仅当反应在多次遭遇中呈现稳定模式时才结晶；无稳定模式时 MUST NOT 捏造自我。

#### Scenario: 稳定模式结晶

- **WHEN** dream 周期审查近期遭遇反应，发现跨多次遭遇的稳定立场模式
- **THEN** 系统将该稳定立场写入 self-cognition 慢变量

#### Scenario: 无稳定模式不结晶

- **WHEN** 近期遭遇反应未呈现稳定模式
- **THEN** 系统不向 self-cognition 写入捏造内容，保持该槽位为既有值或空

### Requirement: 结晶自我治理 wake

结晶后的 self-cognition SHALL 被注入 wake prompt 的 slow-context，在 agent 任何 sense 工具调用之前、于 first-thought 即治理其立场。这关闭构成回路：experience → revised self → different future action。当 self-cognition 为空时 SHALL 优雅回退，不阻断正常 wake。

#### Scenario: 结晶自我进入 first-thought

- **WHEN** self-cognition 慢变量持有结晶立场，且 agent 被唤醒
- **THEN** wake prompt 的 slow-context 包含该结晶自我，agent 在 first-thought 即处于该立场之下，无需先调用 sense 工具获取

#### Scenario: 空槽位优雅回退

- **WHEN** self-cognition 慢变量为空
- **THEN** wake 正常进行，不因缺失结晶自我而失败

### Requirement: 个性涌现而非赋予

系统 SHALL NOT 赋予固定人格字段。自我 MUST 从累积的遭遇反应中涌现；persona 文件作为初始参数保留，但 self-cognition 作为独立的、由经验结晶的层存在并治理行动，不被 persona 静态覆盖。

#### Scenario: 无硬编码人格

- **WHEN** 系统运行自我构成流程
- **THEN** 不存在被写入的固定 MBTI/人格分类字段；self-cognition 内容均来源于遭遇反应的结晶

#### Scenario: persona 与结晶自我分离

- **WHEN** wake 组装 prompt
- **THEN** persona（初始参数）与 self-cognition（经验结晶）作为独立来源共存，后者可随经验演化修订，前者不被后者直接覆写
