"""打包服务 — Feature 层

负责项目打包逻辑，通过 EventBus 与 Presentation 层通信。
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from foundation.event_bus import event_bus, Event
from foundation.logger import get_logger

logger = get_logger(__name__)


class PackagingService:
    """项目打包服务

    监听 UI 发出的打包请求，执行 ZIP 打包并返回结果。
    """

    def __init__(self):
        self._setup_listeners()

    def _setup_listeners(self):
        """设置 EventBus 监听器"""
        event_bus.subscribe("ui.deploy.package_requested", self._on_package_requested)

    def _on_package_requested(self, event: Event):
        """处理打包请求

        Args:
            event: 包含 project_path, output_path 等数据
        """
        project_path = event.data.get("project_path", "")
        output_path = event.data.get("output_path", "")
        project_name = event.data.get("project_name", "project")

        if not project_path or not output_path:
            logger.error("打包请求缺少必要参数")
            event_bus.emit(Event(
                type="feature.deploy.package_failed",
                data={"error": "缺少项目路径或输出路径"},
            ))
            return

        try:
            path = Path(project_path)
            save_path = Path(output_path)

            logger.info(f"开始打包项目: {project_name}")
            event_bus.emit(Event(
                type="feature.deploy.package_progress",
                data={"status": "packaging", "progress": 0, "message": "开始打包..."},
            ))

            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                files = list(path.rglob("*"))
                total = len([f for f in files if f.is_file()])
                processed = 0

                for file in files:
                    if file.is_file() and not file.name.endswith('.pyc'):
                        arcname = file.relative_to(path.parent)
                        zf.write(file, arcname)
                        processed += 1
                        progress = int((processed / total) * 100) if total > 0 else 100

                        # 每 10% 发送一次进度更新
                        if progress % 10 == 0:
                            event_bus.emit(Event(
                                type="feature.deploy.package_progress",
                                data={"status": "packaging", "progress": progress},
                            ))

            logger.info(f"项目打包完成: {save_path}")
            event_bus.emit(Event(
                type="feature.deploy.package_completed",
                data={
                    "status": "completed",
                    "output_path": str(save_path),
                    "project_name": project_name,
                },
            ))

        except Exception as e:
            logger.error(f"打包失败: {e}")
            event_bus.emit(Event(
                type="feature.deploy.package_failed",
                data={"error": str(e)},
            ))


# 全局单例
packaging_service = PackagingService()
