# TodoFloat Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 Windows 桌面悬浮待办工具，打包为单个 exe，始终置顶右上角，支持今日/历史待办管理。

**Architecture:** PyQt6 无边框窗口置顶，标题栏支持拖拽和折叠，右下角支持缩放。TodoWidget 负责待办列表的展示与操作，database.py 封装所有 SQLite CRUD，系统托盘支持隐藏/退出。

**Tech Stack:** Python 3.x, PyQt6, SQLite3 (内置), PyInstaller

---

## Chunk 1: 项目结构 + 数据库层

### Task 1: 初始化项目结构

**Files:**
- Create: `requirements.txt`
- Create: `db/__init__.py`
- Create: `ui/__init__.py`

- [ ] **Step 1: 创建目录结构**

```bash
cd D:/XingGuiProject/dbsx
mkdir -p db ui
touch db/__init__.py ui/__init__.py
```

- [ ] **Step 2: 创建 requirements.txt**

内容：
```
PyQt6>=6.4.0
pyinstaller>=5.0
```

- [ ] **Step 3: 安装依赖**

```bash
pip install PyQt6 pyinstaller
```

Expected: 安装成功，无报错

---

### Task 2: 实现数据库层

**Files:**
- Create: `db/database.py`

- [ ] **Step 1: 创建 db/database.py**

```python
import sqlite3
import os
from datetime import datetime

def get_db_path():
    app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
    db_dir = os.path.join(app_data, 'TodoFloat')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'todo.db')

def get_connection():
    return sqlite3.connect(get_db_path())

def init_db():
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'normal',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_date ON todos(date)')
        conn.commit()

def add_todo(title: str, date: str, priority: str = 'normal') -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO todos (title, date, priority, completed, created_at) VALUES (?, ?, ?, 0, ?)',
            (title, date, priority, datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid

def get_todos_by_date(date: str) -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            'SELECT * FROM todos WHERE date = ? ORDER BY priority DESC, created_at ASC',
            (date,)
        )
        return [dict(row) for row in cursor.fetchall()]

def toggle_todo(todo_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute('SELECT completed FROM todos WHERE id = ?', (todo_id,))
        row = cursor.fetchone()
        if row is None:
            return False
        new_state = 0 if row[0] else 1
        conn.execute('UPDATE todos SET completed = ? WHERE id = ?', (new_state, todo_id))
        conn.commit()
        return bool(new_state)

def delete_todo(todo_id: int):
    with get_connection() as conn:
        conn.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        conn.commit()

def get_dates_with_todos() -> list[str]:
    with get_connection() as conn:
        cursor = conn.execute('SELECT DISTINCT date FROM todos ORDER BY date DESC')
        return [row[0] for row in cursor.fetchall()]
```

- [ ] **Step 2: 验证数据库模块**

```bash
cd D:/XingGuiProject/dbsx
python -c "
from db.database import init_db, add_todo, get_todos_by_date, toggle_todo, delete_todo
init_db()
tid = add_todo('测试任务', '2026-03-11', 'urgent')
print('添加成功 id:', tid)
todos = get_todos_by_date('2026-03-11')
print('查询结果:', todos)
toggle_todo(tid)
todos = get_todos_by_date('2026-03-11')
print('切换完成后:', todos[0]['completed'])
delete_todo(tid)
print('删除成功')
"
```

Expected: 输出 `添加成功 id: 1`，查询结果包含该任务，完成状态变为 1，删除成功

---

## Chunk 2: 悬浮面板主窗口

### Task 3: 实现悬浮面板

**Files:**
- Create: `ui/floating_panel.py`

- [ ] **Step 1: 创建 ui/floating_panel.py**

