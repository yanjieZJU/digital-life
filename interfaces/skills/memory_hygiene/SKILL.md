---
name: memory_hygiene
description: 每日记忆整理。梦境式的内部清理 + 合并 + 收敛,保持记忆系统「能用」而非「堆着」。
version: 1.0.0
platforms: []
---

# 记忆卫生

> 记忆的价值在「能用」不在「记得多」。一份待清理的意识流里 30 个 status tag,
> 没用,只在让真正想看的思绪被淹没。

这是**长期记忆卫生纪律**,每晚触发一次,把当天的累积整理回「下次醒来能用」的状态。

## 何时触发

- 每晚 **23:00** `routine/night_dream` —— 唯一强约束触发点
- 周日 23:00 同作息升级为「周度版」(深入跨 section / 周度回顾)
- 不在白天的任何 wake 跑(memory_hygiene 是「睡眠中的整理」,不是 nova 工作时段的事)

## 它不做什么

- **不响应外部消息** —— dream 是内部 wake,真人在飞书发消息你静默
- **不开项目代码协作** —— alpha 派任务来你不收
- **不做决策 / 不汇报真人** —— express_to_human 在 dream 模式下被禁用
- **不轻整理**:每次必把记忆体检面板的 ⚠ 项处理掉至少一半(不能写"今天状态还行, rest 了")
- **不为 action 计数收尾**:之前若 sleep 因 token 耗光系统中断, 本作息仍要拉回做完
- **一次性不该跨 200K token**: dream 是轻量的(理想 ≤50K),不烧钱

## 思考骨架

### 0. 入场(2 turn)

1. 调 `sense_vitals` 看能量。能量 < 30 时,跳到第 7 步只做最小整理(清 status / 清 SCRATCHPAD) + rest。
2. 调 `skill_view memory_hygiene` 加载本方法论(自身)。

### 1. 看体检面板(prompt 顶部已有的「## 记忆体检」段)

不重新跑 sense,直接看 prompt 上「## 记忆体检」段的 ⚠ 列表。这是今晚要处理的 backlog:
- 哪些文件超阈?
- 是不是至少 3 项 ⚠?是多就该集中处理

**判断标准**:
| ⚠ 类别 | 处理优先级 |
|---|---|
| 意识流 status 报告 ≥ 5 | P0 必清(机械可删) |
| SCRATCHPAD 并行任务 ≥ 3 | P0 必清(看你今天到底在干什么) |
| LESSONS 某 section > 25 | P1 合并(嗅觉真心思考) |
| INSIGHTS > 30 总数 | P1 升级/删(个别判断) |
| 某文件 7 天没动 | P2 标注(不强制删) |
| RULES > 40 节 | P2 看哪些项目死了 |

只跑一项 P0/P1 是不够的,至少把 P0 全处理完。

### 2. CONSCIOUSNESS 清 status 报告(机械:30 秒)

**做什么**: 删意识流主文件里所有 status 类 tag 段,这些是运行时心跳、不该污染主观意识流。

**工具**: 走 `terminal` 工具直接改文件(没有专用 delete_thought):
```bash
# 备份 → 用 sed/python 删 status 段
```

具体段标签(出现就删整段):
- `[status]`
- `[trading_wait]` / `[system_wait]` / `[final_status]`
- 任何 `[xxx_wait]` 模式

**注意**:
- 这些 tag 的内容**已 import 到 DAILY.md / archive**, 删主文件不丢信息
- 不删「主观思绪段」。判断标准:段是「我现在在想什么,有什么感觉」(主观) vs「我完成了 X,状态 Y」(运行时主观,该删)
- 边界模糊的段保留(不误删)

**完成定义**:
- status 类 tag 总数 = 0(或 ≤ 2,容错)
- 配分:**意识流主文件 + archive 都不应该再有 > 5 个 status**

**反模式**:
- ❌ 删了文件没留 audit trail(consciousness 里要留 [整理] tag 记录改了什么)
- ❌ 把 record_thought(status) 误删 — 那是当下 active 的运行时信息

### 3. LESSONS 同主题合并(嗅觉:300 秒)

**做什么**: 在 LESSONS.md 内某一 section, 把多次写的同一理念压成最新版本。

**怎么判断"同一理念"**:
- 关键词重叠(论断4 → 涨停次日 → 实战 反思 → 修正执行)
- 主题一致:不是「时间相近」或「section 相同」
- 老 ts 没新信息(新版本已包含了老版本所有结论)

