"""LangGraph 可视化图编辑器

功能:
1. 节点拖拽布局
2. 节点间连线
3. 节点属性编辑
4. 运行时状态可视化（高亮当前执行节点）
5. 缩放和平移

使用 QGraphicsScene/QGraphicsView 实现。

从 _legacy/widgets/workflow_editor.py 重构。
"""
from __future__ import annotations

import json
from typing import Any

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsItem,
    QGraphicsPathItem, QGraphicsTextItem, QGraphicsRectItem,
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDialog, QLineEdit, QTextEdit, QComboBox, QDialogButtonBox,
    QMenu,
)
from PyQt6.QtCore import (
    Qt, QPointF, QRectF, QLineF, pyqtSignal,
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontDatabase,
    QPainterPath, QPolygonF, QWheelEvent,
)

from foundation.logger import get_logger
from foundation.event_bus import event_bus, Event
from presentation.theme.manager import theme_manager

logger = get_logger(__name__)


# 节点类型 → 颜色映射
NODE_COLORS = {
    "input": ("#4ec9b0", "输入"),       # 青色
    "output": ("#4ec9b0", "输出"),      # 青色
    "llm": ("#569cd6", "LLM"),         # 蓝色
    "prompt": ("#dcdcaa", "Prompt"),    # 黄色
    "parser": ("#ce9178", "解析器"),    # 橙色
    "executor": ("#c586c0", "执行器"),  # 紫色
    "memory": ("#6a9955", "记忆"),      # 绿色
    "event": ("#d4d4d4", "事件"),       # 灰色
    "condition": ("#f44747", "条件"),    # 红色
    "custom": ("#9cdcfe", "自定义"),    # 浅蓝
}