```python
import json
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSizeGrip, QSystemTrayIcon, QMenu, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QSize, QSettings
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QAction

SETTINGS_FILE = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')),
    'TodoFloat', 'settings.json'
)

def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f)


class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self._drag_pos = None
        self.setFixedHeight(36)
        self.setStyleSheet("""
            TitleBar {
                background-color: #f0f0f0;
                border-bottom: 1px solid #ddd;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(4)

        self.title_label = QLabel("待办清单")
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #333;")
        layout.addWidget(self.title_label)
        layout.addStretch()

        self.collapse_btn = QPushButton("▲")
        self.collapse_btn.setFixedSize(24, 24)
        self.collapse_btn.setStyleSheet(self._btn_style())
        self.collapse_btn.clicked.connect(parent.toggle_collapse)
        layout.addWidget(self.collapse_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet(self._btn_style("#e74c3c"))
        self.close_btn.clicked.connect(parent.hide_to_tray)
        layout.addWidget(self.close_btn)

    def _btn_style(self, hover_color="#cccccc"):
        return f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: #666;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {hover_color};
                color: white;
            }}
        """

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.parent_window.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class FloatingPanel(QMainWindow):
    def __init__(self, todo_widget_class):
        super().__init__()
        self._collapsed = False
        self._todo_widget_class = todo_widget_class
        self._setup_window()
        self._setup_ui()
        self._setup_tray()
        self._restore_geometry()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(280, 200)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
        """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        self._main_layout.addWidget(self.title_bar)

        self.todo_widget = self._todo_widget_class()
        self._main_layout.addWidget(self.todo_widget)

        # 右下角缩放手柄
        grip_container = QWidget()
        grip_layout = QHBoxLayout(grip_container)
        grip_layout.setContentsMargins(0, 0, 2, 2)
        grip_layout.addStretch()
        grip = QSizeGrip(self)
        grip.setStyleSheet("QSizeGrip { width: 14px; height: 14px; }")
        grip_layout.addWidget(grip)
        self._main_layout.addWidget(grip_container)

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        # 使用内置图标
        self.tray.setIcon(QApplication.style().standardIcon(
            QApplication.style().StandardPixmap.SP_DialogApplyButton
        ))
        self.tray.setToolTip("待办清单")

        tray_menu = QMenu()
        show_action = QAction("显示面板", self)
        show_action.triggered.connect(self.show_panel)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_panel()

    def _restore_geometry(self):
        settings = load_settings()
        screen = QApplication.primaryScreen().availableGeometry()
        w = settings.get('width', 360)
        h = settings.get('height', 500)
        x = settings.get('x', screen.right() - w - 10)
        y = settings.get('y', screen.top() + 10)
        self.setGeometry(x, y, w, h)

    def _save_geometry(self):
        geo = self.geometry()
        save_settings({
            'x': geo.x(), 'y': geo.y(),
            'width': geo.width(), 'height': geo.height()
        })

    def toggle_collapse(self):
        self._collapsed = not self._collapsed
        self.todo_widget.setVisible(not self._collapsed)
        self.title_bar.collapse_btn.setText("▼" if self._collapsed else "▲")
        if self._collapsed:
            self._expanded_height = self.height()
            self.setFixedHeight(self.title_bar.height() + 30)
        else:
            self.setMinimumSize(280, 200)
            self.setMaximumSize(16777215, 16777215)
            self.resize(self.width(), getattr(self, '_expanded_height', 500))

    def hide_to_tray(self):
        self._save_geometry()
        self.hide()

    def show_panel(self):
        self.show()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide_to_tray()
```

- [ ] **Step 2: 快速语法检查**

```bash
cd D:/XingGuiProject/dbsx
python -c "from ui.floating_panel import FloatingPanel; print('OK')"
```

Expected: 输出 `OK`

---

## Chunk 3: 待办列表组件

### Task 4: 实现 TodoWidget

**Files:**
- Create: `ui/todo_widget.py`

- [ ] **Step 1: 创建 ui/todo_widget.py**

