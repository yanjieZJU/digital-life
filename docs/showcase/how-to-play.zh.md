# 如何玩转数字生命

## 上手

假设你已经 [快速开始](../../README.md#快速开始) 里 init + start 了。

打开 `http://localhost:8642` 进控制台。每个实例都有 Overview / Sessions / Memories / Todos / Calendar / Persona / Config 等标签页。

先到 Config 填好模型 + 飞书凭证（见 [飞书配置](../operations/feishu-setup.md)），重启。Overview 通道状态卡显示绿色 = 接入了。

去飞书群发条消息，几十秒内收到回复。

## 日常

### 对话

群里说话不一定 @ 它 —— 它会自己判断该不该回。@ 是高优先级信号但不是唯一。

你不说话时，它也可能主动活动：按作息节奏定时唤醒、精力充足时主动探索、检测到异常时告警。

### 技能

Skills 标签页里 toggle 订阅。想加自定义技能，在 `shared/skills/<名>/SKILL.md` 写好，重启后自动出现在列表。

### 人设

Persona 标签页直接改。保存后下一次 wake 生效。

### 看它在做什么

- **Overview**：状态 / 能量 / 最近 wakes / 待办 Top
- **Sessions**：每个 wake 的完整 turns + 工具调用 + LLM 输入
- **Memories**：意识流 / 日记 / 教训 / 洞察 / 联想图谱
- **Calendar**：作息节奏 + 闹钟，可视化。

## 进阶

### 项目

Projects 页建项目：定义目标 / deadline / 岗位，把实例分配到岗位。不挂项目的实例只是聊天 bot；挂了项目，它们才分工干活。

### 待办

Todos 页。待办三个来源：实例自己拆出来的、你在群里交代的、项目级共享的。当前没做完的下次 wake 会接着做。

### 多 Agent 协作

一个实例是单兵，两个以上是组织。群消息会被每个 bot 收到（飞书服务端 fan-out），各自决定谁回。加上项目的岗位分工，它们能协作完成一件事。

加第三个实例：`digital-life init --display-name <名>` 建好，然后 Config 里配凭证，重启。

### 事件

数字生命靠事件活着。System → Events 页可以看到所有事件类型（消息 / 定时 / 主动性 / 阈值等）。自定义事件接入需要写适配器调 `emit_event`，这是开发者向的操作。

## 出问题了

| 现象 | 去哪看 |
|---|---|
| Overview 显示「异常」 | 红色 banner 有具体原因。Config 改完重启 |
| 通道灰灯 | Config 检查凭证。飞书改了 App Secret 要重启；微信失效了重新扫码 |
| 没回复 | `digital-life logs -f` 看日志有没有 Ingress message / wake |

实例异常后自动恢复：下一次 wake 模型调用成功就消失。

要重置某个实例：停止 gateway → 备份 `apps/<uuid>/` → 删掉 data/*.db → 重启。记忆会丢，人设保留。
