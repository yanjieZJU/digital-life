## 1. slow_var 自我认知读写基础

- [x] 1.1 在 `domain/memory` 定义 self-cognition 慢变量的领域语义（kind=`self_cognition`，内容契约：结晶立场结构），复用既有 `domain/persistence` port（`set_slow_var`/`get_slow_var`），不新增 port
- [x] 1.2 实现 `get_slow_var("self_cognition")` 的领域读取封装（`domain/memory`），供 wake 组装与 dream 结晶共享——读与写成对落地，避免写而不用（D5 风险）
- [x] 1.3 单测：写入后可读回；空槽位读取返回 None 且不抛异常

## 2. 遭遇事件源与感知路由

- [x] 2.1 定义 `world_encounter` 感知语义标签（`_sys_tool` 维度），与既有 user/timer/vital 标签并列，区分"世界遭遇"stance 与"用户请求"stance
- [x] 2.2 实现遭遇源：种子加载（`apps/{id}/data/memories/CURIOSITY_SEED.md`，格式 per Open Question，起步用简单结构化清单）+ 自驱后续目标选择（Open Question：新增 `seek_encounter` 工具 vs 复用 `web_search`——起步复用 `web_search` 自选 query）
- [x] 2.3 遭遇源产出事件 → 经感知层（`action_prompt` + `_sys_tool=world_encounter`）编码 → 进入生命周期队列，复用既有 event→perception→wake 管线，不新增并行通道
- [x] 2.4 种子贡献衰减逻辑：随自驱探索历史增长降低种子权重
- [x] 2.5 单测：遭遇事件携带 `world_encounter` 标签经感知层路由；种子缺失时优雅空转（不产生遭遇）

## 3. initiative 唤醒转向 outward

- [x] 3.1 在 `domain/lifecycle`（`initiative` 唤醒处理，`scheduler.py:452` 附近）绑定：`initiative` 唤醒且无未完成用户任务时，从遭遇源取一个 `world_encounter` 事件注入 perception，而非留 agent 自由 navel-gaze
- [x] 3.2 能量阈值门控：低于自主探索阈值时不触发遭遇（回退既有 idle 行为）
- [x] 3.3 边界校验：`domain/lifecycle` 只规划触发与事件组装，runtime 执行在 `infrastructure/`；运行 `tests/test_orchestration_boundary.py` 确认未越界

## 4. 反应捕获为 encounter_reaction 层

- [x] 4.1 在 `memory_layers.db` 新增 `layer='encounter_reaction'`（runtime ALTER 先例），每条带遭遇来源 + stance 标签，与 lesson 区分
- [x] 4.2 实现反应写入路径：agent 对遭遇表达立场/偏好时，记录为 encounter_reaction（领域层定义语义，infrastructure 落库）
- [x] 4.3 实现反应读取路径：供 dream 结晶读取近期遭遇反应
- [x] 4.4 单测：反应归类为 encounter_reaction 而非 lesson；带遭遇来源标注

## 5. dream 中结晶写入 slow_var

- [x] 5.1 在 `memory_hygiene` skill 新增结晶步骤（与 7.5e 碎片→profile 消化并列）：读近期 encounter_reaction，由模型判断稳定立场模式
- [x] 5.2 稳定模式 → `set_slow_var(kind="self_cognition", ...)` 写入（首个生产写入方）；无稳定模式则不写（不捏造自我）
- [x] 5.3 结晶保守约束：仅跨多次遭遇的稳定模式结晶；不自动覆写 persona
- [x] 5.4 单测：稳定模式结晶写入；无稳定模式保持既有值/空

## 6. 结晶自我治理 wake

- [x] 6.1 在 `domain/lifecycle/scheduler.py:1144` 附近 slow-context 路径，注入 `get_slow_var("self_cognition")`，与 session digest 并存（非替换）
- [x] 6.2 空槽位优雅回退：self_cognition 为空时 wake 正常进行（digest-only），不阻断
- [x] 6.3 验证 first-thought 治理：wake prompt 在任何 sense 工具调用前即包含结晶自我
- [x] 6.4 运行 event-flow / employee-console 相关测试确认 wake 组装未被破坏

## 7. 集成与边界验证

- [x] 7.1 端到端：idle 高能 → 遭遇事件 → 反应 → dream 结晶 → 下次 wake first-thought 携带结晶自我
- [x] 7.2 回归：`python3 -m pytest`，重点关注 memory / lifecycle / boundary 测试，无新增失败（既有环境/排序失败除外）
- [x] 7.3 分层边界复查：遭遇源/结晶逻辑在 `domain/memory`；runtime 与 SQLite 在 `infrastructure/`；prompt 上下文可审计留在 `domain/memory`/`domain/lifecycle`
- [x] 7.4 更新设计文档 §9 记忆系统，补充自我构成层（遭遇→反应→结晶→治理）说明
