# Game Master Agent V2 - PKG: Electron 桌面打包

> 本文件是 Trae AI 助手的项目指引。请严格按照以下步骤和规范执行。

## 项目概述

你正在帮助用户将已完成的 Game Master Agent V2 **打包成桌面应用程序**（类似 Trae）。
- **目标**: 双击 exe → 弹出 WorkBench 窗口 → 直接使用
- **技术栈**: Electron (壳) + Vue 3 (前端) + Python FastAPI (后端) + PyInstaller (Python 打包)
- **包管理器**: 前端 npm / 后端 uv
- **开发IDE**: Trae

### 架构说明

打包后的程序结构：

```
GameMasterAgent.exe (Electron 主进程)
  ├── 渲染进程: 加载 Vue 前端 (本地 file:// 或 localhost)
  ├── 子进程: 启动 python_backend.exe (FastAPI 后端)
  └── 通信: 渲染进程 ↔ localhost:8000 ↔ Python 后端
```

用户双击 exe 后的流程：
1. Electron 主进程启动
2. 自动启动 python_backend.exe 子进程
3. 等待后端就绪 (轮询 localhost:8000/health)
4. 打开窗口，加载 Vue 前端
5. 用户看到 WorkBench，直接使用
6. 关闭窗口时，自动终止 python_backend.exe 子进程

### 前置条件

**P0-P4 + W1-W7 全部完成**。以下模块全部就绪：

**后端**:
- `src/` — 完整的 Python 后端 (FastAPI + Agent + Memory + Skills + Adapters)
- `prompts/system_prompt.md` — Agent 主提示词
- 226+ 测试通过

**前端**:
- `workbench/` — Vue 3 + Naive UI + Vue Flow + Vite
- 22 个组件 (布局/编辑器/面板/状态管理)
- `npm run build` 能产出 `dist/` 静态文件

### PKG 阶段目标

1. **Python 后端打包** — PyInstaller 将 FastAPI 后端打包成独立 exe
2. **Electron 壳** — 创建 Electron 主进程，管理窗口和子进程
3. **前端集成** — Vue 构建产物嵌入 Electron
4. **打包配置** — electron-builder 配置，产出安装包
5. **测试验证** — 双击 exe → 完整流程可用

## 行为准则

1. **一步一步执行**：严格按照下方步骤顺序执行，每完成一步都验证通过后再进行下一步
2. **先验证再继续**：每个步骤都有"验收标准"，必须验证通过才能继续
3. **主动执行**：用户说"开始"后，你应该主动执行每一步，不需要用户反复催促
4. **遇到错误先尝试解决**：如果某步出错，先尝试自行排查修复，3次失败后再询问用户
5. **每步完成后汇报**：完成一步后，简要汇报结果和下一步计划
6. **代码规范**：
   - 所有文件使用 UTF-8 编码
   - Python 文件使用中文注释
   - JavaScript/TypeScript 使用英文注释
   - 遵循 PEP 8 / ESLint 规范

---

## 参考文档

- `docs/architecture_v2.md` — V2 架构总览
- `docs/dev_plan_v2.md` — V2 开发计划
- `workbench/` — Vue 前端源码
- `src/` — Python 后端源码

## 项目路径

- **项目根目录**: 当前 Trae 工作区
- **后端入口**: `src/api/app.py` (FastAPI 应用)
- **前端入口**: `workbench/src/main.ts`
- **前端构建**: `workbench/dist/` (npm run build 产出)

---

## 步骤

### Step 1: Python 后端打包准备

**目的**: 让 PyInstaller 能正确打包 FastAPI 后端为独立 exe。

**方案**:

1.1 在项目根目录创建 `backend_entry.py`，作为 PyInstaller 入口：

```python
# backend_entry.py
"""PyInstaller 打包入口。启动 FastAPI 后端服务。"""
import sys
import os
import uvicorn

# 将 src 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
```

1.2 创建 `backend.spec` (PyInstaller 配置)：

```python
# backend.spec
# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 项目根目录
PROJECT_ROOT = os.path.abspath('.')

# 收集所有需要的数据文件
datas = [
    # workspace 目录 (记忆文件)
    (os.path.join(PROJECT_ROOT, 'workspace'), 'workspace'),
    # skills 目录 (Skill 文件)
    (os.path.join(PROJECT_ROOT, 'skills'), 'skills'),
    # prompts 目录 (系统提示词)
    (os.path.join(PROJECT_ROOT, 'prompts'), 'prompts'),
]

# 收集 Python 包的隐藏导入
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'multipart',
    'anyio._backends._asyncio',
    'frontmatter',
    'openai',
    'aiosqlite',
    'httpx',
    'sse_starlette',
]

a = Analysis(
    ['backend_entry.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'IPython', 'jupyter', 'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='python_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='python_backend',
)
```

