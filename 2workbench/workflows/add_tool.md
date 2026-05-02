# 工作流: 添加新 LangGraph Tool

## 步骤

1. **在 feature/ai/tools.py 中添加工具函数**:
```python
from langchain_core.tools import tool

@tool
def your_tool_name(param1: str, param2: int = 0) -> str:
    """工具描述（会被 LLM 看到）"""
    # 实现逻辑
    return "结果"
```

2. **在 graph.py 中绑定工具**:
在 `create_tools()` 函数中添加新工具。

3. **在 nodes.py 的 execute_commands 节点中处理**:
如果需要特殊处理，在命令执行逻辑中添加分支。

4. **在 tool_manager.py 中添加 UI 定义**:
在 `BUILTIN_TOOLS` 列表中添加 `ToolDefinition`。

5. **测试**:
```powershell
cd 2workbench ; python -c "
from feature.ai.tools import your_tool_name
result = your_tool_name.invoke({'param1': 'test'})
print(f'结果: {result}')
print('OK: 工具测试通过')
"
```
