"""agent-pack 导入/导出测试"""
import pytest
import zipfile
import json
import io
from pathlib import Path


@pytest.fixture
def client(tmp_path):
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    from src.api.routes.pack import router

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestPackExport:
    def test_export_returns_zip(self, client):
        res = client.get("/api/pack/export")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/zip"

        # 验证是有效 zip
        buf = io.BytesIO(res.content)
        with zipfile.ZipFile(buf, 'r') as zf:
            names = zf.namelist()
            assert "metadata.json" in names

    def test_export_contains_metadata(self, client):
        res = client.get("/api/pack/export")
        buf = io.BytesIO(res.content)
        with zipfile.ZipFile(buf, 'r') as zf:
            metadata = json.loads(zf.read("metadata.json"))
            assert "name" in metadata
            assert "version" in metadata
            assert "exported_at" in metadata


class TestPackImport:
    def test_import_valid_pack(self, client, tmp_path):
        # 创建测试 zip
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr("metadata.json", json.dumps({
                "name": "test", "version": "1.0.0"
            }))
            zf.writestr("system_prompt.md", "# Test Prompt")
        buf.seek(0)

        res = client.post(
            "/api/pack/import",
            files={"file": ("test.zip", buf, "application/zip")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "imported"
        assert len(data["files"]) > 0

    def test_import_invalid_zip(self, client):
        res = client.post(
            "/api/pack/import",
            files={"file": ("bad.txt", b"not a zip", "text/plain")},
        )
        assert res.status_code == 400

    def test_import_missing_metadata(self, client):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr("readme.txt", "no metadata")
        buf.seek(0)

        res = client.post(
            "/api/pack/import",
            files={"file": ("no_meta.zip", buf, "application/zip")},
        )
        assert res.status_code == 400

    def test_import_non_zip_extension(self, client):
        res = client.post(
            "/api/pack/import",
            files={"file": ("test.txt", b"some content", "text/plain")},
        )
        assert res.status_code == 400

    def test_export_import_roundtrip(self, client):
        # 先导出
        export_res = client.get("/api/pack/export")
        assert export_res.status_code == 200

        # 再导入同一个包
        buf = io.BytesIO(export_res.content)
        import_res = client.post(
            "/api/pack/import",
            files={"file": ("roundtrip.zip", buf, "application/zip")},
        )
        assert import_res.status_code == 200
        data = import_res.json()
        assert data["status"] == "imported"
        assert "metadata" in data
