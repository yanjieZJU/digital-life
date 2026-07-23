# apps/

数字生命实例的私有目录。每个实例是一个 UUID 子目录：

```
apps/
├── <uuid-1>/        # 实例 1（不入 git，私有）
│   ├── config/app.yaml       # messenger.app_id / group_chat / skills 等
│   ├── config/secrets.env    # FEISHU_APP_SECRET / GLM_API_KEY（不入 git）
│   ├── persona/LIFE_PERSONA.md
│   ├── data/state.db         # 运行时数据（含 contacts 表）
│   └── ...
└── <uuid-2>/        # 实例 2
```

## 创建新实例

```bash
digital-life init --display-name "MyBot"
```

会：
1. 在 `apps/<new-uuid>/` 下生成目录
2. 从 `config/templates/` 复制 README/persona/profile/skills 模板生成 `config/app.yaml`
3. 初始化 `state.db` 全表 schema

## 实例发现

注册表由 runtime **动态扫描** `apps/*/config/app.yaml` 的 `display_name` 字段构建
（见 `infrastructure/config/__init__.py:_rebuild_registry_from_apps`），新增实例后无需任何注册步骤，`digital-life restart` 即被发现。

`display_name` 用于：
- chat_stream 中作为「我自己」的名字
- 前端管理台的实例标签
- `grep "instance_id[:8]"` 日志定位

## 实例隐私

实例目录不入 git。`apps/<id>/config/secrets.env` 内含飞书 `FEISHU_APP_SECRET`、`GLM_API_KEY`
等敏感凭据,不应公开。如需团队协作,可手工同步或用加密通道分发。
