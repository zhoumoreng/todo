import json
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSizeGrip, QSystemTrayIcon, QMenu, QApplication,
    QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction, QColor, QPalette

SETTINGS_FILE = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')),
    'TodoFloat', 'settings.json'
)

DEFAULT_FONT_FAMILY = "Microsoft YaHei"
DEFAULT_FONT_SIZE = 10


def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    existing = load_settings()
    existing.update(data)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def apply_app_font(family: str, size: int):
    font = QFont(family, size)
    QApplication.setFont(font)


class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self._drag_pos = None
        self.setFixedHeight(42)
        self.setStyleSheet("""
            TitleBar {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F4F6F9
                );
                border-bottom: 1px solid #E8ECF2;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(4)

        # 彩色圆点装饰
        dot = QLabel("●")
        dot.setStyleSheet("color: #5B8AF5; font-size: 8px; margin-right: 4px;")
        layout.addWidget(dot)

        self.title_label = QLabel("待办清单")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #2D3748; letter-spacing: 1px;")
        layout.addWidget(self.title_label)
        layout.addStretch()

        # 设置按钮
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.setToolTip("字体设置")
        self.settings_btn.setStyleSheet(self._icon_btn_style())
        self.settings_btn.clicked.connect(parent.open_settings)
        layout.addWidget(self.settings_btn)

        # 折叠按钮
        self.collapse_btn = QPushButton("▲")
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setToolTip("折叠/展开")
        self.collapse_btn.setStyleSheet(self._icon_btn_style())
        self.collapse_btn.clicked.connect(parent.toggle_collapse)
        layout.addWidget(self.collapse_btn)

        # 关闭按钮
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setToolTip("最小化到托盘")
        self.close_btn.setStyleSheet(self._icon_btn_style(close=True))
        self.close_btn.clicked.connect(parent.hide_to_tray)
        layout.addWidget(self.close_btn)

    def _icon_btn_style(self, close=False):
        hover = "#FFE8E8" if close else "#EBF0FF"
        hover_color = "#E53E3E" if close else "#5B8AF5"
        return f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: #A0AEC0;
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {hover};
                color: {hover_color};
            }}
        """

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() -
                self.parent_window.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.parent_window.move(
                event.globalPosition().toPoint() - self._drag_pos
            )

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class FloatingPanel(QMainWindow):
    def __init__(self, todo_widget_class):
        super().__init__()
        self._collapsed = False
        self._todo_widget_class = todo_widget_class
        self._expanded_height = 520
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
        self.setMinimumSize(280, 220)
        self.setStyleSheet("""
            QMainWindow {
                background: #F8F9FB;
            }
            QMainWindow > QWidget {
                background: #F8F9FB;
                border: 1.5px solid #DDE3EE;
                border-radius: 10px;
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

        # ── 标签栏 ────────────────────────────────────────
        tab_bar = QWidget()
        tab_bar.setFixedHeight(34)
        tab_bar.setStyleSheet("background: #F4F6F9; border-bottom: 1px solid #E8ECF2;")
        tab_h = QHBoxLayout(tab_bar)
        tab_h.setContentsMargins(10, 4, 10, 4)
        tab_h.setSpacing(6)

        self._tab_today = QPushButton("今日")
        self._tab_all   = QPushButton("全部待办")
        for btn in (self._tab_today, self._tab_all):
            btn.setFixedHeight(24)
            btn.setStyleSheet("")
        self._tab_today.clicked.connect(lambda: self._switch_tab(0))
        self._tab_all.clicked.connect(lambda: self._switch_tab(1))
        tab_h.addWidget(self._tab_today)
        tab_h.addWidget(self._tab_all)
        tab_h.addStretch()
        self._main_layout.addWidget(tab_bar)
        self._apply_tab_style(0)

        # ── 内容区（堆叠切换）────────────────────────────
        from ui.todo_widget import AllTodosWidget
        self.stack = QStackedWidget()
        self.todo_widget = self._todo_widget_class()
        self.all_widget  = AllTodosWidget()
        self.stack.addWidget(self.todo_widget)   # index 0
        self.stack.addWidget(self.all_widget)    # index 1
        self._main_layout.addWidget(self.stack)

        # 右下角缩放手柄
        grip_row = QWidget()
        grip_row.setFixedHeight(14)
        grip_row.setStyleSheet("background: transparent;")
        grip_h = QHBoxLayout(grip_row)
        grip_h.setContentsMargins(0, 0, 2, 2)
        grip_h.addStretch()
        grip = QSizeGrip(self)
        grip.setStyleSheet("""
            QSizeGrip {
                width: 12px; height: 12px;
                background: transparent;
            }
        """)
        grip_h.addWidget(grip)
        self._main_layout.addWidget(grip_row)

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(
            QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_DialogApplyButton
            )
        )
        self.tray.setToolTip("待办清单")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
                color: #2D3748;
                font-size: 12px;
            }
            QMenu::item:selected { background: #EBF0FF; color: #5B8AF5; }
        """)
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
        h = settings.get('height', 520)
        x = settings.get('x', screen.right() - w - 10)
        y = settings.get('y', screen.top() + 10)
        self.setGeometry(x, y, w, h)

    def _save_geometry(self):
        geo = self.geometry()
        save_settings({
            'x': geo.x(), 'y': geo.y(),
            'width': geo.width(), 'height': geo.height()
        })

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self._apply_tab_style(index)
        if index == 1:
            self.all_widget.refresh()

    def _apply_tab_style(self, active: int):
        active_style = """
            QPushButton {
                background: #5B8AF5; color: white;
                border: none; border-radius: 5px;
                padding: 2px 12px; font-size: 11px; font-weight: bold;
            }
        """
        inactive_style = """
            QPushButton {
                background: transparent; color: #718096;
                border: 1px solid #E8ECF2; border-radius: 5px;
                padding: 2px 12px; font-size: 11px;
            }
            QPushButton:hover { background: #EBF0FF; color: #5B8AF5; }
        """
        self._tab_today.setStyleSheet(active_style if active == 0 else inactive_style)
        self._tab_all.setStyleSheet(active_style if active == 1 else inactive_style)

    def toggle_collapse(self):
        self._collapsed = not self._collapsed
        self.stack.setVisible(not self._collapsed)
        self.title_bar.collapse_btn.setText("▼" if self._collapsed else "▲")
        if self._collapsed:
            self._expanded_height = self.height()
            self.setFixedHeight(self.title_bar.height() + 16)
        else:
            self.setMinimumSize(280, 220)
            self.setMaximumSize(16777215, 16777215)
            self.resize(self.width(), self._expanded_height)

    def open_settings(self):
        from ui.settings_dialog import SettingsDialog
        settings = load_settings()
        family = settings.get('font_family', DEFAULT_FONT_FAMILY)
        size = settings.get('font_size', DEFAULT_FONT_SIZE)
        dlg = SettingsDialog(family, size, self)
        dlg.font_changed.connect(self._apply_font)
        dlg.exec()

    def _apply_font(self, family: str, size: int):
        save_settings({'font_family': family, 'font_size': size})
        apply_app_font(family, size)
        self.todo_widget._load_todos()
        self.all_widget.refresh()

    def hide_to_tray(self):
        self._save_geometry()
        self.hide()

    def show_panel(self):
        self.show()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide_to_tray()
