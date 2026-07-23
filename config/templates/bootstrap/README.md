# Bootstrap

本目录放置实例**启动时**执行的自定义代码或 hook。

## 用途

- 注册实例专属的工具
- 启动时跑一次的环境初始化（如读外部 API 暖数据）
- 自定义注入逻辑

## 命名约定

- `<feature>.py` — 模块，被运行时 import
- `README.md` — 本实例 bootstrap 的说明（团队成员阅读用）