1.3 确认 `src/api/app.py` 有 `create_app()` 工厂函数（如果没有，需要重构）：

```python
# src/api/app.py 中应该有:
def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(title="Game Master Agent", version="2.0")
    # ... 注册路由等
    return app
```

1.4 添加健康检查端点（Electron 需要轮询判断后端是否就绪）：

在 `src/api/routes/` 下新增或修改，确保有 `/health` 端点：

```python
@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

**验收**:
- [ ] `backend_entry.py` 存在且可独立运行 (`python backend_entry.py` 启动 FastAPI)
- [ ] `backend.spec` 存在
- [ ] `src/api/app.py` 有 `create_app()` 工厂函数
- [ ] `GET /health` 返回 `{"status": "ok"}`

---

### Step 2: PyInstaller 打包 Python 后端

**目的**: 将 Python 后端打包成独立的 `python_backend.exe`。

**方案**:

2.1 安装 PyInstaller：

```bash
uv pip install pyinstaller
```

2.2 执行打包：

```bash
pyinstaller backend.spec --clean
```

2.3 验证打包产物：

```bash
# 检查产物目录
dir dist\python_backend\
# 应该看到 python_backend.exe 和一堆依赖文件
```

2.4 测试打包后的 exe：

```bash
# 启动打包后的后端
dist\python_backend\python_backend.exe 8000
# 另一个终端测试
curl http://127.0.0.1:8000/health
# 应该返回 {"status": "ok"}
```

**验收**:
- [ ] `dist/python_backend/python_backend.exe` 存在
- [ ] 双击或命令行启动后，`curl http://127.0.0.1:8000/health` 返回 `{"status": "ok"}`
- [ ] 不显示控制台黑窗口

---

### Step 3: 创建 Electron 主进程

**目的**: 创建 Electron 应用，作为桌面程序的"壳"。

**方案**:

3.1 在项目根目录创建 `electron/` 目录：

```
electron/
├── main.js          # Electron 主进程
├── preload.js       # 预加载脚本 (安全桥接)
└── package.json     # Electron 依赖
```

3.2 创建 `electron/package.json`：

```json
{
  "name": "game-master-agent",
  "version": "2.0.0",
  "description": "Game Master Agent - Universal Game-Driving Agent Service",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder",
    "build:win": "electron-builder --win",
    "build:mac": "electron-builder --mac",
    "build:linux": "electron-builder --linux"
  },
  "devDependencies": {
    "electron": "^33.0.0",
    "electron-builder": "^25.0.0"
  },
  "build": {
    "appId": "com.gamemaster.agent",
    "productName": "Game Master Agent",
    "directories": {
      "output": "../release"
    },
    "files": [
      "main.js",
      "preload.js",
      "../workbench/dist/**/*"
    ],
    "extraResources": [
      {
        "from": "../dist/python_backend",
        "to": "python_backend"
      },
      {
        "from": "../workspace",
        "to": "workspace"
      },
      {
        "from": "../skills",
        "to": "skills"
      },
      {
        "from": "../prompts",
        "to": "prompts"
      }
    ],
    "win": {
      "target": [
        {
          "target": "nsis",
          "arch": ["x64"]
        }
      ],
      "icon": "icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "shortcutName": "Game Master Agent"
    }
  }
}
```

3.3 创建 `electron/main.js`：

```javascript
// electron/main.js
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow = null;
let backendProcess = null;
const BACKEND_PORT = 8000;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

/**
 * 启动 Python 后端子进程
 */
function startBackend() {
  // 判断是开发环境还是打包环境
  const isDev = !app.isPackaged;

  let backendExe;
  if (isDev) {
    // 开发环境: 直接用 python 启动
    backendExe = process.platform === 'win32' ? 'python' : 'python3';
  } else {
    // 打包环境: 使用打包好的 exe
    backendExe = path.join(process.resourcesPath, 'python_backend', 'python_backend.exe');
  }

  const args = isDev
    ? [path.join(__dirname, '..', 'backend_entry.py'), String(BACKEND_PORT)]
    : [String(BACKEND_PORT)];

  console.log(`Starting backend: ${backendExe} ${args.join(' ')}`);

  backendProcess = spawn(backendExe, args, {
    cwd: isDev ? path.join(__dirname, '..') : path.join(process.resourcesPath, 'python_backend'),
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env }
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend] ${data}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });
}

/**
 * 轮询等待后端就绪
 */
function waitForBackend(maxRetries = 30, interval = 1000) {
  return new Promise((resolve, reject) => {
    let retries = 0;

    const check = () => {
      http.get(`${BACKEND_URL}/health`, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          console.log(`Backend ready: ${data}`);
          resolve();
        });
      }).on('error', () => {
        retries++;
        if (retries >= maxRetries) {
          reject(new Error('Backend failed to start'));
        } else {
          setTimeout(check, interval);
        }
      });
    };

    check();
  });
}

/**
 * 创建主窗口
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 600,
    title: 'Game Master Agent',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, 'icon.ico'),
  });

  // 加载 Vue 前端
  const isDev = !app.isPackaged;
  if (isDev) {
    // 开发环境: 连接 Vite dev server
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // 打包环境: 加载构建产物
    mainWindow.loadFile(path.join(__dirname, '..', 'workbench', 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/**
 * 终止后端进程
 */
function killBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

// App 生命周期
app.whenReady().then(async () => {
  try {
    // 1. 启动后端
    startBackend();

    // 2. 等待后端就绪
    await waitForBackend();

    // 3. 创建窗口
    createWindow();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      }
    });
  } catch (err) {
    console.error('Failed to start:', err);
    // 显示错误窗口
    const { dialog } = require('electron');
    dialog.showErrorBox('启动失败', `后端服务启动失败: ${err.message}`);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  killBackend();
  app.quit();
});

app.on('before-quit', () => {
  killBackend();
});

// IPC 处理
ipcMain.handle('get-backend-url', () => BACKEND_URL);
```

