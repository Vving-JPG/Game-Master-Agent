---
name: "pyqt6-development"
description: "Provides comprehensive PyQt6 GUI development guidance including installation, project structure, widgets, signals/slots, and best practices. Invoke when user wants to create PyQt6 applications, design GUI layouts, or needs PyQt6 coding assistance."
---

# PyQt6 Development

Comprehensive guide for building desktop GUI applications with PyQt6.

## Installation

```bash
# Basic installation
pip install PyQt6

# With additional modules
pip install PyQt6 PyQt6-tools

# Development tools (includes Qt Designer)
pip install pyqt6-tools
```

## Project Structure

```
my_pyqt_app/
├── main.py              # Application entry point
├── requirements.txt     # Dependencies
├── resources/
│   ├── icons/          # Icon files
│   ├── images/         # Image assets
│   └── styles/         # QSS stylesheets
├── ui/
│   ├── main_window.py  # Main window implementation
│   ├── widgets/        # Custom widgets
│   └── dialogs/        # Dialog implementations
├── core/
│   ├── models.py       # Data models
│   ├── controllers.py  # Business logic
│   └── utils.py        # Utility functions
└── tests/              # Unit tests
```

## Basic Application Template

```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My PyQt6 App")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        
        # Widgets
        self.label = QLabel("Hello PyQt6!")
        self.button = QPushButton("Click Me")
        self.button.clicked.connect(self.on_button_click)
        
        layout.addWidget(self.label)
        layout.addWidget(self.button)
    
    def on_button_click(self):
        self.label.setText("Button clicked!")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

## Core Concepts

### 1. Widgets Hierarchy

```
QObject
  └── QWidget
        ├── QMainWindow      # Main application window
        ├── QDialog          # Dialog windows
        ├── QLabel           # Text display
        ├── QPushButton      # Clickable button
        ├── QLineEdit        # Text input
        ├── QTextEdit        # Multi-line text
        ├── QComboBox        # Dropdown selection
        ├── QListWidget      # List display
        ├── QTableWidget     # Table display
        ├── QTreeWidget      # Tree display
        ├── QTabWidget       # Tabbed interface
        ├── QStackedWidget   # Stacked pages
        ├── QFrame           # Container frame
        └── QGroupBox        # Grouped container
```

### 2. Layouts

```python
from PyQt6.QtWidgets import (
    QVBoxLayout,    # Vertical layout
    QHBoxLayout,    # Horizontal layout
    QGridLayout,    # Grid layout
    QFormLayout,    # Form layout (label-field pairs)
    QStackedLayout  # Stacked layout (switchable pages)
)

# Example: Complex layout
class ComplexWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main horizontal layout
        main_layout = QHBoxLayout(central)
        
        # Left sidebar (vertical)
        sidebar = QVBoxLayout()
        sidebar.addWidget(QPushButton("Home"))
        sidebar.addWidget(QPushButton("Settings"))
        sidebar.addStretch()
        
        # Right content area (grid)
        content = QGridLayout()
        content.addWidget(QLabel("Name:"), 0, 0)
        content.addWidget(QLineEdit(), 0, 1)
        content.addWidget(QLabel("Email:"), 1, 0)
        content.addWidget(QLineEdit(), 1, 1)
        
        main_layout.addLayout(sidebar, 1)
        main_layout.addLayout(content, 3)
```

### 3. Signals and Slots

```python
from PyQt6.QtCore import pyqtSignal, QObject


class Communicate(QObject):
    """Custom signal emitter"""
    speak = pyqtSignal(str)  # Signal with string parameter


class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.c = Communicate()
        self.c.speak.connect(self.on_speak)  # Connect signal to slot
        
        button = QPushButton("Emit Signal")
        button.clicked.connect(self.emit_signal)
    
    def emit_signal(self):
        self.c.speak.emit("Hello from signal!")
    
    def on_speak(self, message):
        print(f"Received: {message}")