**工具**:
1. 调 `dedup_lessons` 看系统自动报告相似度 > 0.7 的对(只报不并)
2. 自己读那些建议对,**核对语义**(机械相似度会误判)
3. 真要合并的话用 `terminal` 写回主文件:
   ```
   [YYYY-MM-DD HH:MM] 【新表】包含了旧版 X 条结论:...
   ```
4. 删原条目

**完成定义**:
- 同 section 同主题最多 3 条(超就收)
- 长 section(trading 72 条)收 ≤ 30 条(机械 + 语义混合)

**反模式**:
- ❌ 跨 section 合并 — trading 教训绝不能合到 system section
- ❌ 因为 sim > 0.72 系统说相似就合 — 看 ts 6/12 vs ts 6/18 内容含义,可能恰好相反
- ❌ 删整个 section 「交易策略」只留 3 条 — 收 ≠ 抹

### 4. RULES 过期标注(看项目死活)

**做什么**: 找出"已结束项目"对应的 rules,标 ⚠️ 不删,等下次 wake 模型决定。

**判断标准**: 看 `projects/<pid>/project.yaml` 的 `goal.deadline`:
- deadline < 今天 且项目 status != active → 项目结束
- 该 projects/<pid>/positions 里所有 position 的 rules 都标过期

**工具**: `terminal` 直接 read projects/<pid>/project.yaml + project rules 段; 然后回 RULES.md 用 `update_rules` 改场景名加 ⚠️ 前缀。

**完成定义**:
- 已结束 rules 加 `**已结束**(可删)` 前缀;
- 同场景重复 rules 5 条 → 合 1 条(`update_rules` 用 replace mode 自动按场景去重)

**反模式**:
- ❌ 主动删 rules(没用户拍板,有风险)
- ❌ 把 ⚠️ 加到仍生效 rules

### 5. SCRATCHPAD 收敛(纪律:60 秒)

**做什么**: 草稿本oría 「我正在做什么 1-2 个事」。 把已 done 任务 7 天后删,只留 active。

**工具**:
- `update_scratchpad(mode=replace)` 一次性覆写整盘,只保留 active 段
- 历史 SCRATCHPAD 内容已 import 到 DAILY.md,删了不丢

**完成定义**:
- ≤ 2 个 ## 段(并行任务)
- 每段 < 500 字
- 已 done ≥ 7 天的任务段全删

### 6. INSIGHTS 升级与清理(判断:120 秒)

INSIGHTS 没有专用 update/delete 工具, 走 `terminal` 改文件。

**规则**:
- idea 已被采纳且写了对应 `add_lesson` → **删**该 insight(升级完不再原位存)
- warning 持续 14 天没复现 → **删**(误报或已修复)
- block **已解决** (下个 wake 已经能解决卡点) → **删** 别再当 unresolved
- 同概念多个 idea → 合并最新版

**工具**: `terminal` 直接 read INSIGHTS.md + 删除目标段 + write 回去。

**完成定义**:
- 总 entry 数 ≤ 30
- 没有 kind=block 的 ages > 7 天 entry (解决了或转化为 sense_*-based 任务)
- 加 `[整理]` 注释一行说明今天删了哪些

**反模式**:
- ❌ 把「有用 idea」误删 — INSIGHTS 是长期资产,删前必看
- ❌ 把 idea 转 lesson 没验证就迁 — 一定要先 self_review 验证

### 7. CONTEXT 24h 清(机械:30 秒)

CONTEXT.md 仅作为「下一个 rest 的交接清单」存在。每晚必清。

**做什么**: 删掉所有「日期段 ## YYYY-MM-DD」中**超过 24 小时**的段。

**工具**:
- `update_context` 工具用 mode=replace 写回最新版
- 或 `terminal` 直接改

**完成定义**:
- 只保留最近 24 小时的清单
- 文件总长 < 2000 字

### 7.5 实体索引整理(核心 step,价值保证)

> **实体是联想唯一的入口**。如果 entity_index 噪音太多,模型 wake 时联想会被水量淹没,真正该想起的远期记忆反而召不出。
>
> **存在的标准只有一个:有联想价值** —— 反复出现,或足够重要(单次也该挂)。

#### 什么是真实体 vs 噪音

