# 飞书配置

在 [飞书开放平台](https://open.feishu.cn/app) 创建自建应用，配置四处。

## 1. 权限

应用详情 → 权限管理 → **导入权限配置**，粘贴以下 JSON：

```json
{
  "scopes": {
    "tenant": [
      "im:chat",
      "im:chat.access_event.bot_p2p_chat:read",
      "im:chat.members:bot_access",
      "im:chat:readonly",
      "im:message",
      "im:message.group_at_msg.include_bot:readonly",
      "im:message.group_at_msg:readonly",
      "im:message.group_msg",
      "im:message.p2p_msg:readonly",
      "im:message.reactions:write_only",
      "im:message:readonly",
      "im:message:send_as_bot",
      "im:resource"
    ]
  }
}
```

> 只含数字生命实际需要的权限。`im:message.reactions:write_only` 是可选的表情收条。

## 2. 事件订阅

应用详情 → 事件与回调 → 选「长连接」（不需公网回调地址）→ 开启 `im.message.receive_v1`。

## 3. 机器人

应用详情 → 应用功能 → 启用机器人。

## 4. 发布 + 加群

创建版本并发布。

在飞书群聊 → 右上角设置 → **群机器人** → 添加机器人 → 选择你刚发布的自建应用 bot。不是通过联系人拉人，是通过群设置里的"群机器人"入口添加。

## 填入实例

实例 Config → 飞书 → 填 App ID + App Secret → 重启。

## 关于 @ 与跨实例消息

**同一服务下的多个实例**（都跑在同一个 gateway 上）：群消息不 @ 也能互相收到，因为内部做了消息广播适配。

**不同服务的实例**（比如你朋友的独立部署）：飞书服务端会过滤掉非 @ 的机器人消息，别人家的 bot 发的消息你 @ 不到就收不到。这是飞书平台限制，无法突破。所以跨服务协作时必须 @。
