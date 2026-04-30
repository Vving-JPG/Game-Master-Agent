"""API 客户端"""
import json
import requests
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class SSEThread(QThread):
    """SSE 事件流线程"""
    
    event_received = pyqtSignal(str, dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.running = False
        
    def run(self):
        """运行 SSE 事件流"""
        self.running = True
        try:
            import sseclient
            
            response = requests.get(
                f"{self.base_url}/api/agent/stream",
                stream=True,
                headers={"Accept": "text/event-stream"}
            )
            
            client = sseclient.SSEClient(response)
            
            for event in client.events():
                if not self.running:
                    break
                    
                try:
                    data = json.loads(event.data) if event.data else {}
                    self.event_received.emit(event.event, data)
                except json.JSONDecodeError:
                    self.event_received.emit(event.event, {"raw": event.data})
                    
        except Exception as e:
            if self.running:
                self.error_occurred.emit(str(e))
                
    def stop(self):
        """停止 SSE 流"""
        self.running = False
        self.wait(1000)


class APIClient(QObject):
    """API 客户端"""
    
    event_received = pyqtSignal(str, dict)
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__()
        self.base_url = base_url
        self.sse_thread: Optional[SSEThread] = None
        self.sse_running = False
        
    def check_health(self) -> bool:
        """检查服务器健康状态"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
            
    def start_sse_stream(self):
        """启动 SSE 事件流"""
        if self.sse_running:
            return
            
        self.sse_thread = SSEThread(self.base_url)
        self.sse_thread.event_received.connect(self.event_received.emit)
        self.sse_thread.start()
        self.sse_running = True
        
    def stop_sse_stream(self):
        """停止 SSE 事件流"""
        if self.sse_thread:
            self.sse_thread.stop()
            self.sse_thread = None
        self.sse_running = False
        
    # === Workspace API ===
    
    def get_workspace_tree(self, path: str = "") -> dict:
        """获取 Workspace 文件树"""
        response = requests.get(
            f"{self.base_url}/api/workspace/tree",
            params={"path": path}
        )
        response.raise_for_status()
        return response.json()
        
    def get_file(self, path: str) -> dict:
        """获取文件内容"""
        response = requests.get(
            f"{self.base_url}/api/workspace/file",
            params={"path": path}
        )
        response.raise_for_status()
        return response.json()
        
    def update_file(self, path: str, content: str = None, 
                    frontmatter: dict = None, raw: str = None) -> dict:
        """更新文件"""
        data = {"path": path}
        if raw is not None:
            data["raw"] = raw
        if content is not None:
            data["content"] = content
        if frontmatter is not None:
            data["frontmatter"] = frontmatter
            
        response = requests.put(
            f"{self.base_url}/api/workspace/file",
            json=data
        )
        response.raise_for_status()
        return response.json()
        
    def create_file(self, path: str, content: str = "") -> dict:
        """创建文件"""
        response = requests.post(
            f"{self.base_url}/api/workspace/file",
            json={"path": path, "content": content}
        )
        response.raise_for_status()
        return response.json()
        
    def delete_file(self, path: str) -> dict:
        """删除文件"""
        response = requests.delete(
            f"{self.base_url}/api/workspace/file",
            params={"path": path}
        )
        response.raise_for_status()
        return response.json()
        
    # === Skills API ===
    
    def list_skills(self) -> list:
        """列出所有 Skills"""
        response = requests.get(f"{self.base_url}/api/skills")
        response.raise_for_status()
        return response.json()
        
    def get_skill(self, name: str) -> dict:
        """获取 Skill 内容"""
        response = requests.get(f"{self.base_url}/api/skills/{name}")
        response.raise_for_status()
        return response.json()
        
    def update_skill(self, name: str, content: str) -> dict:
        """更新 Skill"""
        response = requests.put(
            f"{self.base_url}/api/skills/{name}",
            json={"content": content}
        )
        response.raise_for_status()
        return response.json()
        
    def create_skill(self, name: str, content: str) -> dict:
        """创建 Skill"""
        response = requests.post(
            f"{self.base_url}/api/skills",
            json={"name": name, "content": content, "source": "agent_created"}
        )
        response.raise_for_status()
        return response.json()
        
    def delete_skill(self, name: str) -> dict:
        """删除 Skill"""
        response = requests.delete(f"{self.base_url}/api/skills/{name}")
        response.raise_for_status()
        return response.json()
        
    # === Agent API ===
    
    def get_status(self) -> dict:
        """获取 Agent 状态"""
        response = requests.get(f"{self.base_url}/api/agent/status")
        response.raise_for_status()
        return response.json()
        
    def get_context(self) -> dict:
        """获取 Agent 上下文"""
        response = requests.get(f"{self.base_url}/api/agent/context")
        response.raise_for_status()
        return response.json()
        
    def send_event(self, event_type: str, data: dict, 
                   event_id: str = None, timestamp: str = None) -> dict:
        """发送事件"""
        from datetime import datetime
        
        payload = {
            "event_id": event_id or f"gui_{datetime.now().timestamp()}",
            "timestamp": timestamp or datetime.now().isoformat(),
            "type": event_type,
            "data": data,
            "context_hints": [],
            "game_state": {}
        }
        
        response = requests.post(
            f"{self.base_url}/api/agent/event",
            json=payload
        )
        response.raise_for_status()
        return response.json()
        
    def inject_instruction(self, content: str, level: str = "user") -> dict:
        """注入指令"""
        response = requests.post(
            f"{self.base_url}/api/agent/inject",
            json={"content": content, "level": level}
        )
        response.raise_for_status()
        return response.json()
        
    def control_agent(self, action: str) -> dict:
        """控制 Agent"""
        response = requests.post(
            f"{self.base_url}/api/agent/control",
            params={"action": action}
        )
        response.raise_for_status()
        return response.json()
        
    def reset_session(self) -> dict:
        """重置会话"""
        response = requests.post(f"{self.base_url}/api/agent/reset")
        response.raise_for_status()
        return response.json()
        
    def get_workflow(self) -> dict:
        """获取工作流"""
        response = requests.get(f"{self.base_url}/api/agent/workflow")
        response.raise_for_status()
        return response.json()
        
    # === Pack API ===
    
    def export_pack(self, file_path: str):
        """导出 Pack"""
        response = requests.get(
            f"{self.base_url}/api/pack/export",
            stream=True
        )
        response.raise_for_status()
        
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
    def import_pack(self, file_path: str) -> dict:
        """导入 Pack"""
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/api/pack/import",
                files={"file": f}
            )
        response.raise_for_status()
        return response.json()
