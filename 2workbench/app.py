# 2workbench/app.py
"""Game Master Agent IDE — 应用入口

启动流程:
1. 初始化 QApplication
2. 应用主题
3. 初始化数据库
4. 启用 Feature 系统
5. 创建并显示主窗口
6. 启动 qasync 事件循环
"""
from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    """主入口"""
    from PyQt6.QtWidgets import QApplication
    import qasync

    # 1. 创建 QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Game Master Agent IDE")
    app.setOrganizationName("GMA")

    # 2. 应用主题
    from presentation.theme.manager import theme_manager
    theme_manager.apply("dark")

    # 3. 显示项目选择器（像 Godot 一样）
    from presentation.dialogs.project_selector import ProjectSelector
    from presentation.project.new_dialog import NewProjectDialog
    from presentation.project.manager import project_manager
    
    selector = ProjectSelector()
    selected_project = None
    create_new = False
    
    def on_project_selected(path: str):
        nonlocal selected_project
        selected_project = path
        
    def on_new_project():
        nonlocal create_new
        create_new = True
        
    selector.project_selected.connect(on_project_selected)
    selector.new_project_requested.connect(on_new_project)
    
    # 循环显示项目选择器，直到用户选择项目或创建新项目
    while True:
        selector.exec()
        
        # 4. 处理项目选择结果
        if create_new:
            # 显示新建项目对话框
            dialog = NewProjectDialog()
            if dialog.exec() != NewProjectDialog.DialogCode.Accepted:
                # 用户取消新建，回到项目选择器
                create_new = False
                continue
                
            project_data = dialog.get_project_data()
            name = project_data["name"]
            template = project_data["template"]
            
            if not name:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(None, "警告", "项目名称不能为空")
                # 回到项目选择器
                create_new = False
                continue
            
            try:
                # 指定在 data 目录下创建项目
                data_dir = PROJECT_ROOT / "data"
                data_dir.mkdir(exist_ok=True)
                selected_project = project_manager.create_project(name, template, directory=str(data_dir))
                # 创建成功，跳出循环
                break
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "创建失败", f"创建项目失败: {e}")
                # 回到项目选择器
                create_new = False
                continue
        elif selected_project:
            # 用户选择了已有项目，跳出循环
            break
        else:
            # 没有选择项目，回到项目选择器
            continue

    # 5. 初始化数据库
    from foundation.config import settings
    from foundation.database import init_db
    db_path = PROJECT_ROOT / "data" / "default.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    init_db(db_path=str(db_path))

    # 6. 启用 Feature 系统
    from feature import (
        feature_registry,
        BattleSystem, DialogueSystem, QuestSystem,
        ItemSystem, ExplorationSystem, NarrationSystem,
    )
    feature_registry.register(BattleSystem(db_path=str(db_path)))
    feature_registry.register(DialogueSystem(db_path=str(db_path)))
    feature_registry.register(QuestSystem(db_path=str(db_path)))
    feature_registry.register(ItemSystem(db_path=str(db_path)))
    feature_registry.register(ExplorationSystem(db_path=str(db_path)))
    feature_registry.register(NarrationSystem(db_path=str(db_path)))
    feature_registry.enable_all()

    # 7. 打开选中的项目
    if selected_project:
        try:
            project_manager.open_project(selected_project)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "错误", f"打开项目失败: {e}")
            return
    
    # 8. 创建主窗口
    from presentation.main_window import MainWindow
    window = MainWindow()
    window.show()

    # 8. 启动事件循环
    from foundation.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Game Master Agent IDE 启动完成")

    loop = qasync.QEventLoop(app)

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