class GraphNodeItem(QGraphicsRectItem):
    """图节点 — 可拖拽的矩形节点"""

    def __init__(
        self,
        node_id: str,
        node_type: str = "custom",
        label: str = "",
        position: dict | None = None,
    ):
        width = 160
        height = 60
        super().__init__(0, 0, width, height)

        self.node_id = node_id
        self.node_type = node_type
        self.label = label or node_id

        # 位置
        x = position.get("x", 0) if position else 0
        y = position.get("y", 0) if position else 0
        self.setPos(x, y)

        # 样式 - 从主题获取颜色
        p = theme_manager.PALETTES.get(theme_manager.current_theme, {})
        color_hex, type_label = NODE_COLORS.get(node_type, ("#9cdcfe", "自定义"))
        self._color = QColor(color_hex)

        self.setBrush(QBrush(self._color))
        border_color = p.get("border", "#3e3e42")
        self.setPen(QPen(QColor(border_color), 2))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(1)

        # 标签文本
        self._label_item = QGraphicsTextItem(self.label, self)
        text_bright = p.get("text_bright", "#ffffff")
        self._label_item.setDefaultTextColor(QColor(text_bright))
        font_family = p.get("font_family", "Microsoft YaHei")
        font = QFont(font_family.split(",")[0].strip('"'), 10, QFont.Weight.Bold)
        self._label_item.setFont(font)
        # 居中
        text_rect = self._label_item.boundingRect()
        self._label_item.setPos(
            (width - text_rect.width()) / 2,
            (height - text_rect.height()) / 2 - 6,
        )

        # 类型标签
        self._type_item = QGraphicsTextItem(type_label, self)
        text_primary = p.get("text_primary", "#cccccc")
        self._type_item.setDefaultTextColor(QColor(text_primary))
        type_font = QFont(font_family.split(",")[0].strip('"'), 8)
        self._type_item.setFont(type_font)
        type_rect = self._type_item.boundingRect()
        self._type_item.setPos(
            (width - type_rect.width()) / 2,
            height - type_rect.height() - 4,
        )

        # 运行状态
        self._is_running = False

        # 连接点（用于连线）
        self._input_port = None
        self._output_port = None
        self._setup_ports()

    def _setup_ports(self) -> None:
        """设置输入/输出连接点"""
        port_size = 10
        # 输入连接点（左侧）
        self._input_port = QGraphicsRectItem(-port_size/2, 25, port_size, port_size, self)
        self._input_port.setBrush(QBrush(QColor("#4ec9b0")))
        self._input_port.setPen(QPen(QColor("#ffffff"), 1))
        self._input_port.setToolTip("输入连接点")
        # 输出连接点（右侧）
        self._output_port = QGraphicsRectItem(160 - port_size/2, 25, port_size, port_size, self)
        self._output_port.setBrush(QBrush(QColor("#ce9178")))
        self._output_port.setPen(QPen(QColor("#ffffff"), 1))
        self._output_port.setToolTip("输出连接点（拖拽连线）")
        self._output_port.setCursor(Qt.CursorShape.CrossCursor)

    def get_input_pos(self) -> QPointF:
        """获取输入连接点位置（场景坐标）"""
        return self.mapToScene(self._input_port.rect().center())

    def get_output_pos(self) -> QPointF:
        """获取输出连接点位置（场景坐标）"""
        return self.mapToScene(self._output_port.rect().center())

    def set_running(self, running: bool) -> None:
        """设置运行状态高亮"""
        self._is_running = running
        if running:
            self.setPen(QPen(QColor("#ffffff"), 3))
        else:
            self.setPen(QPen(QColor("#3e3e42"), 2))
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        """自定义绘制"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._is_running:
            # 运行中: 发光效果
            glow_pen = QPen(QColor("#ffffff"), 4)
            painter.setPen(glow_pen)
            painter.setBrush(QBrush(self._color))
            painter.drawRoundedRect(self.rect(), 8, 8)
        else:
            super().paint(painter, option, widget)

    def itemChange(self, change, value):
        """位置变化时通知"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 通知场景更新连线
            scene = self.scene()
            if scene and hasattr(scene, "update_edges"):
                scene.update_edges()
        return super().itemChange(change, value)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "position": {
                "x": int(self.pos().x()),
                "y": int(self.pos().y()),
            },
        }

    def contextMenuEvent(self, event) -> None:
        """右键菜单"""
        menu = QMenu()
        menu.addAction("编辑属性", self._edit_properties)
        menu.addAction("删除节点", self._delete)
        menu.addSeparator()
        # 添加连线子菜单
        connect_menu = menu.addMenu("连接到...")
        scene = self.scene()
        if scene and hasattr(scene, "_nodes"):
            for node_id, node in scene._nodes.items():
                if node_id != self.node_id:
                    connect_menu.addAction(
                        f"{node.label} ({node_id})",
                        lambda nid=node_id: self._connect_to(nid)
                    )
        menu.exec(event.screenPos())

    def _connect_to(self, target_id: str) -> None:
        """连接到目标节点"""
        scene = self.scene()
        if scene and hasattr(scene, "add_edge"):
            scene.add_edge(self.node_id, target_id)

    def _edit_properties(self) -> None:
        """编辑节点属性"""
        dialog = NodePropertyDialog(self.node_id, self.node_type, self.label)
        if dialog.exec():
            data = dialog.get_data()
            self.node_type = data["type"]
            self.label = data["label"]
            self._label_item.setPlainText(self.label)
            # 更新颜色
            color_hex, _ = NODE_COLORS.get(self.node_type, ("#9cdcfe", "自定义"))
            self._color = QColor(color_hex)
            self.setBrush(QBrush(self._color))

    def _delete(self) -> None:
        """删除节点"""
        scene = self.scene()
        if scene and hasattr(scene, 'remove_node'):
            scene.remove_node(self.node_id)


class GraphEdgeItem(QGraphicsPathItem):
    """图边 — 连接两个节点的曲线"""

    def __init__(self, source: GraphNodeItem, target: GraphNodeItem, condition: str = ""):
        super().__init__()
        self.source = source
        self.target = target
        self.condition = condition  # 新增
        self.setPen(QPen(QColor("#858585"), 2))
        self.setZValue(0)
        self.update_path()
        self._update_style()  # 新增

    def _update_style(self) -> None:
        """根据是否有条件更新样式"""
        if self.condition:
            # 条件边: 红色虚线
            pen = QPen(QColor("#f44747"), 2, Qt.PenStyle.DashLine)
            self.setPen(pen)
        else:
            # 普通边: 灰色实线
            self.setPen(QPen(QColor("#858585"), 2))

    def update_path(self) -> None:
        """更新连线路径"""
        start = self.source.get_output_pos()
        end = self.target.get_input_pos()
        path = QPainterPath()
        path.moveTo(start)
        ctrl_offset = abs(end.x() - start.x()) * 0.5
        path.cubicTo(
            start + QPointF(ctrl_offset, 0),
            end - QPointF(ctrl_offset, 0),
            end,
        )
        self.setPath(path)

        # 如果是条件边，在中间绘制条件标签
        if self.condition:
            # 清除旧标签
            for child in self.childItems():
                if isinstance(child, QGraphicsTextItem):
                    self.scene().removeItem(child) if self.scene() else None
            mid = path.pointAtPercent(0.5)
            label = QGraphicsTextItem(self.condition, self)
            label.setDefaultTextColor(QColor("#f44747"))
            label.setFont(QFont("Microsoft YaHei", 8) if "Microsoft YaHei" in QFontDatabase.families() else QFont("Segoe UI", 8))
            label.setPos(mid.x() - 30, mid.y() - 15)

    def to_dict(self) -> dict:
        """序列化为字典"""
        result = {
            "from": self.source.node_id,
            "to": self.target.node_id,
        }
        if self.condition:
            result["condition"] = self.condition
        return result


