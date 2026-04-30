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
