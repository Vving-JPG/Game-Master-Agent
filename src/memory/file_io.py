"""
记忆文件原子读写模块。
所有 .md 文件的写入操作都必须通过此模块。
"""
import os
import tempfile
from pathlib import Path
from datetime import datetime

import frontmatter


def atomic_write(filepath: str, content: str, encoding: str = "utf-8") -> None:
    """
    原子写入文件。在目标文件同目录创建临时文件，完成后原子替换。
    """
    path = Path(filepath)
    dirpath = path.parent
    dirpath.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(dirpath),
        prefix=f".{path.stem}.tmp_",
        suffix=path.suffix
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def update_memory_file(
    filepath: str,
    frontmatter_updates: dict = None,
    append_content: str = None
) -> None:
    """
    更新记忆文件的统一接口。
    自动递增 version，更新 last_modified。
    """
    path = Path(filepath)

    if path.exists():
        post = frontmatter.load(str(path))
    else:
        post = frontmatter.Post(content="")

    if frontmatter_updates:
        for key, value in frontmatter_updates.items():
            post[key] = value

    if append_content:
        post.content += append_content

    post["version"] = post.get("version", 0) + 1
    post["last_modified"] = datetime.now().isoformat()

    atomic_write(str(path), frontmatter.dumps(post))
