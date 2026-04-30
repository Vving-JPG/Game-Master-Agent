"""
agent-pack 导入/导出 API
"""
from __future__ import annotations

import io
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/pack", tags=["pack"])

# 项目根目录
PROJECT_ROOT = Path(".")


@router.get("/export")
async def export_pack():
    """
    导出 agent-pack.zip
    包含: system_prompt + skills + memory + config + workflow
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. metadata.json
        metadata = {
            "name": "GameMaster Agent",
            "version": "2.0.0",
            "description": "RPG Game Master Agent 配置包",
            "exported_at": datetime.now().isoformat(),
        }
        zf.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))

        # 2. system_prompt.md
        sp_path = PROJECT_ROOT / "prompts" / "system_prompt.md"
        if sp_path.exists():
            zf.write(str(sp_path), "system_prompt.md")

        # 3. skills/
        skills_dir = PROJECT_ROOT / "skills"
        if skills_dir.exists():
            for f in skills_dir.rglob("*.md"):
                arcname = f"skills/" + str(f.relative_to(skills_dir))
                zf.write(str(f), arcname)

        # 4. memory/ (workspace/)
        workspace_dir = PROJECT_ROOT / "workspace"
        if workspace_dir.exists():
            for f in workspace_dir.rglob("*.md"):
                arcname = "memory/" + str(f.relative_to(workspace_dir))
                zf.write(str(f), arcname)

        # 5. workflow/
        workflow_dir = PROJECT_ROOT / "workflow"
        if workflow_dir.exists():
            for f in workflow_dir.rglob("*.yaml"):
                arcname = "workflow/" + str(f.relative_to(workflow_dir))
                zf.write(str(f), arcname)

        # 6. config/.env.template
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            # 移除敏感值
            lines = []
            for line in content.split('\n'):
                if 'API_KEY' in line or 'SECRET' in line or 'PASSWORD' in line:
                    key = line.split('=')[0] if '=' in line else line
                    lines.append(f"{key}=YOUR_VALUE_HERE")
                else:
                    lines.append(line)
            zf.writestr("config/.env.template", '\n'.join(lines))

    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=agent-pack.zip"},
    )


@router.post("/import")
async def import_pack(file: UploadFile):
    """
    导入 agent-pack.zip
    校验完整性 → 预览差异 → 合并
    """
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    content = await file.read()
    buf = io.BytesIO(content)

    try:
        with zipfile.ZipFile(buf, 'r') as zf:
            # 校验 metadata.json
            if "metadata.json" not in zf.namelist():
                raise HTTPException(status_code=400, detail="Invalid pack: missing metadata.json")

            metadata = json.loads(zf.read("metadata.json"))

            # 预览差异
            preview = []
            for name in zf.namelist():
                if name == "metadata.json":
                    continue

                # 映射到项目路径
                if name.startswith("system_prompt.md"):
                    target = PROJECT_ROOT / "prompts" / "system_prompt.md"
                elif name.startswith("skills/"):
                    target = PROJECT_ROOT / "skills" / name[len("skills/"):]
                elif name.startswith("memory/"):
                    target = PROJECT_ROOT / "workspace" / name[len("memory/"):]
                elif name.startswith("workflow/"):
                    target = PROJECT_ROOT / "workflow" / name[len("workflow/"):]
                elif name.startswith("config/"):
                    target = PROJECT_ROOT / name[len("config/"):]
                else:
                    continue

                exists = target.exists()
                action = "update" if exists else "create"
                preview.append({
                    "file": name,
                    "target": str(target),
                    "action": action,
                    "exists": exists,
                })

            # 执行合并（自动备份）
            backup_dir = PROJECT_ROOT / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
            for item in preview:
                target = Path(item["target"])
                if item["exists"]:
                    # 备份
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(target), str(backup_dir / target.name))

                # 提取文件
                target.parent.mkdir(parents=True, exist_ok=True)
                data = zf.read(item["file"])
                target.write_bytes(data)

            return {
                "status": "imported",
                "metadata": metadata,
                "files": preview,
                "backup": str(backup_dir) if backup_dir.exists() else None,
            }

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
