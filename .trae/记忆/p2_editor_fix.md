# P2 修复: 编辑器体验修复

> 修复时间: 2026-05-03
> 关联文件: 优化步骤P2-编辑器体验修复.md

---

## 2.1 Prompt 编辑器持久化到文件

**文件**: `2workbench/presentation/editor/prompt_editor.py`

**问题**: `_save_prompt` 只将内容保存到内存 `self._prompts` 字典，不写入文件。关闭项目后修改丢失。

**修复**: 保存到内存 + 持久化到文件

```python
def _save_prompt(self) -> None:
    """保存当前 Prompt 到内存 + 持久化到文件"""
    if not self._current_prompt:
        return
    content = self._editor.toPlainText()
    
    # 1. 保存到内存
    self._prompts[self._current_prompt] = content
    
    # 2. 保存版本
    if self._current_prompt not in self._versions:
        self._versions[self._current_prompt] = []
    self._versions[self._current_prompt].append(
        PromptVersion(content=content, note="手动保存")
    )

    # === 3. 持久化到文件 ===
    try:
        from presentation.project.manager import project_manager
        project_manager.save_prompt(self._current_prompt, content)
        logger.info(f"Prompt 已持久化: {self._current_prompt} ({len(content)} 字符)")
    except Exception as e:
        logger.error(f"Prompt 持久化失败: {e}")

    self.prompt_changed.emit(self._current_prompt, content)
```

**ProjectManager 支持**:
```python
# manager.py 中已有实现
def save_prompt(self, name: str, content: str) -> None:
    """保存 Prompt 模板"""
    if not self._project_path:
        raise RuntimeError("没有打开的项目")
    prompt_path = self._project_path / "prompts" / f"{name}.md"
    prompt_path.write_text(content, encoding="utf-8")
```

---

## 2.2 图编辑器节点删除 Bug 修复

**文件**: `2workbench/presentation/editor/graph_editor.py`

**问题**: `GraphNodeItem._delete` 只调用 `scene.removeItem(self)` 但未调用 `scene.remove_node`，导致关联边未正确移除，图形残留。

**修复**: `_delete` 调用 `remove_node`

```python
class GraphNodeItem(QGraphicsGraphicsObject):
    def _delete(self) -> None:
        """删除此节点"""
        scene = self.scene()
        if scene and hasattr(scene, 'remove_node'):
            scene.remove_node(self.node_id)  # 使用 scene 的方法正确删除
```

**GraphScene.remove_node 实现**:
```python
class GraphScene(QGraphicsScene):
    def remove_node(self, node_id: str) -> bool:
        """删除节点及其所有关联边"""
        if node_id not in self._nodes:
            return False

        node = self._nodes.pop(node_id)

        # 删除所有关联的边（从场景中移除 QGraphicsItem）
        edges_to_remove = [e for e in self._edges
                           if e.source.node_id == node_id or e.target.node_id == node_id]
        for edge in edges_to_remove:
            self._edges.remove(edge)
            self.removeItem(edge)  # 关键：从场景中移除
            logger.debug(f"删除边: {edge.source.node_id} -> {edge.target.node_id}")

        # 删除节点
        self.removeItem(node)  # 关键：从场景中移除
        logger.debug(f"删除节点: {node_id}")
        return True
```

---

## 2.3 图编辑器拖拽连线交互

**文件**: `2workbench/presentation/editor/graph_editor.py`

**问题**: 只能通过右键菜单"连接到..."来连线，缺少可视化拖拽连线交互。

**修复**: 在 `GraphEditorView` 中添加拖拽连线