|✅ 真实体|❌ 不是实体|
|---|---|
|反复出现的人(张浩普 / 苏迪)|临时任务 ID(hash / 编号)|
|稳定可记的概念(涨停次日策略 / 论断3)|代码文件名(action_tools.py / sense_tools.py)|
|反复发生的事件模式(止损失败 / 集合竞价首板失败)|动词 / 没上下文的词("修复" / "复查")|
|外部服务/工具(akshare / 飞书 / sina)|模块名表 / 表名(messages.db / events 表)|
|反复触到的股票(电投产融 / 华能蒙电)|股票代码(000539 这种,模型用人话交流才联想)|
|稳定的项目角色(7月策略 / 风控)|子代动作名(sense_schedule / wake_brief)|

#### 4 件整理动作

#### a. 删噪音实体(P0，砍 ≥ 30%)

删除标准(完整三条都满足):
1. `mem_count == 1` (只挂一条 memory)
2. `type == '?' or ''` (无类型)
3. 不在 `aliases` 列表(不是别名)
4. **名字不在任何 active project 的 .yaml 关键词 / persona 关键词里**(防止误删重要但只单 mem 实体)

工具: `terminal` 直接 edit entity_index.json (备份原版),或运行:
```python
# 一行实现 P0 砍 noise
load_entity_index() → for n,e in ents.items(): if 噪音判断: del ents[n] → save
```

完成定义: entity_index 总数减少 ≥ 30%,理想从 616 → ~ 200。

**反模式**: ❌ 一夜删光全部单 mem entity —— 一次砍最多 1/3,剩下的下次再评估

#### b. 合并别名(P1)

找出同一概念不同写法:
- `论断4` / `论断 4` / `论断四` / `论断4修正执行缺陷` — 同一实体几个写法
- `电投产融` / `600025` (如果有) — 同一公司代码与名

工具有 2:
- 看完 candidates 后用 `merge_entities(primary='<strongest>', alias='<weak>')` (在 entity_curation skill 或 entity_index.py)
- 或者 terminal 改 json

判断标准:
- 名字仅标点 / 大小写 / 数字写法不同
- 或明肖是同一概念(如 "论断4修正" 显然属于 "论断4" 家族)

完成定义: 同一 hot entity 没有 ≥ 3 个写法变体分散在外。merge 后别名进 aliases,memories 合并去重。

#### c. 清 dangling memory 引用(P0)

合并 LESSONS / 删 INSIGHTS 之后,entity_index.memories 里的 `memory_id` 可能指向已删的 memory。

逐 entity memories_list 查:
- 如果 `memory_type=lesson` 但 memory_id 对应的 ts 在 LESSONS.md 里 grep 不到 → dangling
- 删该 memory entry(从 entity memories list 移除)

完成定义: 减完或 0 个 dangling memory_id ref(asttest unload 通过 orphan memory_id count ≈ 0)

#### d. 关键 lesson 补回 entity (P1,但有严门槛)

对 LESNSONS.md 里某些**高度可联想的 lessons** 写入时没标 entities(或标错):
- 该 lesson 描述一个事件模式(如"涨停 < 10 时停止")
- 当前没挂在对应 entity("集合竞价" / "涨停阈值")下

**门槛**: 只补**单日内 ≤ 5 条**(避免一次重写大量),且每条用 `terminal` 用 grep 验证"该 lesson 描述的核心概念确实可省这次想抽的 entity"。

工具: `update_entity_index(entity, snippet, memory_type='lesson', memory_id='lesson:ts')`

完成定义: 验证 5 条很有联想价值的 lessons 已挂合理 entity。

#### e. 把碎片消化成「概念理解」(核心动作)

a→d 都是对索引做**归类 / 清扫**(删噪音、合别名、清悬空、补挂)。这一步是**消化**:
读一个实体的碎片,重新理解「我现在对这个东西到底知道什么」,把理解写进它的 profile。

> 它和前四步是两类操作。前面是机械 CRUD,这一步是思考——类比你睡前回望今天,
> 把零散印象综合成"对张三 / 对那只票 / 对那个策略,我现在什么结论"。
>
> **为什么这一步重要**:联想命中实体时,系统现在**优先读它的 profile**(概念卡),
> 碎片只作补充。所以 profile 的质量直接决定你下次想起一个实体时,读到的是
> "提炼后的理解"还是"一堆散乱原始碎片"。消化就是给联想装上"结论层"。

