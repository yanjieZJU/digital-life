# Shared 空间说明

跨实例共享的代码、能力、方法论。任何实例写到这里，所有实例都能引用。

## 子目录

- `capabilities/` — 通用能力模块（OCR / TTS / 数据采集 / 算法库）
- `tools/` — 注册为模型可调工具的 Python 模块（每个文件一个工具）
- `skills/` — 跨项目通用的方法论

## 注册机制

模型调 `register_tool(name=..., scope='shared', code=...)` 时工具文件写到 `tools/`，
所有实例的 instance_tools 表自动注册该工具，但**需要 app.yaml 显式 enable 才真正可用**。

`skills/` 同理 — 模型调 `register_skill(scope='shared', ...)` 写到这里，
要在实例 app.yaml 的 skills 列表加 name 才生效。

## 谁可以写到 shared/

模型可以写到 `capabilities/` 子目录（贡献能力），但写到 `tools/` / `skills/`
要走 `register_*` 接口（确保 schema + handler 完整）。
