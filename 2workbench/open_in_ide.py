# 在 IDE 中打开 Agent 项目
from __future__ import annotations

import sys
from pathlib import Path

# 确保项目路径
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tempfile
from presentation.project.manager import project_manager

# 使用之前创建的临时目录
tmp_dir = r'C:\Users\25514\AppData\Local\Temp\tmp6ak6sgk3'
project_path = Path(tmp_dir) / 'my_first_agent.agent'

if project_path.exists():
    # 打开项目
    config = project_manager.open_project(project_path)
    print(f'✅ 已在 IDE 中打开项目: {config.name}')
    
    # 加载到编辑器
    from presentation.main_window import MainWindow
    from PyQt6.QtWidgets import QApplication
    
    # 获取主窗口实例
    app = QApplication.instance()
    if app:
        for widget in app.topLevelWidgets():
            if isinstance(widget, MainWindow):
                # 加载图编辑器
                graph = project_manager.load_graph()
                widget.center_panel.show_graph_editor(graph)
                
                # 加载 Prompt 编辑器
                prompts = {}
                for name in project_manager.list_prompts():
                    prompts[name] = project_manager.load_prompt(name)
                widget.center_panel.show_prompt_editor(prompts)
                
                # 显示工具管理器
                widget.center_panel.show_tool_manager()
                
                print('✅ 已加载编辑器界面')
                break
else:
    print(f'❌ 项目路径不存在: {project_path}')
