# 2workbench/app.py
"""Game Master Agent IDE — 应用入口

启动流程:
1. 解析命令行参数
2. 初始化 QApplication
3. 应用主题
4. 初始化数据库
5. 启用 Feature 系统
6. 创建并显示主窗口
7. 启动 qasync 事件循环
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from foundation.logger import get_logger

logger = get_logger("app")

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _get_version() -> str:
    """从 pyproject.toml 获取版本号"""
    try:
        import tomllib
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "0.1.0")
    except Exception:
        return "0.1.0"


def parse_args():
    """解析命令行参数"""
    version = _get_version()
    parser = argparse.ArgumentParser(description="Game Master Agent IDE")
    parser.add_argument("--project", "-p", help="直接打开指定项目路径")
    parser.add_argument("--version", "-v", action="version", version=f"GMA IDE v{version}")
    parser.add_argument("--no-gui", action="store_true", help="无头模式（仅测试）")
    parser.add_argument("--theme", "-t", choices=["dark", "light"], default="dark", help="主题模式 (默认: dark)")
    parser.add_argument("--port", type=int, default=18080, help="HTTP 服务器端口 (默认: 18080)")
    parser.add_argument("--debug", "-d", action="store_true", help="调试模式")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="日志级别")
    parser.add_argument("--skip-selector", action="store_true", help="跳过项目选择器")
    parser.add_argument("--dev", action="store_true", help="开发模式（启用热重载）")
    return parser.parse_args()


def main() -> None:
    """主入口"""
    # 1. 解析命令行参数
    args = parse_args()

    from PyQt6.QtWidgets import QApplication
    import qasync

    # 2. 创建 QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Game Master Agent IDE")
    app.setOrganizationName("GMA")

    # 3. 设置日志级别
    if args.debug:
        args.log_level = "DEBUG"
    from foundation.logger import setup_logging
    setup_logging(level=args.log_level)

    # 4. 应用主题
    from presentation.theme.manager import theme_manager
    theme_manager.apply(args.theme)

    # 4. 显示项目选择器或直接使用命令行参数
    from presentation.dialogs.project_selector import ProjectSelector
    from presentation.project.new_dialog import NewProjectDialog
    from presentation.project.manager import project_manager

    selected_project = None

    # 如果通过命令行指定了项目路径，直接打开
    if args.project:
        project_path = Path(args.project)
        if project_path.exists():
            selected_project = project_path
        else:
            logger.error(f"项目路径不存在: {args.project}")
            return
    elif args.skip_selector:
        # 跳过项目选择器，直接创建空项目
        data_dir = PROJECT_ROOT / "data"
        data_dir.mkdir(exist_ok=True)
        selected_project = None
    else:
        # 显示项目选择器（像 Godot 一样）
        selector = ProjectSelector()
        create_new = False
        user_cancelled = False

        def on_project_selected(path: str):
            nonlocal selected_project
            selected_project = path

        def on_new_project():
            nonlocal create_new
            create_new = True

        def on_rejected():
            nonlocal user_cancelled
            user_cancelled = True

        selector.project_selected.connect(on_project_selected)
        selector.new_project_requested.connect(on_new_project)
        selector.rejected.connect(on_rejected)

        # 循环显示项目选择器，直到用户选择项目或创建新项目
        while True:
            selector.exec()

            # 检查用户是否点击了 X 按钮关闭对话框
            if user_cancelled:
                # 用户取消，退出程序
                return

            # 处理项目选择结果
            if create_new:
                # 显示新建项目对话框
                dialog = NewProjectDialog()
                if dialog.exec() != NewProjectDialog.DialogCode.Accepted:
                    # 用户取消新建，回到项目选择器
                    create_new = False
                    user_cancelled = False
                    continue

                project_data = dialog.get_project_data()
                name = project_data["name"]
                template = project_data["template"]
                project_dir = project_data.get("directory")

                if not name:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(None, "警告", "项目名称不能为空")
                    # 回到项目选择器
                    create_new = False
                    user_cancelled = False
                    continue

                try:
                    # 使用用户选择的路径，或使用默认路径
                    if project_dir:
                        data_dir = Path(project_dir)
                    else:
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
                    user_cancelled = False
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
    # 显式传入 schema 路径，避免 Foundation 层硬编码 Core 层路径
    schema_path = PROJECT_ROOT / "core" / "models" / "schema.sql"
    init_db(db_path=str(db_path), schema_path=str(schema_path))

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

    # 10. 启动事件循环
    from foundation.logger import get_logger
    logger = get_logger(__name__)

    # 9. 开发模式：启动热重载
    if args.dev:
        from foundation.hot_reload import create_reloader_for_project
        reloader = create_reloader_for_project(PROJECT_ROOT)
        reloader.start_background()
        logger.info("开发模式：热重载已启用")

    logger.info("Game Master Agent IDE 启动完成")

    loop = qasync.QEventLoop(app)

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