```python
from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QScrollArea, QCheckBox, QFrame,
    QDateEdit, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QAction
from db.database import get_todos_by_date, add_todo, toggle_todo, delete_todo


class TodoItem(QWidget):
    def __init__(self, todo: dict, on_toggle, on_delete, parent=None):
        super().__init__(parent)
        self.todo = todo
        self.on_toggle = on_toggle
        self.on_delete = on_delete
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(bool(self.todo['completed']))
        self.checkbox.toggled.connect(lambda: self.on_toggle(self.todo['id']))
        layout.addWidget(self.checkbox)

        self.text_label = QLabel(self.todo['title'])
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        font = QFont()
        font.setPointSize(9)
        self.text_label.setFont(font)
        self._update_text_style()
        layout.addWidget(self.text_label)

        priority_label = QLabel("紧急" if self.todo['priority'] == 'urgent' else "一般")
        priority_label.setFixedWidth(32)
        priority_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.todo['priority'] == 'urgent':
            priority_label.setStyleSheet(
                "background: #e74c3c; color: white; border-radius: 3px; font-size: 9px; padding: 1px 2px;"
            )
        else:
            priority_label.setStyleSheet(
                "background: #bbb; color: white; border-radius: 3px; font-size: 9px; padding: 1px 2px;"
            )
        layout.addWidget(priority_label)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setStyleSheet("TodoItem:hover { background: #f8f8f8; }")

    def _update_text_style(self):
        if self.todo['completed']:
            self.text_label.setStyleSheet("color: #aaa; text-decoration: line-through;")
        else:
            self.text_label.setStyleSheet("color: #333;")

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.on_delete(self.todo['id']))
        menu.addAction(delete_action)
        menu.exec(self.mapToGlobal(pos))


class TodoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_date = date.today().isoformat()
        self._build_ui()
        self._load_todos()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 日期导航栏
        date_bar = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(24, 24)
        self.prev_btn.setStyleSheet(self._nav_btn_style())
        self.prev_btn.clicked.connect(self._prev_day)

        self.date_label = QPushButton()
        self.date_label.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #333;
                font-size: 11px;
                padding: 2px 8px;
            }
            QPushButton:hover { background: #f0f0f0; }
        """)
        self.date_label.clicked.connect(self._pick_date)

        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(24, 24)
        self.next_btn.setStyleSheet(self._nav_btn_style())
        self.next_btn.clicked.connect(self._next_day)

        date_bar.addWidget(self.prev_btn)
        date_bar.addStretch()
        date_bar.addWidget(self.date_label)
        date_bar.addStretch()
        date_bar.addWidget(self.next_btn)
        layout.addLayout(date_bar)

        # 统计标签
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #888; font-size: 9px;")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stats_label)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #eee;")
        layout.addWidget(line)

        # 待办列表（可滚动）
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_container)
        layout.addWidget(self.scroll)

        # 空状态标签
        self.empty_label = QLabel("暂无待办，添加一个吧 ✓")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #bbb; font-size: 11px;")
        layout.addWidget(self.empty_label)

        # 输入区
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background: #f9f9f9;
                border: 1px solid #eee;
                border-radius: 6px;
            }
        """)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(6, 6, 6, 6)
        input_layout.setSpacing(4)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("添加待办...")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                background: white;
            }
            QLineEdit:focus { border-color: #4a9eff; }
        """)
        self.input_edit.returnPressed.connect(self._add_todo)
        input_layout.addWidget(self.input_edit)

        bottom_row = QHBoxLayout()
        self.priority_combo = QComboBox()
        self.priority_combo.addItem("一般", "normal")
        self.priority_combo.addItem("紧急", "urgent")
        self.priority_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 10px;
                background: white;
            }
        """)
        bottom_row.addWidget(self.priority_combo)

        add_btn = QPushButton("添加")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #4a9eff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 14px;
                font-size: 10px;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        add_btn.clicked.connect(self._add_todo)
        bottom_row.addWidget(add_btn)
        input_layout.addLayout(bottom_row)

        layout.addWidget(input_frame)
        self._update_date_label()

    def _nav_btn_style(self):
        return """
            QPushButton {
                background: transparent;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #666;
                font-size: 10px;
            }
            QPushButton:hover { background: #f0f0f0; }
        """

    def _update_date_label(self):
        today = date.today().isoformat()
        if self._current_date == today:
            d = date.fromisoformat(self._current_date)
            self.date_label.setText(f"今天 {d.month:02d}-{d.day:02d}")
        else:
            self.date_label.setText(self._current_date)

    def _prev_day(self):
        d = date.fromisoformat(self._current_date) - timedelta(days=1)
        self._current_date = d.isoformat()
        self._update_date_label()
        self._load_todos()

    def _next_day(self):
        d = date.fromisoformat(self._current_date) + timedelta(days=1)
        self._current_date = d.isoformat()
        self._update_date_label()
        self._load_todos()

    def _pick_date(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QCalendarWidget, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("选择日期")
        dialog.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        vbox = QVBoxLayout(dialog)
        vbox.setContentsMargins(4, 4, 4, 4)
        cal = QCalendarWidget()
        cal.setSelectedDate(QDate.fromString(self._current_date, "yyyy-MM-dd"))
        cal.setGridVisible(True)
        cal.setStyleSheet("QCalendarWidget { font-size: 10px; }")
        cal.clicked.connect(lambda d: (
            setattr(self, '_current_date', d.toString("yyyy-MM-dd")),
            self._update_date_label(),
            self._load_todos(),
            dialog.accept()
        ))
        vbox.addWidget(cal)
        # 定位到按钮下方
        btn_pos = self.date_label.mapToGlobal(self.date_label.rect().bottomLeft())
        dialog.move(btn_pos)
        dialog.exec()

    def _load_todos(self):
        # 清除旧列表（保留最后的 stretch）
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        todos = get_todos_by_date(self._current_date)

        # 更新统计
        total = len(todos)
        done = sum(1 for t in todos if t['completed'])
        self.stats_label.setText(f"共 {total} 项，已完成 {done} 项" if total else "")

        # 空状态
        self.empty_label.setVisible(total == 0)
        self.scroll.setVisible(total > 0)

        # 先显示紧急未完成，再一般未完成，最后已完成
        def sort_key(t):
            return (t['completed'], 0 if t['priority'] == 'urgent' else 1)

        for todo in sorted(todos, key=sort_key):
            item_widget = TodoItem(
                todo,
                on_toggle=self._handle_toggle,
                on_delete=self._handle_delete
            )
            self.list_layout.insertWidget(self.list_layout.count() - 1, item_widget)

    def _handle_toggle(self, todo_id: int):
        toggle_todo(todo_id)
        self._load_todos()

    def _handle_delete(self, todo_id: int):
        delete_todo(todo_id)
        self._load_todos()

    def _add_todo(self):
        title = self.input_edit.text().strip()
        if not title:
            return
        priority = self.priority_combo.currentData()
        add_todo(title, self._current_date, priority)
        self.input_edit.clear()
        self._load_todos()
```

