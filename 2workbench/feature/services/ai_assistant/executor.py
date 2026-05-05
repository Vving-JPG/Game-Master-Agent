"""
AI 工具执行引擎
负责执行单个 PlanStep，管理文件快照、Diff 生成和撤销
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from foundation.logger import get_logger
from foundation.event_bus import event_bus, Event
from .tools import tool_registry
from .models import PlanStep, StepStatus

logger = get_logger(__name__)


class StepExecutionError(Exception):
    """步骤执行失败"""
    def __init__(self, step: PlanStep, message: str):
        self.step = step
        self.message = message
        super().__init__(f"步骤 {step.step_id} 执行失败: {message}")


class SnapshotManager:
    """文件快照管理器"""

    def __init__(self):
        # 快照存储：{文件路径: 原始内容}
        self._snapshots: dict[str, str] = {}
        # 快照存储目录
        self._snapshot_dir: Path | None = None

    def create_snapshot(self, file_path: str) -> str | None:
        """
        为指定文件创建快照

        Args:
            file_path: 文件绝对路径

        Returns:
            快照 ID（文件路径本身作为 ID），如果文件不存在返回 None
        """
        path = Path(file_path)
        if not path.exists():
            logger.debug(f"文件不存在，跳过快照: {file_path}")
            return None

        try:
            content = path.read_text(encoding="utf-8")
            self._snapshots[file_path] = content
            logger.debug(f"快照已创建: {file_path} ({len(content)} bytes)")
            return file_path
        except Exception as e:
            logger.warning(f"快照创建失败: {file_path} -> {e}")
            return None

    def restore_snapshot(self, file_path: str) -> bool:
        """
        从快照恢复文件

        Args:
            file_path: 文件绝对路径

        Returns:
            是否恢复成功
        """
        if file_path not in self._snapshots:
            logger.warning(f"没有找到快照: {file_path}")
            return False

        original_content = self._snapshots[file_path]
        path = Path(file_path)

        try:
            if path.exists():
                path.write_text(original_content, encoding="utf-8")
            else:
                # 文件被删除了，恢复内容
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(original_content, encoding="utf-8")

            logger.info(f"快照已恢复: {file_path}")
            return True
        except Exception as e:
            logger.error(f"快照恢复失败: {file_path} -> {e}")
            return False

    def delete_snapshot(self, file_path: str):
        """删除指定快照"""
        self._snapshots.pop(file_path, None)

    def clear_all(self):
        """清除所有快照"""
        self._snapshots.clear()

    def has_snapshot(self, file_path: str) -> bool:
        """检查是否有指定文件的快照"""
        return file_path in self._snapshots

    def get_snapshot(self, file_path: str) -> str | None:
        """获取快照内容"""
        return self._snapshots.get(file_path)


class DiffGenerator:
    """Diff 生成器"""

    @staticmethod
    def generate_unified_diff(old_content: str, new_content: str, file_path: str) -> str:
        """
        生成统一 diff 格式

        Args:
            old_content: 原始文件内容
            new_content: 新文件内容
            file_path: 文件路径（用于 diff header）

        Returns:
            统一 diff 格式的字符串
        """
        if old_content == new_content:
            return ""

        old_lines = old_content.split("\n")
        new_lines = new_content.split("\n")

        diff_lines = [
            f"--- {file_path}",
            f"+++ {file_path}",
        ]

        # 使用 difflib 生成统一 diff 格式
        import difflib
        differ = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )

        diff_text = "\n".join(differ)
        return diff_text

    @staticmethod
    def generate_delete_diff(content: str, file_path: str) -> str:
        """生成文件删除的 diff"""
        lines = content.split("\n")
        diff_lines = [
            f"--- {file_path}",
            f"+++ /dev/null",
        ]
        for line in lines:
            diff_lines.append(f"-{line}")
        return "\n".join(diff_lines)

    @staticmethod
    def generate_create_diff(content: str, file_path: str) -> str:
        """生成文件创建的 diff"""
        lines = content.split("\n")
        diff_lines = [
            f"--- /dev/null",
            f"+++ {file_path}",
        ]
        for line in lines:
            diff_lines.append(f"+{line}")
        return "\n".join(diff_lines)


class ToolExecutor:
    """工具执行引擎"""

    def __init__(self):
        self._registry = tool_registry
        self._snapshot_manager = SnapshotManager()
        self._diff_generator = DiffGenerator()

    async def execute_step(self, step: PlanStep) -> PlanStep:
        """
        执行单个计划步骤

        Args:
            step: 要执行的步骤

        Returns:
            更新后的步骤（包含执行结果和 diff）

        Raises:
            StepExecutionError: 执行失败
        """
        logger.info(f"开始执行步骤 {step.step_id}: {step.description}")

        # 1. 标记为执行中
        step.status = StepStatus.EXECUTING

        # 2. 发送执行开始事件
        event_bus.emit(Event(
            type="ai_assistant.step_started",
            data={"step_id": step.step_id, "tool": step.tool_name},
            source="ToolExecutor",
        ))

        # 3. 创建快照（对于可能修改文件的工具）
        snapshot_id = self._pre_execute_snapshot(step)

        try:
            # 4. 执行工具
            result = await self._registry.execute(
                step.tool_name,
                **step.parameters,
            )

            # 5. 处理结果
            if result.success:
                step.status = StepStatus.COMPLETED
                step.result = {
                    "message": result.message,
                    "data": result.data,
                }

                # 6. 生成 Diff
                if result.file_path and result.diff:
                    step.diff = result.diff
                elif result.file_path:
                    step.diff = self._post_execute_diff(
                        step, result.file_path
                    )

                logger.info(
                    f"步骤 {step.step_id} 执行成功: {result.message}"
                )

                # 发送执行完成事件
                event_bus.emit(Event(
                    type="ai_assistant.step_completed",
                    data={
                        "step_id": step.step_id,
                        "tool": step.tool_name,
                        "message": result.message,
                        "diff": step.diff,
                        "file_path": result.file_path,
                    },
                    source="ToolExecutor",
                ))
            else:
                step.status = StepStatus.FAILED
                step.error = result.message
                logger.warning(
                    f"步骤 {step.step_id} 执行失败: {result.message}"
                )

                # 恢复快照
                if snapshot_id:
                    self._snapshot_manager.restore_snapshot(snapshot_id)

                # 发送执行失败事件
                event_bus.emit(Event(
                    type="ai_assistant.step_failed",
                    data={
                        "step_id": step.step_id,
                        "tool": step.tool_name,
                        "error": result.message,
                    },
                    source="ToolExecutor",
                ))

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            logger.error(f"步骤 {step.step_id} 异常: {e}")

            # 恢复快照
            if snapshot_id:
                self._snapshot_manager.restore_snapshot(snapshot_id)

            event_bus.emit(Event(
                type="ai_assistant.step_failed",
                data={
                    "step_id": step.step_id,
                    "tool": step.tool_name,
                    "error": str(e),
                },
                source="ToolExecutor",
            ))

        return step

    def reject_step(self, step: PlanStep) -> bool:
        """
        用户拒绝步骤的变更，从快照恢复

        Args:
            step: 被拒绝的步骤

        Returns:
            是否成功恢复
        """
        if step.status != StepStatus.COMPLETED:
            logger.warning(f"只能拒绝已完成的步骤，当前状态: {step.status}")
            return False

        # 查找关联的快照
        file_path = step.result.get("file_path", "") if step.result else ""
        if not file_path:
            logger.warning(f"步骤 {step.step_id} 没有关联的文件路径")
            return False

        restored = self._snapshot_manager.restore_snapshot(file_path)
        if restored:
            step.status = StepStatus.REJECTED
            event_bus.emit(Event(
                type="ai_assistant.step_rejected",
                data={"step_id": step.step_id},
                source="ToolExecutor",
            ))
        return restored

    def _pre_execute_snapshot(self, step: PlanStep) -> str | None:
        """
        执行前创建文件快照

        根据工具类型判断是否需要快照：
        - create_* 工具：不需要（文件不存在）
        - edit_* 工具：需要（文件存在，要修改）
        - delete_* 工具：需要（文件存在，要删除）
        - update_* 工具：需要（文件存在，要修改）
        - read_* / list_* / test_* 工具：不需要（只读）
        """
        tool_name = step.tool_name

        # 只读工具，不需要快照
        if tool_name.startswith(("read_", "list_", "test_")):
            return None

        # create 工具，检查文件是否已存在
        if tool_name.startswith("create_"):
            # 从参数中推断文件路径
            file_path = self._infer_file_path(step)
            if file_path and Path(file_path).exists():
                return self._snapshot_manager.create_snapshot(file_path)
            return None

        # edit / delete / update 工具，需要快照
        if tool_name.startswith(("edit_", "delete_", "update_")):
            file_path = self._infer_file_path(step)
            if file_path:
                return self._snapshot_manager.create_snapshot(file_path)

        return None

    def _post_execute_diff(self, step: PlanStep, file_path: str) -> str:
        """执行后生成 Diff"""
        old_content = self._snapshot_manager.get_snapshot(file_path)

        if old_content is None:
            # 没有快照 = 新建文件
            try:
                new_content = Path(file_path).read_text(encoding="utf-8")
                return self._diff_generator.generate_create_diff(
                    new_content, file_path
                )
            except Exception:
                return ""

        try:
            new_content = Path(file_path).read_text(encoding="utf-8")
            return self._diff_generator.generate_unified_diff(
                old_content, new_content, file_path
            )
        except Exception as e:
            logger.warning(f"Diff 生成失败: {e}")
            return ""

    def _infer_file_path(self, step: PlanStep) -> str | None:
        """
        从步骤参数中推断文件路径

        Args:
            step: 计划步骤

        Returns:
            推断出的文件绝对路径，或 None
        """
        from feature.project import project_manager

        if not project_manager.is_open:
            return None

        base_path = project_manager.project_path
        tool_name = step.tool_name
        params = step.parameters

        if tool_name in ("create_prompt", "edit_prompt", "delete_prompt"):
            name = params.get("name", "")
            if name:
                return str(base_path / "prompts" / f"{name}.md")

        elif tool_name in ("create_skill", "edit_skill", "delete_skill"):
            name = params.get("name", "")
            if name:
                return str(base_path / "skills" / name / "SKILL.md")

        elif tool_name == "update_graph":
            return str(base_path / "graph.json")

        elif tool_name == "update_config":
            return str(base_path / "config.json")

        return None

    def clear_snapshots(self):
        """清除所有快照"""
        self._snapshot_manager.clear_all()


# 全局单例
tool_executor = ToolExecutor()
