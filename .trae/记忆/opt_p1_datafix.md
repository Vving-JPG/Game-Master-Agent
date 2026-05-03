# P1: 数据 Bug 修复（v5 版本）

> 优先级：🔴 高 | 预估工作量：30 分钟 | 前置条件：无
> **记录时间**: 2026-05-03

---

## 修复内容概览

本次修复解决了两个数据相关的 Bug：
1. **knowledge_editor.py** 导入/导出遗漏 items 和 quests
2. **server.py** CORS 配置缺少 X-Auth-Token

---

## Step 1.1: 修复 knowledge_editor.py 导入/导出遗漏

### 问题描述
- **Bug ID**: BUG-019
- **文件**: `2workbench/presentation/ops/knowledge/knowledge_editor.py` L734-768
- **问题**: `_import_data()` 和 `_export_data()` 只处理 npcs 和 locations，遗漏了 items 和 quests

### 修复方案

#### _import_data() 修改
```python
def _import_data(self) -> None:
    """导入 JSON 数据"""
    path, _ = QFileDialog.getOpenFileName(
        self, "导入知识库", "", "JSON (*.json)"
    )
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "npcs" in data:
            self._npc_editor.load_data(data["npcs"])
        if "locations" in data:
            self._loc_editor.load_data(data["locations"])
        if "items" in data:                          # 新增
            self._item_editor.load_data(data["items"])
        if "quests" in data:                         # 新增
            self._quest_editor.load_data(data["quests"])
        logger.info(f"知识库导入成功: {path}")
        QMessageBox.information(self, "导入成功", f"知识库已从 {path} 导入")
    except Exception as e:
        logger.error(f"导入失败: {e}")
        QMessageBox.critical(self, "导入失败", str(e))
```

#### _export_data() 修改
```python
def _export_data(self) -> None:
    """导出 JSON 数据"""
    path, _ = QFileDialog.getSaveFileName(
        self, "导出知识库", "knowledge.json", "JSON (*.json)"
    )
    if not path:
        return
    try:
        data = {
            "npcs": self._npc_editor.get_data(),
            "locations": self._loc_editor.get_data(),
            "items": self._item_editor.get_data(),      # 新增
            "quests": self._quest_editor.get_data(),    # 新增
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"知识库导出成功: {path}")
        QMessageBox.information(self, "导出成功", f"知识库已导出到 {path}")
    except Exception as e:
        logger.error(f"导出失败: {e}")
        QMessageBox.critical(self, "导出失败", str(e))
```

### 关键代码位置
- [knowledge_editor.py L748-761](file:///d:/Game-Master-Agent/2workbench/presentation/ops/knowledge/knowledge_editor.py#L748-L761)

---

## Step 1.2: 修复 server.py CORS 缺少 X-Auth-Token

### 问题描述
- **Bug ID**: BUG-020
- **文件**: `2workbench/presentation/server.py` L111
- **问题**: CORS `Access-Control-Allow-Headers` 缺少 `X-Auth-Token`，导致浏览器跨域请求无法携带认证头

### 修复方案

```python
def do_OPTIONS(self):
    self.send_response(200)
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Token")  # 添加 X-Auth-Token
    self.end_headers()
```

### 关键代码位置
- [server.py L111](file:///d:/Game-Master-Agent/2workbench/presentation/server.py#L111)

---

## 验收标准

- [x] 导出 JSON 包含 npcs、locations、items、quests 四个字段
- [x] 导入 JSON 能正确加载 items 和 quests 数据
- [x] 导出后重新导入，数据不丢失
- [x] 浏览器跨域请求能正确携带 X-Auth-Token 头
- [x] 预检请求返回正确的 CORS 头

---

## 相关文件

| 文件路径 | 修改类型 | 说明 |
|---------|---------|------|
| `presentation/ops/knowledge/knowledge_editor.py` | 修改 | 导入/导出功能完善 |
| `presentation/server.py` | 修改 | CORS 配置修复 |

---

*最后更新: 2026-05-03*
