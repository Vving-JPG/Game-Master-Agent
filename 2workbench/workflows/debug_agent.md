# 工作流: 调试 Agent

## 常见问题排查

### 1. Agent 无响应
```powershell
cd 2workbench ; python -c "
from foundation.config import settings
print(f'API Key: {settings.deepseek_api_key[:10]}...')
print(f'Base URL: {settings.deepseek_base_url}')
print(f'Model: {settings.default_model}')
"
```

### 2. EventBus 事件未触发
```powershell
cd 2workbench ; python -c "
from foundation.event_bus import event_bus, Event
result = event_bus.emit(Event(type='test.debug', data={'key': 'value'}))
print(f'订阅者数量: {len(result)}')
"
```

### 3. 数据库连接问题
```powershell
cd 2workbench ; python -c "
from foundation.database import init_db, get_db
import tempfile, os
tmp = tempfile.mktemp(suffix='.db')
init_db(db_path=tmp)
db = get_db(db_path=tmp)
tables = db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print(f'表: {[t[0] for t in tables]}')
os.unlink(tmp)
"
```

### 4. LangGraph 图编译问题
```powershell
cd 2workbench ; python -c "
from feature.ai.graph import create_gm_graph
graph = create_gm_graph()
print(f'节点: {list(graph.nodes)}')
print(f'边: {list(graph.edges)}')
"
```

### 5. Feature 未启用
```powershell
cd 2workbench ; python -c "
from feature.registry import feature_registry
print(f'已注册: {feature_registry.list_features()}')
states = feature_registry.get_all_states()
for name, state in states.items():
    print(f'  {name}: enabled={state[\"enabled\"]}')
"
```