- [ ] **Step 2: 语法检查**

```bash
cd D:/XingGuiProject/dbsx
python -c "from ui.todo_widget import TodoWidget; print('OK')"
```

Expected: 输出 `OK`

---

## Chunk 4: 主入口 + 打包

### Task 5: 实现主入口

**Files:**
- Create: `main.py`

- [ ] **Step 1: 创建 main.py**

```python
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from db.database import init_db
from ui.floating_panel import FloatingPanel
from ui.todo_widget import TodoWidget


def main():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，仅隐藏到托盘

    # 初始化数据库
    init_db()

    # 创建主窗口
    panel = FloatingPanel(TodoWidget)
    panel.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 运行应用测试**

```bash
cd D:/XingGuiProject/dbsx
python main.py
```

Expected: 悬浮面板出现在屏幕右上角，可拖拽、折叠、添加待办

---

### Task 6: 打包为 exe

**Files:**
- Create: `build.spec` (PyInstaller spec 文件)

- [ ] **Step 1: 生成初始 spec**

```bash
cd D:/XingGuiProject/dbsx
pyinstaller --onefile --windowed --name TodoFloat main.py
```

- [ ] **Step 2: 验证 exe**

```bash
dist/TodoFloat.exe
```

Expected: 程序正常启动，功能与开发模式一致

- [ ] **Step 3: （可选）添加图标**

若有 `.ico` 文件，重新打包：
```bash
pyinstaller --onefile --windowed --name TodoFloat --icon=icon.ico main.py
```