# Common built-in signals
button.clicked.connect(handler)           # Button click
line_edit.textChanged.connect(handler)    # Text changed
combo_box.currentIndexChanged.connect(h)  # Selection changed
slider.valueChanged.connect(handler)      # Value changed
timer.timeout.connect(handler)            # Timer timeout
```

### 4. Custom Widgets

```python
class CustomButton(QPushButton):
    """Custom button with additional functionality"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
    
    def mousePressEvent(self, event):
        # Custom mouse press behavior
        super().mousePressEvent(event)
        print("Custom button pressed!")
```

## Common UI Patterns

### Dialog Implementation

```python
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout


class InputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input Dialog")
        
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        
        layout.addRow("Name:", self.name_input)
        layout.addRow("Email:", self.email_input)
        
        # Button box
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_data(self):
        return {
            'name': self.name_input.text(),
            'email': self.email_input.text()
        }


# Usage
dialog = InputDialog(self)
if dialog.exec() == QDialog.DialogCode.Accepted:
    data = dialog.get_data()
    print(data)
```

### Table with Data

```python
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem


class DataTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Name", "Age", "City"])
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
    
    def populate_data(self, data):
        """Populate table with list of dicts"""
        self.setRowCount(len(data))
        for row, item in enumerate(data):
            self.setItem(row, 0, QTableWidgetItem(item.get('name', '')))
            self.setItem(row, 1, QTableWidgetItem(str(item.get('age', ''))))
            self.setItem(row, 2, QTableWidgetItem(item.get('city', '')))
```

### Threading (QThread)

```python
from PyQt6.QtCore import QThread, pyqtSignal


class WorkerThread(QThread):
    """Background worker thread"""
    progress = pyqtSignal(int)
    result = pyqtSignal(object)
    finished = pyqtSignal()
    
    def __init__(self, task_data):
        super().__init__()
        self.task_data = task_data
    
    def run(self):
        for i in range(100):
            # Simulate work
            self.msleep(50)
            self.progress.emit(i + 1)
        
        self.result.emit("Task completed!")
        self.finished.emit()


# Usage in main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
    
    def start_task(self):
        self.worker = WorkerThread("some data")
        self.worker.progress.connect(self.update_progress)
        self.worker.result.connect(self.handle_result)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def handle_result(self, result):
        print(result)
    
    def on_finished(self):
        self.worker = None
```

## Styling with QSS

```python
# Apply stylesheet to application
app.setStyleSheet("""
    QMainWindow {
        background-color: #f5f5f5;
    }
    
    QPushButton {
        background-color: #0078d4;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 13px;
    }
    
    QPushButton:hover {
        background-color: #106ebe;
    }
    
    QPushButton:disabled {
        background-color: #ccc;
    }
    
    QLineEdit {
        border: 1px solid #ccc;
        padding: 6px;
        border-radius: 3px;
    }
    
    QLineEdit:focus {
        border-color: #0078d4;
    }
    
    QTableWidget {
        gridline-color: #ddd;
        selection-background-color: #0078d4;
    }
    
    QHeaderView::section {
        background-color: #f0f0f0;
        padding: 5px;
        border: 1px solid #ddd;
        font-weight: bold;
    }
""")
```

## Best Practices

### 1. Separate UI from Logic

```python
# ui/main_window.py - UI only
class MainWindowUI:
    def setup_ui(self, main_window):
        # Create widgets and layouts only
        pass

# core/controller.py - Business logic
class MainController:
    def __init__(self, ui):
        self.ui = ui
        self.connect_signals()
    
    def connect_signals(self):
        self.ui.button.clicked.connect(self.handle_click)
    
    def handle_click(self):
        # Business logic here
        pass
```

### 2. Resource Management

```python
from PyQt6.QtCore import QDir
from PyQt6.QtGui import QIcon, QPixmap


class ResourceManager:
    """Centralized resource management"""
    
    @staticmethod
    def get_icon(name):
        return QIcon(f"resources/icons/{name}")
    
    @staticmethod
    def get_pixmap(name):
        return QPixmap(f"resources/images/{name}")
    
    @staticmethod
    def load_stylesheet(name):
        with open(f"resources/styles/{name}.qss", "r") as f:
            return f.read()
```

### 3. Error Handling

```python
from PyQt6.QtWidgets import QMessageBox


def show_error(parent, message, title="Error"):
    QMessageBox.critical(parent, title, message)


def show_warning(parent, message, title="Warning"):
    QMessageBox.warning(parent, title, message)


def show_info(parent, message, title="Information"):
    QMessageBox.information(parent, title, message)


def confirm_dialog(parent, message, title="Confirm"):
    reply = QMessageBox.question(
        parent, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes
```

### 4. Settings Persistence

```python
from PyQt6.QtCore import QSettings


class AppSettings:
    def __init__(self):
        self.settings = QSettings("MyCompany", "MyApp")
    
    def save_window_geometry(self, window):
        self.settings.setValue("geometry", window.saveGeometry())
        self.settings.setValue("windowState", window.saveState())
    
    def restore_window_geometry(self, window):
        geometry = self.settings.value("geometry")
        if geometry:
            window.restoreGeometry(geometry)
        state = self.settings.value("windowState")
        if state:
            window.restoreState(state)
```

## Common Pitfalls

1. **Never modify GUI from non-GUI threads** - Always use signals/slots
2. **Avoid long-running operations in main thread** - Use QThread
3. **Don't forget to call `super().__init__()`** in custom widgets
4. **Always pass parent to child widgets** for proper memory management
5. **Use `self` to keep references** to widgets that need to persist

## References

- [PyQt6 Official Docs](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Qt6 Documentation](https://doc.qt.io/qt-6/)
- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) - Modern UI components
