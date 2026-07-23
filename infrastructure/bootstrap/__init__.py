"""Instance bootstrap module.

实例创建逻辑的正式归属层（不是 scripts/ 本地工具）。由：
  - master 启动时 _ensure_default_instance() 调
  - 控制台 POST /api/system/instances 调
  - CLI python -m infrastructure.bootstrap.instance 调
"""