```python
class GraphEditorView(QGraphicsView):
    """图编辑器视图 — 支持缩放和平移、拖拽连线"""

    def __init__(self, scene: GraphScene, parent=None):
        super().__init__(scene, parent)
        # ... 现有初始化 ...
        
        # 拖拽连线状态
        self._dragging_edge = False
        self._drag_source_port = None  # (node_id, "output"|"input")
        self._temp_line = None

    def mousePressEvent(self, event):
        """检测是否点击了连接点"""
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, QGraphicsRectItem) and item.parentItem():
                node = item.parentItem()
                if isinstance(node, GraphNodeItem):
                    # 判断是输入还是输出端口
                    port_pos = item.pos()
                    node_center = node.boundingRect().center()
                    if port_pos.x() > node_center.x():
                        self._drag_source_port = (node.node_id, "output")
                    else:
                        self._drag_source_port = (node.node_id, "input")
                    self._dragging_edge = True
                    self.setDragMode(QGraphicsView.DragMode.NoDrag)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """拖拽时绘制临时连线"""
        if self._dragging_edge and self._drag_source_port:
            scene_pos = self.mapToScene(event.pos())

            if self._temp_line is None:
                self._temp_line = QGraphicsPathItem()
                self._temp_line.setPen(QPen(QColor("#4A90D9"), 2, Qt.PenStyle.DashLine))
                self.scene().addItem(self._temp_line)

            # 获取源端口位置
            source_node = self.scene()._nodes.get(self._drag_source_port[0])
            if source_node:
                if self._drag_source_port[1] == "output":
                    start = source_node.get_output_pos()
                else:
                    start = source_node.get_input_pos()

                # 创建曲线路径
                path = QPainterPath()
                path.moveTo(start)
                ctrl_offset = abs(scene_pos.x() - start.x()) * 0.5
                path.cubicTo(
                    start + QPointF(ctrl_offset, 0),
                    scene_pos - QPointF(ctrl_offset, 0),
                    scene_pos,
                )
                self._temp_line.setPath(path)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """释放时连接到目标节点"""
        if self._dragging_edge and self._drag_source_port:
            # 清除临时线
            if self._temp_line:
                self.scene().removeItem(self._temp_line)
                self._temp_line = None

            # 检测目标节点
            target_item = self.itemAt(event.pos())
            if isinstance(target_item, QGraphicsRectItem) and target_item.parentItem():
                target_node = target_item.parentItem()
                if isinstance(target_node, GraphNodeItem):
                    source_id = self._drag_source_port[0]
                    target_id = target_node.node_id
                    if source_id != target_id:
                        # 根据拖拽方向确定连接方向
                        if self._drag_source_port[1] == "output":
                            self.scene().add_edge(source_id, target_id)
                        else:
                            self.scene().add_edge(target_id, source_id)
                        logger.debug(f"拖拽连线: {source_id} -> {target_id}")

            self._dragging_edge = False
            self._drag_source_port = None
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            return
        super().mouseReleaseEvent(event)
```

---

## 2.4 节点 ID 自动生成

**文件**: `2workbench/presentation/editor/graph_editor.py`

**问题**: `_add_node_dialog` 中节点 ID 固定为 `"new_node"`，多次添加会冲突。

**修复**: 使用类变量自动生成唯一 ID

```python
class GraphEditorWidget(QWidget):
    """图编辑器组件 — 场景 + 视图 + 工具栏"""

    _node_counter = 0  # 类变量，用于自动生成节点 ID

    def _add_node_dialog(self) -> None:
        """添加节点对话框"""
        # 自动生成唯一 ID
        GraphEditorWidget._node_counter += 1
        node_id = f"node_{GraphEditorWidget._node_counter}"

        # 检查 ID 是否已存在
        while node_id in self._scene._nodes:
            GraphEditorWidget._node_counter += 1
            node_id = f"node_{GraphEditorWidget._node_counter}"

        dialog = NodePropertyDialog(node_id, "custom", "新节点")
        if dialog.exec():
            data = dialog.get_data()
            # 如果用户修改了 ID，检查是否冲突
            final_id = data["id"]
            if final_id != node_id and final_id in self._scene._nodes:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "ID 冲突", f"节点 ID '{final_id}' 已存在，使用自动生成的 ID")
                final_id = node_id

            self._scene.add_node(
                node_id=final_id,
                node_type=data["type"],
                label=data["label"],
                position={"x": 200 + GraphEditorWidget._node_counter * 30,
                          "y": 200 + GraphEditorWidget._node_counter * 20},
            )
            logger.info(f"添加节点: {final_id} ({data['type']})")
```

---

## 2.5 清理调试 print 语句

**检查**: `main_window.py` 中的 print 语句

**结果**: 未发现需要清理的 print 语句，代码已使用 logger 记录日志。

---

## 验证清单

- [x] 编辑 Prompt → 保存 → 关闭项目 → 重新打开 → Prompt 仍然存在
- [x] 删除图节点 → 关联边自动消失（无图形残留）
- [x] 从节点输出端口拖拽到另一节点输入端口 → 自动创建连线
- [x] 连续添加多个节点 → 每个节点有唯一 ID
- [x] `grep -rn "print(" main_window.py` → 零结果

---

## 关联记忆

- `p1_agent_fix.md` - P1 打通 Agent 运行流程
- `p3_tool_feature_fix.md` - P3 工具与 Feature 打通