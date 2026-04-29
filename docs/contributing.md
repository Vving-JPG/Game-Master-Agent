# 贡献指南

## 代码规范

- UTF-8 编码，中文注释
- PEP 8 风格
- 每个模块必须有 pytest 测试
- 使用 `uv` 管理依赖

## 添加新工具

1. 在 `src/tools/` 创建工具函数
2. 在 `src/tools/tool_definitions.py` 添加 Schema
3. 在 `src/tools/__init__.py` 注册
4. 编写测试

## 添加新插件

1. 在 `src/plugins/` 创建 Python 文件
2. 继承 `GamePlugin` 基类
3. 实现需要的事件钩子
