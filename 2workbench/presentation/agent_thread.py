"""Agent 运行线程 — Presentation 层

负责在后台线程中运行 Agent，通过信号与主线程通信。
不包含业务逻辑，只负责事件循环管理和线程调度。
"""
from __future__ import annotations

import asyncio
from typing import Callable

from PyQt6.QtCore import QThread, pyqtSignal

from foundation.logger import get_logger

logger = get_logger(__name__)


class AgentThread(QThread):
    """Agent 运行线程

    在独立线程中运行 Agent 的异步方法，避免阻塞 UI。
    通过信号将结果返回给主线程。

    Signals:
        finished: 运行完成，传递结果字典
        error: 运行出错，传递错误信息
        stopped: 运行被停止
        stream_chunk: 流式输出片段
    """

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    stopped = pyqtSignal()
    stream_chunk = pyqtSignal(str)

    def __init__(self, agent, user_input: str):
        """初始化

        Args:
            agent: GMAgent 实例
            user_input: 用户输入文本
        """
        super().__init__()
        self.agent = agent
        self.user_input = user_input
        self._should_stop = False

    def stop(self):
        """请求停止线程（协作式取消）"""
        self._should_stop = True
        self.requestInterruption()
        logger.debug("AgentThread 收到停止请求")

    def run(self):
        """线程主函数"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 创建任务
            task = loop.create_task(self.agent.run(self.user_input))

            # 定期检查是否请求停止
            while not task.done() and not self._should_stop:
                loop.run_until_complete(asyncio.sleep(0.1))

            if self._should_stop:
                # 取消任务
                task.cancel()
                try:
                    loop.run_until_complete(task)
                except asyncio.CancelledError:
                    pass
                self.stopped.emit()
                logger.info("AgentThread 已停止")
            else:
                # 获取结果
                result = task.result()
                self.finished.emit(result)
                logger.info("AgentThread 运行完成")

            loop.close()

        except Exception as e:
            if not self._should_stop:
                logger.error(f"AgentThread 运行错误: {e}")
                self.error.emit(str(e))