class GraphScene(QGraphicsScene):
    """图场景 — 管理节点和边"""

    node_selected = pyqtSignal(str)  # 节点 ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes: dict[str, GraphNodeItem] = {}
        self._edges: list[GraphEdgeItem] = []
        # 从主题管理器获取背景色
        bg_color = theme_manager.PALETTES.get(theme_manager.current_theme, {}).get("bg_primary", "#1e1e1e")
        self.setBackgroundBrush(QBrush(QColor(bg_color)))

    def add_node(self, node_id: str, node_type: str, label: str, position: dict | None = None) -> GraphNodeItem:
        """添加节点"""
        node = GraphNodeItem(node_id, node_type, label, position)
        self.addItem(node)
        self._nodes[node_id] = node
        return node

    def add_edge(self, source_id: str, target_id: str, condition: str = "") -> GraphEdgeItem | None:
        """添加边"""
        source = self._nodes.get(source_id)
        target = self._nodes.get(target_id)
        if not source or not target:
            return None
        edge = GraphEdgeItem(source, target, condition=condition)
        self.addItem(edge)
        self._edges.append(edge)
        return edge

    def remove_node(self, node_id: str) -> None:
        """删除节点及其连线"""
        node = self._nodes.pop(node_id, None)
        if node:
            # 一次性收集要删除的边
            edges_to_remove = [
                e for e in self._edges
                if e.source.node_id == node_id or e.target.node_id == node_id
            ]
            # 从场景中移除关联的边
            for edge in edges_to_remove:
                self.removeItem(edge)
            # 更新边列表
            self._edges = [e for e in self._edges if e not in edges_to_remove]
            # 移除节点
            self.removeItem(node)

    def set_running_node(self, node_id: str | None) -> None:
        """高亮运行中的节点"""
        for nid, node in self._nodes.items():
            node.set_running(nid == node_id)

    def update_edges(self) -> None:
        """更新所有连线位置"""
        for edge in self._edges:
            edge.update_path()

    def load_graph(self, graph_data: dict) -> None:
        """从字典加载图"""
        self.clear()
        self._nodes.clear()
        self._edges.clear()

        # 添加节点
        for node_data in graph_data.get("nodes", []):
            self.add_node(
                node_id=node_data["id"],
                node_type=node_data.get("type", "custom"),
                label=node_data.get("label", node_data["id"]),
                position=node_data.get("position"),
            )

        # 添加边（包含 condition）
        for edge_data in graph_data.get("edges", []):
            self.add_edge(
                edge_data["from"],
                edge_data["to"],
                condition=edge_data.get("condition", ""),
            )

    def to_dict(self) -> dict:
        """导出为字典"""
        return {
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "edges": [edge.to_dict() for edge in self._edges],
        }

    def clear(self) -> None:
        """清空场景"""
        self._nodes.clear()
        self._edges.clear()
        super().clear()


