"""
渐进式记忆加载器。
Layer 1 (Index): ~100 tokens/file
Layer 2 (Activation): ~500-2000 tokens/file
Layer 3 (Execution): ~2000-5000 tokens/file
"""
import re
from pathlib import Path

import frontmatter


class MemoryLoader:
    """渐进式记忆加载器"""

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)

    def load_index(self, file_paths: list[str]) -> str:
        """Layer 1: 只读取 name, type, tags, version"""
        lines = ["## 相关实体索引\n"]
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                lines.append(f"- {fp}: [不存在]")
                continue
            post = frontmatter.load(str(full_path))
            name = post.get("name", fp)
            etype = post.get("type", "unknown")
            tags = post.get("tags", [])
            version = post.get("version", 0)
            tag_str = ", ".join(tags) if tags else ""
            lines.append(f"- [{etype}] {name} (v{version}) {tag_str}")
        return "\n".join(lines)

    def load_activation(self, file_paths: list[str]) -> str:
        """Layer 2: 完整 YAML + 章节标题"""
        blocks = []
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                continue
            post = frontmatter.load(str(full_path))
            fm_lines = [f"### {post.get('name', fp)}"]
            for key, value in post.metadata.items():
                if key in ("version", "last_modified", "modified_by", "created_at"):
                    continue
                fm_lines.append(f"- {key}: {value}")
            headings = re.findall(r'^## .+$', post.content, re.MULTILINE)
            if headings:
                fm_lines.append("- 章节: " + " | ".join(h[3:] for h in headings))
            blocks.append("\n".join(fm_lines))
        return "\n\n".join(blocks)

    def load_execution(self, file_paths: list[str]) -> str:
        """Layer 3: 完整文件内容"""
        blocks = []
        for fp in file_paths:
            full_path = self.workspace / f"{fp}.md"
            if not full_path.exists():
                continue
            post = frontmatter.load(str(full_path))
            blocks.append(f"### {post.get('name', fp)}\n{post.content}")
        return "\n\n".join(blocks)
