# workbench/widgets/workflow_editor.py
"""流程图编辑器 — QGraphicsScene 节点编排"""
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QGraphicsTextItem, QGraphicsRectItem,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QFileDialog, QGraphicsEllipseItem, QGraphicsPolygonItem,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QPolygonF,
)
import yaml
from pathlib import Path


# 节点类型定义
NODE_TYPES = {
    "start": {"label": "开始", "color": "#4caf50", "shape": "ellipse"},
    "end": {"label": "结束", "color": "#f44336", "shape": "ellipse"},
    "event": {"label": "接收事件", "color": "#2196f3", "shape": "rect"},
    "prompt": {"label": "构建 Prompt", "color": "#ff9800", "shape": "rect"},
    "llm": {"label": "LLM 推理", "color": "#9c27b0", "shape": "rect"},
    "command": {"label": "解析命令", "color": "#00bcd4", "shape": "rect"},
    "memory": {"label": "更新记忆", "color": "#8bc34a", "shape": "rect"},
    "condition": {"label": "条件判断", "color": "#ff5722", "shape": "diamond"},
    "parallel": {"label": "并行执行", "color": "#607d8b", "shape": "rect"},
    "loop": {"label": "循环", "color": "#795548", "shape": "rect"},
}


class WorkflowNode(QGraphicsItem):
    """工作流节点基类"""

    def __init__(self, node_type: str, node_id: str, x: float = 0, y: float = 0):
        super().__init__()
        self.node_type = node_type
        self.node_id = node_id
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        config = NODE_TYPES.get(node_type, {"label": node_type, "color": "#666", "shape": "rect"})
        self.color = QColor(config["color"])
        self.label = config["label"]
        self.shape_type = config["shape"]

        # 根据形状设置大小
        if self.shape_type == "diamond":
            self.width = 100
            self.height = 80
        else:
            self.width = 140
            self.height = 60

        # 标签
        self.text_item = QGraphicsTextItem(self.label, self)
        self.text_item.setDefaultTextColor(QColor("#ffffff"))
        font = QFont("Microsoft YaHei", 10)
        font.setBold(True)
        self.text_item.setFont(font)
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos((self.width - text_rect.width()) / 2, (self.height - text_rect.height()) / 2 - 8)

        # ID 标签
        self.id_text = QGraphicsTextItem(node_id, self)
        self.id_text.setDefaultTextColor(QColor("#aaaaaa"))
        self.id_text.setFont(QFont("Consolas", 8))
        id_rect = self.id_text.boundingRect()
        self.id_text.setPos((self.width - id_rect.width()) / 2, (self.height - id_rect.height()) / 2 + 10)

    def boundingRect(self):
        if self.shape_type == "diamond":
            return QRectF(-self.width/2, -self.height/2, self.width, self.height)
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option, widget):
        painter.setPen(QPen(self.color, 2))
        painter.setBrush(QBrush(QColor(self.color.red(), self.color.green(), self.color.blue(), 60)))

        if self.shape_type == "ellipse":
            painter.drawEllipse(self.boundingRect())
        elif self.shape_type == "diamond":
            polygon = QPolygonF([
                QPointF(0, -self.height/2),
                QPointF(self.width/2, 0),
                QPointF(0, self.height/2),
                QPointF(-self.width/2, 0),
            ])
            painter.drawPolygon(polygon)
        else:  # rect
            painter.drawRoundedRect(self.boundingRect(), 8, 8)

        # 选中高亮
        if self.isSelected():
            painter.setPen(QPen(QColor("#ffffff"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self.shape_type == "ellipse":
                painter.drawEllipse(self.boundingRect().adjusted(-2, -2, 2, 2))
            elif self.shape_type == "diamond":
                polygon = QPolygonF([
                    QPointF(0, -self.height/2 - 2),
                    QPointF(self.width/2 + 2, 0),
                    QPointF(0, self.height/2 + 2),
                    QPointF(-self.width/2 - 2, 0),
                ])
                painter.drawPolygon(polygon)
            else:
                painter.drawRoundedRect(self.boundingRect().adjusted(-2, -2, 2, 2), 10, 10)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 通知场景更新连线
            scene = self.scene()
            if scene and hasattr(scene, "update_edges"):
                scene.update_edges()
        return super().itemChange(change, value)

    def get_connection_point(self, is_input: bool) -> QPointF:
        """获取连接点位置"""
        if self.shape_type == "diamond":
            if is_input:
                return self.pos() + QPointF(-self.width/2, 0)
            else:
                return self.pos() + QPointF(self.width/2, 0)
        else:
            if is_input:
                return self.pos() + QPointF(0, self.height/2)
            else:
                return self.pos() + QPointF(self.width, self.height/2)


class WorkflowEdge(QGraphicsPathItem):
    """工作流连线"""

    def __init__(self, source: WorkflowNode, target: WorkflowNode):
        super().__init__()
        self.source = source
        self.target = target
        self.setPen(QPen(QColor("#666666"), 2))
        self.setZValue(-1)
        self.update_path()

    def update_path(self):
        """更新连线路径"""
        start = self.source.get_connection_point(False)
        end = self.target.get_connection_point(True)

        path = QPainterPath()
        path.moveTo(start)

        # 使用贝塞尔曲线
        ctrl_x = (start.x() + end.x()) / 2
        path.cubicTo(ctrl_x, start.y(), ctrl_x, end.y(), end.x(), end.y())
        self.setPath(path)

        # 绘制箭头
        # TODO: 添加箭头标记


class WorkflowScene(QGraphicsScene):
    """工作流场景"""

    def __init__(self):
        super().__init__()
        self.nodes: dict[str, WorkflowNode] = {}
        self.edges: list[WorkflowEdge] = []
        self.setSceneRect(0, 0, 2000, 1500)

    def add_node(self, node_type: str, node_id: str, x: float, y: float) -> WorkflowNode:
        """添加节点"""
        node = WorkflowNode(node_type, node_id, x, y)
        self.addItem(node)
        self.nodes[node_id] = node
        return node

    def add_edge(self, source_id: str, target_id: str):
        """添加连线"""
        if source_id in self.nodes and target_id in self.nodes:
            edge = WorkflowEdge(self.nodes[source_id], self.nodes[target_id])
            self.addItem(edge)
            self.edges.append(edge)

    def update_edges(self):
        """更新所有连线"""
        for edge in self.edges:
            edge.update_path()

    def clear_all(self):
        """清空所有节点和连线"""
        self.clear()
        self.nodes.clear()
        self.edges.clear()

    def load_from_yaml(self, yaml_content: str):
        """从 YAML 加载工作流"""
        self.clear_all()
        try:
            data = yaml.safe_load(yaml_content)
            if not data:
                return
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            for node in nodes:
                self.add_node(
                    node.get("type", "event"),
                    node.get("id", ""),
                    node.get("x", 0),
                    node.get("y", 0),
                )
            for edge in edges:
                self.add_edge(edge.get("from", ""), edge.get("to", ""))
        except Exception as e:
            print(f"加载工作流失败: {e}")

    def to_yaml(self) -> str:
        """导出为 YAML"""
        nodes = []
        for nid, node in self.nodes.items():
            nodes.append({
                "id": nid,
                "type": node.node_type,
                "x": int(node.pos().x()),
                "y": int(node.pos().y()),
            })
        edges = []
        for edge in self.edges:
            edges.append({"from": edge.source.node_id, "to": edge.target.node_id})
        return yaml.dump({"nodes": nodes, "edges": edges}, allow_unicode=True)


class WorkflowEditor(QWidget):
    """流程图编辑器组件"""

    def __init__(self):
        super().__init__()
        self.current_file: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self.node_combo = QComboBox()
        for ntype, config in NODE_TYPES.items():
            self.node_combo.addItem(f"{config['label']} ({ntype})", ntype)
        btn_add = QPushButton("+ 添加节点")
        btn_add.clicked.connect(self._add_node)
        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self._save)
        btn_load = QPushButton("加载")
        btn_load.clicked.connect(self._load_file_dialog)
        toolbar.addWidget(self.node_combo)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_save)
        toolbar.addWidget(btn_load)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 场景 + 视图
        self.scene = WorkflowScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setStyleSheet("background-color: #1a1a2e; border: none;")
        layout.addWidget(self.view)

        # 加载默认工作流
        self._load_default_workflow()

    def _load_default_workflow(self):
        """加载默认的 Agent 主循环工作流"""
        default_yaml = """
nodes:
  - id: receive_event
    type: event
    x: 50
    y: 200
  - id: build_prompt
    type: prompt
    x: 250
    y: 200
  - id: llm_reasoning
    type: llm
    x: 450
    y: 200
  - id: parse_command
    type: command
    x: 650
    y: 150
  - id: stream_output
    type: event
    x: 650
    y: 300
  - id: update_memory
    type: memory
    x: 850
    y: 150
  - id: send_command
    type: event
    x: 850
    y: 300
  - id: end
    type: end
    x: 1050
    y: 200
edges:
  - from: receive_event
    to: build_prompt
  - from: build_prompt
    to: llm_reasoning
  - from: llm_reasoning
    to: parse_command
  - from: llm_reasoning
    to: stream_output
  - from: parse_command
    to: update_memory
  - from: stream_output
    to: send_command
  - from: update_memory
    to: end
  - from: send_command
    to: end
"""
        self.scene.load_from_yaml(default_yaml)

    def _add_node(self):
        """添加新节点"""
        node_type = self.node_combo.currentData()
        node_id = f"node_{len(self.scene.nodes) + 1}"
        # 在视图中心添加节点
        center = self.view.mapToScene(self.view.viewport().rect().center())
        self.scene.add_node(node_type, node_id, center.x() - 70, center.y() - 30)

    def _save(self):
        """保存工作流"""
        if not self.current_file:
            self.current_file = "workflow/main_loop.yaml"
        yaml_content = self.scene.to_yaml()
        Path(self.current_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self.current_file).write_text(yaml_content, encoding="utf-8")
        print(f"工作流已保存到: {self.current_file}")

    def _load_file_dialog(self):
        """文件对话框加载"""
        path, _ = QFileDialog.getOpenFileName(self, "加载工作流", "workflow/", "YAML (*.yaml *.yml)")
        if path:
            self.current_file = path
            content = Path(path).read_text(encoding="utf-8")
            self.scene.load_from_yaml(content)

    def load_from_file(self, path: str):
        """从文件加载"""
        self.current_file = path
        content = Path(path).read_text(encoding="utf-8")
        self.scene.load_from_yaml(content)
