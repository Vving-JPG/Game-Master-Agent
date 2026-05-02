# 创建简单 Agent 项目测试脚本
from __future__ import annotations

import sys
from pathlib import Path

# 确保项目路径
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from presentation.project.manager import project_manager
import tempfile

# 创建临时目录用于测试项目
tmp_dir = tempfile.mkdtemp()
print(f"使用临时目录: {tmp_dir}")

# 创建项目
path = project_manager.create_project('my_first_agent', template='trpg', directory=tmp_dir)
print(f'✅ 项目已创建: {path}')

# 打开项目
config = project_manager.open_project(path)
print(f'✅ 项目已打开: {config.name}')

# 加载图定义
graph = project_manager.load_graph()
node_count = len(graph["nodes"])
print(f'✅ 图定义节点数: {node_count}')

# 列出 Prompts
prompts = project_manager.list_prompts()
print(f'✅ Prompts: {prompts}')

# 创建自定义 Prompt
project_manager.save_prompt('my_custom_prompt', '这是一个自定义的 Prompt 模板\n\n玩家输入: {input}')
print('✅ 已创建自定义 Prompt')

print()
print('=' * 60)
print('🎉 简单 Agent 项目创建成功！')
print('=' * 60)
print(f'项目路径: {path}')
print(f'项目名称: {config.name}')
print(f'模板类型: {config.template}')
print()
print('项目结构:')
print('  📁 prompts/        - Prompt 模板')
print('  📁 skills/         - 技能定义')
print('  📁 npcs/           - NPC 配置')
print('  📁 locations/      - 地点配置')
print('  📄 graph.json      - LangGraph 图定义')
print('  📄 config.json     - 项目配置')
print('=' * 60)