class GraphEditorView(QGraphicsView):
    """图编辑器视图 — 支持缩放和平移、拖拽连线"""

    def __init__(self, scene: GraphScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self._zoom = 1.0

        # 拖拽连线状态
        self._dragging_edge = False
        self._drag_source_port = None  # (node_id, "output"|"input")
        self._temp_line = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        """鼠标滚轮缩放"""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom *= factor
        self._zoom = max(0.3, min(3.0, self._zoom))
        self.setTransform(self.transform().scale(factor, factor))

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

    def fit_to_view(self) -> None:
        """适应视图"""
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # 从当前 transform 获取实际缩放值
        self._zoom = self.transform().m11()  # m11() 返回水平缩放因子


class NodePropertyDialog(QDialog):
    """节点属性编辑对话框"""

    def __init__(self, node_id: str, node_type: str, label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"节点属性 — {node_id}")
        self.setMinimumWidth(350)
        self._setup_ui(node_id, node_type, label)

    def _setup_ui(self, node_id: str, node_type: str, label: str) -> None:
        layout = QFormLayout(self)

        self._id_edit = QLineEdit(node_id)
        self._id_edit.setEnabled(False)
        layout.addRow("节点 ID:", self._id_edit)

        self._type_combo = QComboBox()
        for type_key, (color, type_label) in NODE_COLORS.items():
            self._type_combo.addItem(f"{type_label} ({type_key})", type_key)
        # 选中当前类型
        idx = self._type_combo.findData(node_type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        layout.addRow("节点类型:", self._type_combo)

        self._label_edit = QLineEdit(label)
        layout.addRow("标签:", self._label_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "id": self._id_edit.text(),
            "type": self._type_combo.currentData() or "custom",
            "label": self._label_edit.text(),
        }


class GraphEditorWidget(QWidget):
    """图编辑器组件 — 场景 + 视图 + 工具栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._node_counter = 0  # 实例变量，用于自动生成节点 ID
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        from presentation.widgets.styled_button import StyledButton

        self._btn_fit = StyledButton("适应视图", style_type="ghost")
        self._btn_fit.clicked.connect(self.fit_to_view)
        toolbar.addWidget(self._btn_fit)

        self._btn_add_node = StyledButton("+ 添加节点", style_type="ghost")
        self._btn_add_node.clicked.connect(self._add_node_dialog)
        toolbar.addWidget(self._btn_add_node)

        self._btn_clear = StyledButton("清空", style_type="ghost")
        self._btn_clear.clicked.connect(self.clear)
        toolbar.addWidget(self._btn_clear)

        toolbar.addStretch()

        # 保存按钮
        self._btn_save = StyledButton("💾 保存", style_type="primary")
        self._btn_save.clicked.connect(self._save_graph)
        toolbar.addWidget(self._btn_save)

        layout.addLayout(toolbar)

        # 场景和视图
        self._scene = GraphScene()
        self._view = GraphEditorView(self._scene)
        layout.addWidget(self._view)

        # 运行时高亮订阅
        from foundation.event_bus import event_bus
        event_bus.subscribe("feature.ai.node.started", self._on_node_started)
        event_bus.subscribe("feature.ai.node.completed", self._on_node_completed)

    def _on_node_started(self, event) -> None:
        """节点开始执行时高亮"""
        node_id = event.get("node_id", "")
        if node_id and node_id in self._scene._nodes:
            self._scene.set_running_node(node_id)

    def _on_node_completed(self, event) -> None:
        """节点执行完成时取消高亮"""
        self._scene.set_running_node(None)

    def load_graph(self, graph_data: dict) -> None:
        """加载图定义"""
        self._scene.load_graph(graph_data)
        # 延迟适应视图
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.fit_to_view)

    def get_graph(self) -> dict:
        """获取当前图定义"""
        return self._scene.to_dict()

    def set_running_node(self, node_id: str | None) -> None:
        """高亮运行中的节点"""
        self._scene.set_running_node(node_id)

    def fit_to_view(self) -> None:
        """适应视图"""
        self._view.fit_to_view()

    def clear(self) -> None:
        """清空图"""
        self._scene.clear()

    def _add_node_dialog(self) -> None:
        """添加节点对话框"""
        # 自动生成唯一 ID
        self._node_counter += 1
        node_id = f"node_{self._node_counter}"

        # 检查 ID 是否已存在
        while node_id in self._scene._nodes:
            self._node_counter += 1
            node_id = f"node_{self._node_counter}"

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
                position={"x": 200 + self._node_counter * 30,
                          "y": 200 + self._node_counter * 20},
            )
            logger.info(f"添加节点: {final_id} ({data['type']})")

    def _save_graph(self) -> None:
        """保存图定义到 graph.json 并触发编译"""
        from presentation.project.manager import project_manager
        from PyQt6.QtWidgets import QMessageBox

        graph_data = self.get_graph()

        # 保存到文件
        try:
            project_manager.save_graph(graph_data)
            logger.info(f"图定义已保存 ({len(graph_data['nodes'])} 节点, {len(graph_data['edges'])} 边)")
        except RuntimeError as e:
            logger.error(f"保存失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存图时出错: {e}")
            return

        # 触发编译（通过 EventBus 请求，不直接调用 Feature 层）
        try:
            event_bus.emit(Event(type="ui.graph.save_requested", data={
                "graph_data": graph_data,
                "node_count": len(graph_data["nodes"]),
                "edge_count": len(graph_data["edges"]),
            }))
            logger.info("图保存请求已发出，等待编译完成通知")
            QMessageBox.information(self, "保存成功", f"图已保存 ({len(graph_data['nodes'])} 节点)，编译请求已发送")
        except Exception as e:
            logger.error(f"图编译请求失败: {e}")
            QMessageBox.warning(self, "编译警告", f"图已保存但编译请求失败: {e}")
