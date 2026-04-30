# wb.spec
# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
PROJECT_ROOT = os.path.abspath('.')

# 收集数据文件
datas = [
    (os.path.join(PROJECT_ROOT, 'workbench', 'styles', 'dark_theme.qss'), 'workbench/styles'),
]

# 收集需要递归导入的模块
hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'frontmatter',
    'yaml',
    'qasync',
    'src',
    'src.memory',
    'src.memory.manager',
    'src.skills',
    'src.skills.loader',
    'workbench',
    'workbench.app',
    'workbench.main_window',
    'workbench.bridge',
    'workbench.bridge.agent_bridge',
    'workbench.widgets',
    'workbench.widgets.resource_tree',
    'workbench.widgets.editor_stack',
    'workbench.widgets.console_tabs',
    'workbench.widgets.agent_status',
    'workbench.widgets.resource_monitor',
    'workbench.widgets.md_editor',
    'workbench.widgets.yaml_editor',
    'workbench.widgets.kv_editor',
    'workbench.widgets.tool_viewer',
    'workbench.widgets.runtime_viewer',
    'workbench.widgets.workflow_editor',
]

# 收集 src 目录下的所有子模块
src_hiddenimports = collect_submodules('src')
hiddenimports.extend(src_hiddenimports)

a = Analysis(
    ['wb_entry.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'tkinter', 'IPython', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GameMasterAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 程序，不显示控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
