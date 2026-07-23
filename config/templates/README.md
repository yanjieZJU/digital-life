# {DISPLAY_NAME}

本目录是这个数字生命实例（{DISPLAY_NAME}）的私有工作空间。

## 目录结构

- `persona/LIFE_PERSONA.md` — 系统人设 prompt（最重要，决定实例的性格和行为底色）
- `profile/` — 个人资料（照片、声音等可选素材）
- `config/app.yaml` — 实例启动配置（messenger.app_id / group_chat / skills）
- `config/secrets.env` — 实例级敏感凭证（`apps/<id>/config/secrets.env` 中的相对路径：FEISHU_APP_SECRET / LLM_API_KEY，不入 git）
- `skills/` — 实例专属 skill 配置（系统级 skill 在 `interfaces/skills/`）
- `bootstrap/` — 实例启动时定制的注入点（hooks、自定义初始化代码）
- `data/` — 运行时所有数据库和缓存（不入 git）

## 运行时数据（自动生成，请勿手工修改）

- `data/state.db` — 主状态库（events / vitals / affairs / alarms / contacts 等）
- `data/sessions.db` — SessionDB 其实也在 state.db 中，这里是历史残留
- `data/tasks/tasks.db` — 实例的私人任务池
- `data/memories/` — 残留记忆文件（DAILY / SCRATCHPAD / consciousness 等）
- `data/sessions/` — 每次对话的 JSON 转录
- `data/logs/digital-life.log` — 本实例的运行日志

## 下一步

1. 编辑 `persona/LIFE_PERSONA.md` 填写人设
2. 编辑 `config/app.yaml` 配置飞书路由
3. 在前端管理台「实例」面板启用本实例（或 `digital-life restart`）