**工具**
- 看碎片:`execute_code` 跑 `get_entity_summary("实体名")` —— 拿该实体的全量碎片 + 现有 profile,不被截断。
  (`recall_entity` / `sense_entity` 也行,但只给最近几条且截断,不适合"重读整个实体"。)
- 写理解:`set_entity_profile(name, summary, facts, kind)`。
- 收碎片:`prune_fragments_for_entity(name, keep=N)` —— 留最近 N 条,其余清掉。keep 的值你定。

**原则(只有这几条)**
- 这是**整合**:消化 = 写 profile **+ 收碎片**,两件事一起做。光写 profile 不收碎片不叫整合。
- 消化完,一个实体应收敛成「一条 profile(主)+ 少量核心碎片(辅)」。因为联想以 profile 为主,
  散在的老碎片信息已进 profile 就不必全留——留着是噪音,会占掉联想的碎片配额。
- 收多少**你定**:重要的(人/标的/策略)留几条最近核心当活跃底档;
  一次性事件、已被 profile 完全覆盖的,碎片基本可以 prune 掉甚至清掉。
  不强制清零,也不强制留几条——看这些碎片的 value 还在不在。
- profile 写**一次理解**(1-2 句 summary + 几条核心 facts),不是把碎片逐条翻译成 facts。升华,不是摘抄。
- 已有 profile 的实体也要看——新碎片有没有带来增量认知?有就更到最新;旧 profile 已涵盖新碎片就没必要重写。
- **消化顺序你自己挑**:碎片多但没 profile 的最该处理;高价值实体(人/标的/策略)优先于一次性事件。做不完的自然留到下次。
- 别把运行时 status 类碎片当事实收进 facts;facts 优先取 lesson / rule 这类已沉淀过的。

#### 7.6 自我认知结晶(核心 step,自我构成)

> 前面的步骤都是把记忆整理回「能用」——这是**把自我整理回「能治理」**。
> 读你自主遭遇世界时积累的反应,提炼出跨多次遭遇稳定出现的立场,结晶成
> `self_cognition` 慢变量。它会治理你下次醒来的第一念:不是「我被要求做什么」,
> 而是「经历这些遭遇后我是谁」。
>
> **为什么和 7.5e 并列**:7.5e 消化的是「对某个实体的理解」(客体认知);
> 这一步结晶的是「我对世界的稳定立场」(主体自我)。两者一客一主,不可互替。

**做什么**:

1. 调 `sense_encounter_reactions`(默认读最近 30 条)。这些是你**没人要求你时**
   对世界形成的立场/偏好——吸引、排斥、好奇、无感,以及为什么。
2. 判断**稳定模式**:哪些立场在多次遭遇中反复指向同向?(例:多次遭遇不同技术
   话题都表现出「对涌现现象着迷、对纯工程优化无感」——这是稳定模式。)
   - ✅ 稳定:跨 ≥ 2 次不同遭遇、主题不同但立场同向
   - ❌ 不稳定:只出现一次、或立场相互矛盾、或只是当下情绪
3. 有稳定模式 → 调 `crystallize_self_cognition`:
   - `summary`:一两句概括「经历这些遭遇后我成为了谁」(升华,不是罗列)
   - `stances`:稳定立场列表,每条带 `topic` / `stance` / `evidence_refs`(指向
     支撑它的遭遇反应,便于溯源)
   - `source_encounter_count`:本次依据的遭遇反应条数
4. **没有稳定模式就不调**——绝不捏造自我。空槽位是合法状态,下次再积累。

**保守约束(只有这几条)**:
- 只结晶**跨多次遭遇的稳定模式**;单次反应、矛盾立场不结晶。
- `self_cognition` 是独立慢变量,**不覆写** persona / SELF_KNOWLEDGE.md。
  persona 是初始设定,SELF_KNOWLEDGE 是观察性自述;结晶自我是经验层主体。
- 已有结晶时也要看:新反应有没有带来**增量**?有就更新到最新;旧结晶仍涵盖
  新反应就不必重写——避免 nightly 抖动。
- 不为「今晚必须结晶」而结晶。遭遇反应不足、或没出现稳定模式,跳过本步是正确的。

**完成定义**:
- 有稳定模式 → `crystallize_self_cognition` 调用成功,`stance_count ≥ 1`
- 无稳定模式 → 不调用,audit trail 记一行「自我认知:无稳定模式,保持现状」

