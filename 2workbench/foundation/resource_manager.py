"""资源管理器 — 文件系统操作

提供安全的文件读写、目录扫描、资源类型检测等功能。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from foundation.logger import get_logger

logger = get_logger(__name__)


# 文件类型 -> 资源类型映射
FILE_TYPE_MAP = {
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".py": "python",
    ".sql": "sql",
    ".env": "config",
    ".cfg": "config",
    ".ini": "config",
    ".toml": "config",
    ".qss": "stylesheet",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".svg": "image",
}


class ResourceManager:
    """资源管理器

    用法:
        rm = ResourceManager(base_path="./workspace")
        tree = rm.scan_directory()
        content = rm.read_file("npcs/张三.md")
        rm.write_file("npcs/新NPC.md", content)
    """

    def __init__(self, base_path: str | Path = "./data/resources"):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    @property
    def base_path(self) -> Path:
        return self._base_path

    def scan_directory(
        self,
        relative_path: str = "",
        ignore_patterns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """扫描目录，返回文件/文件夹列表

        Args:
            relative_path: 相对于 base_path 的子目录
            ignore_patterns: 忽略的文件模式（如 ["__pycache__", "*.pyc"]）

        Returns:
            [{"name": str, "type": "file/dir", "path": str, "resource_type": str}]
        """
        ignore = set(ignore_patterns or ["__pycache__", "*.pyc", ".git"])
        scan_dir = self._base_path / relative_path

        if not scan_dir.exists():
            return []

        items = []
        for item in sorted(scan_dir.iterdir()):
            # 跳过忽略项
            if any(item.match(p) for p in ignore):
                continue
            if item.name.startswith(".") and item.name != ".env":
                continue

            rel_path = str(item.relative_to(self._base_path))
            resource_type = ""

            if item.is_file():
                resource_type = FILE_TYPE_MAP.get(item.suffix.lower(), "unknown")

            items.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
                "path": rel_path,
                "resource_type": resource_type,
            })

        return items

    def read_file(self, relative_path: str, encoding: str = "utf-8") -> str:
        """读取文件内容"""
        full_path = self._resolve(relative_path)
        return full_path.read_text(encoding=encoding)

    def write_file(
        self,
        relative_path: str,
        content: str,
        encoding: str = "utf-8",
    ) -> str:
        """写入文件（自动创建目录）

        Returns:
            文件的完整路径
        """
        full_path = self._resolve(relative_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding=encoding)
        logger.debug(f"文件写入: {full_path}")
        return str(full_path)

    def delete_file(self, relative_path: str) -> bool:
        """删除文件"""
        full_path = self._resolve(relative_path)
        if full_path.exists():
            full_path.unlink()
            logger.debug(f"文件删除: {full_path}")
            return True
        return False

    def file_exists(self, relative_path: str) -> bool:
        """检查文件是否存在"""
        return self._resolve(relative_path).exists()

    def get_resource_type(self, relative_path: str) -> str:
        """获取资源类型"""
        suffix = Path(relative_path).suffix.lower()
        return FILE_TYPE_MAP.get(suffix, "unknown")

    def _resolve(self, relative_path: str) -> Path:
        """解析路径，防止目录遍历"""
        full = (self._base_path / relative_path).resolve()
        base = self._base_path.resolve()
        if not str(full).startswith(str(base)):
            raise ValueError(f"路径越界: {relative_path}")
        return full