3.4 创建 `electron/preload.js`：

```javascript
// electron/preload.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  platform: process.platform,
  isPackaged: process.env.NODE_ENV !== 'development',
});
```

**验收**:
- [ ] `electron/main.js` 存在
- [ ] `electron/preload.js` 存在
- [ ] `electron/package.json` 存在
- [ ] `cd electron && npm install` 成功

---

### Step 4: 前端构建与集成

**目的**: 确保 Vue 前端能正确构建，并在 Electron 中加载。

**方案**:

4.1 修改 `workbench/vite.config.ts`，添加 Electron 兼容配置：

```typescript
// workbench/vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  base: './',  // 使用相对路径，Electron file:// 加载需要
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // Electron 环境下不需要代码分割
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
});
```

4.2 修改前端 API 基础 URL 配置，支持 Electron 环境：

在前端 stores 或 api 配置中，API 请求应始终使用相对路径 `/api/...`，而不是绝对路径。这样在开发环境通过 Vite proxy 转发，在打包环境直接请求 `localhost:8000`。

检查 `workbench/src/` 下所有 API 调用，确保：
- 使用 `fetch('/api/...')` 或 `axios.get('/api/...')` (相对路径)
- **不要**硬编码 `http://localhost:8000`

4.3 构建前端：

```bash
cd workbench
npm run build
```

4.4 验证构建产物：

```bash
dir workbench\dist\
# 应该看到 index.html + assets/ 目录
```

**验收**:
- [ ] `vite.config.ts` 中 `base: './'` 已设置
- [ ] 所有 API 调用使用相对路径
- [ ] `npm run build` 成功，`workbench/dist/index.html` 存在
- [ ] 在浏览器中直接打开 `workbench/dist/index.html` 能看到界面（可能有 API 报错，但界面能渲染）

---

### Step 5: Electron 开发模式测试

**目的**: 在开发环境中验证 Electron + 后端 + 前端的完整流程。

**方案**:

5.1 启动后端（终端 1）：

```bash
python backend_entry.py 8000
```

5.2 启动前端 dev server（终端 2）：

```bash
cd workbench
npm run dev
```

5.3 启动 Electron（终端 3）：

```bash
cd electron
npm start
```

5.4 验证：
- Electron 窗口弹出
- 显示 Vue 前端界面
- 能看到 WorkBench 界面（左侧资源树、中间编辑器、右侧状态面板）
- 关闭 Electron 窗口后，后端进程也被终止

**验收**:
- [ ] Electron 窗口正常弹出
- [ ] WorkBench 界面完整显示
- [ ] API 请求正常（左侧资源树能加载数据）
- [ ] 关闭窗口后后端进程终止

---

### Step 6: Electron 生产打包

**目的**: 使用 electron-builder 打包成安装程序。

**方案**:

6.1 确保前端已构建：

```bash
cd workbench
npm run build
```

6.2 确保后端已打包：

```bash
pyinstaller backend.spec --clean
```

6.3 安装 electron-builder：

```bash
cd electron
npm install
```

6.4 执行打包：

```bash
cd electron
npm run build:win
```

6.5 验证打包产物：

```bash
dir ..\release\
# 应该看到:
#   Game Master Agent Setup x.x.x.exe  (安装程序)
#   或 win-unpacked/ 目录 (免安装版)
```

6.6 测试免安装版：

```bash
# 直接运行免安装版
..\release\win-unpacked\Game Master Agent.exe
# 验证:
# 1. 窗口弹出
# 2. WorkBench 界面显示
# 3. API 正常工作
# 4. 关闭程序后进程全部退出
```

