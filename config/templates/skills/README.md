# {DISPLAY_NAME} Skills

本目录放置**实例专属** skill 或 skill 配置。

系统级 skill（跨实例共享）定义在仓库根的 `interfaces/skills/`，不在此处。

## 何时放在这里

- 仅本实例启用的 skill
- 共享 skill 的本实例 override 配置
- 实验/未成熟 skill 的草稿

## 推荐路径

- 单文件 skill：直接放 `<skill_name>.md`
- 多文件 skill：建目录 `<skill_name>/` 内放 `SKILL.md` + 资源