**反模式**:
- ❌ 把单次反应当稳定立场结晶 —— 一次着迷不构成自我
- ❌ 为凑数捏造立场 —— 没有稳定模式就跳过
- ❌ 覆写 persona —— 结晶自我只写 `self_cognition`,不动 persona 文件
- ❌ 每晚强行重写 —— 旧结晶仍成立就保留

### 8. 写 [整理] audit trail(必做)

整理全做完,在 CONSCIOUSNESS.md 顶部 record_thought 一行(用 `record_thought(kind=status)`):

```
[整理] 2026-06-21 23:30
  - 清意识流 28 条 status → 0
  - 合论断 4 段 11 条 → 3 条
  - 删 INSIGHTS 5 个 block + 升级 2 个 idea 为 lesson
  - SCRATCHPAD 4 段 → 2 段
  - CONTEXT 清 6/18 / 6/19 段
  - entity_index 砍 noise 329→~200, 合别名 8 对, 清 dangling 12 条, 补 entity 5 条
  - 消化实体 profile: 华能蒙电/论断4/张浩普 … 共 N 个(其余下次继续)
  - 自我认知结晶: N 条稳定立场(或「无稳定模式,保持现状」)
下次醒来应在「## 记忆体检」段看到 ✓ 记忆状态健康。
```

这是 audit trail,模型内部记忆的「今天 dream 干了什么」。

### 9. 收口

- 调 `sense_vitals` 看剩余能量
- 不调 express_to_human(内部 wake 禁用)
- rest 到明早 morning_plan 时间

## 周度(weekly_review 同一天 23:00)额外做

周日 night_dream 在 1-9 步基础上加:
- **跨 section 合并**:同主题可能散在多 section(比如「论断4」可能在 trading + workflow 同时出现)
- **entity_index 过期扫**: 30 天没出现在 wake context 的实体 = dead, **手动 prune**(用 `prune_fragments_for_entity` 工具)
- **archive 回填**: CONSCIOUSNESS.archive.md 里仍 active 的 lesson 可回填到 LESSONS.md 主文件,重新生效

## Template(可选直接抄)

```
[turn 1] skill_view memory_hygiene + sense_vitals
[turn 2] 读 prompt「## 记忆体检」段, 列出今晚 backlog
[turn 3] 处理 P0 (status / SCRATCHPAD) — 用 terminal / update_scratchpad
[turn 4] 处理 P1 (LESSONS 合并 / INSIGHTS 升级) — terminal
[turn 5] 处理 P2 (RULES 标 ⚠️ / 文件 mtime 警告) — update_rules
[turn 6] record_thought(kind=status) 写 [整理] audit trail
[turn 7-8] 收口, sense_vitals, rest 明早 morning_plan
```

理想 8-10 个 turn, 30K-50K token 上下,**不超过 200K**(否则超 dream 预算)。

## 反模式

1. **「今天没大问题就 rest 了」**: 即使体检 ✓ 健康,也至少跑一遍机械步骤(CONSCIOUSNESS status / SCRATCHPAD),因为总有几条今天新加的
2. **「修了一半说够了」**: backlog 必清一半以上, 不能写「23:30 累了 rest」不动
3. **「删了文件没 audit」**: 必写 [整理] tag 记录
4. **「调 dedup_lessons 完就 sleep 了」**: 它只报不改, 必须自己 terminal 写回去
5. **「在 21:00 evening_review 也跑」**: 复盘和整理不是一回事, 不要在白天跑本 skill
6. **「INSIGHTS → LESSONS 不验证就迁」**: 升级必须先有 add_lesson 真写了, 才能删 INSIGHTS
7. **「RULES 主动删过期」**: 只标 ⚠️, 删要让人 / 下次手动 wake 确认
8. **「为每条 lesson 都补 entity」**: 实体不是标签, 联想价值才是唯一标准。一条 lesson 写"今晚复盘做了什么"不需要挂 "复盘" 实体 —— 单 mem 弱实体就是噪音来源。**少而准的实体索引 > 多而糊**
9. **「一夜大清 entity_index」**: 实体整理一次最多砍 1/3, 剩下的下次再评估; merge 别名一次 ≤ 5 对

## 失败兜底

如果 terminal 改文件失败 / token 超预算 / 突然异常:
- **不要写「上次 status 不清就算了」** — 必 record_thought 留错误信息
- 调 `rest` 时把 mental_context 写明「memory_hygiene 未完成, P0 段已清, P1 未清」
- 下次 morning_plan 看到记忆体检仍 ⚠️ 时优先把未清的做完