**验收**:
- [ ] `release/Game Master Agent Setup x.x.x.exe` 存在
- [ ] 安装后能正常启动
- [ ] WorkBench 界面完整显示
- [ ] API 请求正常
- [ ] 关闭程序后无残留进程

---

### Step 7: 创建启动脚本 (开发便利)

**目的**: 提供一键启动开发环境的脚本。

**方案**:

7.1 创建 `dev.bat` (Windows)：

```batch
@echo off
echo ========================================
echo  Game Master Agent - Dev Mode
echo ========================================

echo [1/3] Starting Python backend...
start "Backend" cmd /k "python backend_entry.py 8000"

echo [2/3] Waiting for backend...
timeout /t 3 /nobreak > nul

echo [3/3] Starting Electron...
cd electron
npm start
```

7.2 创建 `dev.sh` (macOS/Linux)：

```bash
#!/bin/bash
echo "========================================"
echo " Game Master Agent - Dev Mode"
echo "========================================"

echo "[1/3] Starting Python backend..."
python3 backend_entry.py 8000 &
BACKEND_PID=$!

echo "[2/3] Waiting for backend..."
sleep 3

echo "[3/3] Starting Electron..."
cd electron
npm start

# Cleanup
kill $BACKEND_PID 2>/dev/null
```

**验收**:
- [ ] `dev.bat` 存在，双击能启动完整开发环境
- [ ] `dev.sh` 存在，`bash dev.sh` 能启动完整开发环境

---

### Step 8: 最终验证

**目的**: 确保打包后的程序完整可用。

**方案**:

8.1 清理并重新完整打包：

```bash
# 清理
rmdir /s /q dist
rmdir /s /q release
rmdir /s /q workbench\dist

# 1. 构建前端
cd workbench && npm run build && cd ..

# 2. 打包后端
pyinstaller backend.spec --clean

# 3. 打包 Electron
cd electron && npm run build:win && cd ..
```

8.2 安装测试：

```
1. 运行 release/Game Master Agent Setup x.x.x.exe
2. 选择安装目录
3. 安装完成后启动
4. 验证 WorkBench 界面
5. 验证 API 功能 (资源树加载、编辑器打开、Agent 状态)
6. 关闭程序
7. 检查任务管理器，确认无残留进程
```

8.3 卸载测试：

```
1. 控制面板 → 卸载 Game Master Agent
2. 确认安装目录被清理
```

**验收**:
- [ ] 完整打包流程无错误
- [ ] 安装程序能正常安装
- [ ] 启动后 WorkBench 完整可用
- [ ] 关闭后无残留进程
- [ ] 卸载正常

---

## 注意事项

### PyInstaller 踩坑
1. **隐藏导入**: FastAPI + uvicorn 有很多动态导入，必须在 `hiddenimports` 中列出
2. **数据文件**: workspace/、skills/、prompts/ 必须作为 datas 打包
3. **路径问题**: 打包后 `__file__` 路径变化，使用 `sys._MEIPASS` 获取资源路径
4. **UPX**: 如果 UPX 压缩导致问题，设置 `upx=False`
5. **控制台窗口**: `console=False` 隐藏黑窗口，调试时改为 `True`

### Electron 踩坑
1. **子进程管理**: 必须在 app quit 时 kill 后端进程，否则会残留
2. **CORS**: FastAPI 需要配置 CORS 允许 Electron 访问
3. **file:// 协议**: 打包后前端通过 file:// 加载，API 请求走 localhost
4. **路径分隔符**: Windows 用 `\`，macOS/Linux 用 `/`，用 `path.join()`
5. **图标**: 需要 .ico (Windows) / .icns (macOS) 格式

### FastAPI CORS 配置
确保 `src/api/app.py` 中有 CORS 中间件：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Electron 环境下可以放宽
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 打包体积优化
- PyInstaller: `excludes` 排除不需要的大型库 (matplotlib, numpy, pandas 等)
- Electron: electron-builder 默认会压缩，最终安装包约 150-250MB
- 如果体积太大，考虑用 `--dir` 模式生成免安装目录而非安装程序

---

## 完成检查清单

- [ ] Step 1: `backend_entry.py` + `backend.spec` + `/health` 端点
- [ ] Step 2: `dist/python_backend/python_backend.exe` 可独立运行
- [ ] Step 3: `electron/` 目录创建，`npm install` 成功
- [ ] Step 4: 前端 `npm run build` 成功，相对路径 API
- [ ] Step 5: Electron 开发模式三端联调成功
- [ ] Step 6: `electron-builder` 打包成功，安装程序可用
- [ ] Step 7: `dev.bat` / `dev.sh` 一键启动脚本
- [ ] Step 8: 完整安装→使用→卸载流程验证通过
