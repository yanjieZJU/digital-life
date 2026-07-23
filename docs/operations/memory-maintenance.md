# Memory Maintenance

本手册用于维护每个数字生命实例的记忆质量。架构机制见
[../architecture/memory-lifecycle-design.md](../architecture/memory-lifecycle-design.md)。

## 何时执行

- `weekly_review` 完成后进行完整维护。
- `initiative` 唤醒且 `check_memory_health` 报警时进行定向维护。
- `self_iteration` 聚焦记忆时，至少执行健康检查和结果记录。

## 标准流程

1. 运行 `check_memory_health`，确认 RULES、LESSONS、SCRATCHPAD 和
   CONSCIOUSNESS 的体积、重复和异常。
2. 运行 `dedup_lessons`，合并高相似经验；只有重复验证且违反会造成损失的经验才晋升为规则。
3. 用 `sense_rules` 检查重复、冲突和长期未触发规则。
4. 用 `sense_entity` 查看实体热力图，使用 `merge_entities` 合并重复实体。
5. 检查 `CONSCIOUSNESS.archive.md`、`DAILY.archive.md` 和 scratchpad 是否需要整理。
6. 记录发现、调整和剩余风险，不直接批量改写运行期记忆。

## 召回质量

检查 session 日志中的 `[实体触发记忆]` 和 `[快速联想]`：

- 有帮助的召回是否准确、及时。
- 噪声召回是否需要调整实体、别名或阈值。
- 预期出现但缺失的记忆是否尚未建立实体关联。

日志位于 `apps/{instance}/data/sessions/`。所有实例数据都是 mutable runtime
data；普通开发任务不得修改。

## 原则

- 证据先行，每次只处理少量明确问题。
- 不为追求整洁删除仍有维护价值的经验。
- 不把实例运行期数据提交到仓库。
- 架构或工具行为变化时，同步更新记忆生命周期设计文档。
