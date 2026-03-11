from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QScrollArea, QCheckBox, QFrame,
    QSizePolicy, QMenu, QDialog, QCalendarWidget, QProgressBar,
    QPlainTextEdit
)
from PyQt6.QtCore import Qt, QDate, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QColor, QPainter, QPen, QBrush
from db.database import get_todos_by_date, add_todo, toggle_todo, delete_todo, get_all_todos


class RoundCheckBox(QWidget):
    """自绘圆形复选框：未选=空心圆，已选=蓝色实心圆+白色✓"""
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, v: bool):
        self._checked = v
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = 8
        cx, cy = self.width() // 2, self.height() // 2

        if self._checked:
            # 蓝色实心圆
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(CLR_PRIMARY)))
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            # 白色 ✓
            pen = QPen(QColor("#FFFFFF"), 2, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            from PyQt6.QtCore import QPointF
            p.drawPolyline([
                QPointF(cx - 4, cy),
                QPointF(cx - 1, cy + 3.5),
                QPointF(cx + 4.5, cy - 3.5),
            ])
        else:
            # 空心圆
            pen = QPen(QColor(CLR_BORDER), 2)
            p.setPen(pen)
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        p.end()


class AutoResizeTextEdit(QPlainTextEdit):
    """随内容自动伸缩高度的多行输入框，Enter 提交，Shift+Enter 换行"""

    submitted = None  # 由外部赋值为回调函数

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._min_height = 72   # 约 3 行高度
        self._max_height = 160
        self.setFixedHeight(self._min_height)
        self.document().contentsChanged.connect(self._adjust_height)

    def _adjust_height(self):
        doc_h = int(self.document().size().height())
        margins = self.contentsMargins()
        new_h = doc_h + margins.top() + margins.bottom() + 6
        new_h = max(self._min_height, min(new_h, self._max_height))
        self.setFixedHeight(new_h)

    def keyPressEvent(self, event):
        # Enter 提交；Shift+Enter 插入换行
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                if callable(self.submitted):
                    self.submitted()
            return
        super().keyPressEvent(event)

    def text(self) -> str:
        return self.toPlainText()

    def clear(self):
        super().clear()
        self.setFixedHeight(self._min_height)


# ── 颜色常量 ──────────────────────────────────────────
CLR_BG          = "#F8F9FB"
CLR_CARD        = "#FFFFFF"
CLR_BORDER      = "#E8ECF2"
CLR_PRIMARY     = "#5B8AF5"
CLR_URGENT      = "#FF6B6B"
CLR_NORMAL_TAG  = "#94A3B8"
CLR_TEXT        = "#2D3748"
CLR_MUTED       = "#718096"
CLR_DISABLED    = "#CBD5E0"
CLR_HOVER       = "#F0F4FF"
CLR_DONE_TEXT   = "#A0AEC0"

_SCROLLBAR_STYLE = """
    QScrollBar:vertical {
        width: 5px;
        background: transparent;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:vertical {
        background: #CBD5E0;
        border-radius: 2px;
        min-height: 20px;
    }
    QScrollBar::add-line:vertical {
        height: 0; border: none; background: none;
    }
    QScrollBar::sub-line:vertical {
        height: 0; border: none; background: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
"""


def _apply_scrollbar_style(scrollbar):
    """直接给 verticalScrollBar() 应用样式，确保箭头按钮被隐藏。"""
    scrollbar.setStyleSheet(_SCROLLBAR_STYLE)


def _tag_style(urgent: bool, done: bool = False) -> str:
    if done:
        return (
            "background: #F0FFF4; color: #38A169; border: 1px solid #C6F6D5;"
            "border-radius: 10px; font-size: 10px; padding: 1px 6px;"
        )
    if urgent:
        return (
            "background: #FFF0F0; color: #E53E3E; border: 1px solid #FED7D7;"
            "border-radius: 10px; font-size: 10px; padding: 1px 6px;"
        )
    return (
        "background: #F1F5F9; color: #64748B; border: 1px solid #E2E8F0;"
        "border-radius: 10px; font-size: 10px; padding: 1px 6px;"
    )


class TodoItem(QWidget):
    def __init__(self, todo: dict, on_toggle, on_delete, parent=None):
        super().__init__(parent)
        self.todo = todo
        self.on_toggle = on_toggle
        self.on_delete = on_delete
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"""
            TodoItem {{
                background: {CLR_CARD};
                border: 1px solid {CLR_BORDER};
                border-radius: 8px;
            }}
            TodoItem:hover {{
                background: {CLR_HOVER};
                border-color: #C3D0F5;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # 复选框（圆形，勾选后显示 ✓）
        self.checkbox = RoundCheckBox(bool(self.todo['completed']))
        self.checkbox.toggled.connect(lambda: self.on_toggle(self.todo['id']))
        layout.addWidget(self.checkbox)

        # 文字
        self.text_label = QLabel(self.todo['title'])
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._apply_text_style()
        layout.addWidget(self.text_label)

        # 状态/优先级标签
        done = bool(self.todo['completed'])
        is_urgent = self.todo['priority'] == 'urgent'
        tag_text = "完成" if done else ("紧急" if is_urgent else "一般")
        tag = QLabel(tag_text)
        tag.setStyleSheet(_tag_style(is_urgent, done))
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tag)

        # 删除按钮
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("删除")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {CLR_DISABLED};
                font-size: 15px;
                font-weight: bold;
                border-radius: 4px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: #FFE8E8;
                color: #E53E3E;
            }}
        """)
        del_btn.clicked.connect(lambda: self.on_delete(self.todo['id']))
        layout.addWidget(del_btn)

    def _apply_text_style(self):
        if self.todo['completed']:
            self.text_label.setStyleSheet(
                f"color: {CLR_DONE_TEXT}; text-decoration: line-through;"
            )
        else:
            self.text_label.setStyleSheet(f"color: {CLR_TEXT};")

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: white; border: 1px solid {CLR_BORDER};
                border-radius: 6px; padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 16px; border-radius: 4px;
                color: {CLR_TEXT}; font-size: 11px;
            }}
            QMenu::item:selected {{ background: #FFF0F0; color: #E53E3E; }}
        """)
        delete_action = QAction("🗑  删除", self)
        delete_action.triggered.connect(lambda: self.on_delete(self.todo['id']))
        menu.addAction(delete_action)
        menu.exec(self.mapToGlobal(pos))


class MiniProgress(QWidget):
    """轻量进度条显示完成比例"""
    def __init__(self, done: int, total: int, parent=None):
        super().__init__(parent)
        self.done = done
        self.total = total
        self.setFixedHeight(4)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # 背景
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(CLR_BORDER)))
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)
        # 进度
        if self.total > 0 and self.done > 0:
            ratio = self.done / self.total
            fill_w = max(h, int(w * ratio))
            p.setBrush(QBrush(QColor(CLR_PRIMARY)))
            p.drawRoundedRect(0, 0, fill_w, h, h // 2, h // 2)
        p.end()


class TodoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_date = date.today().isoformat()
        self._build_ui()
        self._load_todos()

    def _build_ui(self):
        self.setStyleSheet(f"background: {CLR_BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── 日期导航 ────────────────────────────────────
        date_card = QFrame()
        date_card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 1px solid {CLR_BORDER};
                border-radius: 8px;
            }}
        """)
        date_row = QHBoxLayout(date_card)
        date_row.setContentsMargins(6, 5, 6, 5)
        date_row.setSpacing(4)

        nav_style = f"""
            QPushButton {{
                background: transparent; border: none;
                color: {CLR_MUTED}; font-size: 11px;
                border-radius: 4px; padding: 2px 6px;
            }}
            QPushButton:hover {{ background: {CLR_HOVER}; color: {CLR_PRIMARY}; }}
        """
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(26, 26)
        self.prev_btn.setStyleSheet(nav_style)
        self.prev_btn.clicked.connect(self._prev_day)

        self.date_label = QPushButton()
        self.date_label.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {CLR_TEXT}; font-weight: bold;
                font-size: 12px; padding: 2px 6px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background: {CLR_HOVER}; color: {CLR_PRIMARY}; }}
        """)
        self.date_label.clicked.connect(self._pick_date)

        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(26, 26)
        self.next_btn.setStyleSheet(nav_style)
        self.next_btn.clicked.connect(self._next_day)

        date_row.addWidget(self.prev_btn)
        date_row.addStretch()
        date_row.addWidget(self.date_label)
        date_row.addStretch()
        date_row.addWidget(self.next_btn)
        layout.addWidget(date_card)

        # ── 统计区 ───────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(4, 0, 4, 0)
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"color: {CLR_MUTED}; font-size: 10px;")
        self.progress_bar = MiniProgress(0, 0)
        stats_row.addWidget(self.stats_label)
        stats_row.addStretch()
        layout.addLayout(stats_row)
        layout.addWidget(self.progress_bar)

        # ── 待办列表（可滚动）────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        _apply_scrollbar_style(self.scroll.verticalScrollBar())
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(5)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_container)
        layout.addWidget(self.scroll)

        # ── 空状态 ───────────────────────────────────────
        self.empty_label = QLabel("暂无待办，轻松一天～")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {CLR_DISABLED}; font-size: 12px; padding: 20px 0;")
        layout.addWidget(self.empty_label)

        # ── 输入区 ───────────────────────────────────────
        input_card = QFrame()
        input_card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 1px solid {CLR_BORDER};
                border-radius: 8px;
            }}
        """)
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(6)

        self.input_edit = AutoResizeTextEdit("＋  新建待办事项...")
        self.input_edit.submitted = self._add_todo
        self.input_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                border: 1.5px solid {CLR_BORDER};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
                background: #F8F9FB;
                color: {CLR_TEXT};
            }}
            QPlainTextEdit:focus {{
                border-color: {CLR_PRIMARY};
                background: white;
            }}
        """)
        input_layout.addWidget(self.input_edit)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)

        self.priority_combo = QComboBox()
        self.priority_combo.addItem("  一般", "normal")
        self.priority_combo.addItem("  紧急", "urgent")
        self.priority_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1.5px solid {CLR_BORDER};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                background: #F8F9FB;
                color: {CLR_TEXT};
                min-width: 70px;
            }}
            QComboBox:focus {{ border-color: {CLR_PRIMARY}; }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox QAbstractItemView {{
                border: 1px solid {CLR_BORDER};
                border-radius: 6px;
                background: white;
                selection-background-color: {CLR_HOVER};
                selection-color: {CLR_PRIMARY};
            }}
        """)
        ctrl_row.addWidget(self.priority_combo)
        ctrl_row.addStretch()

        add_btn = QPushButton("添加")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {CLR_PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #4A7AE8; }}
            QPushButton:pressed {{ background: #3A6AD8; }}
        """)
        add_btn.clicked.connect(self._add_todo)
        ctrl_row.addWidget(add_btn)
        input_layout.addLayout(ctrl_row)

        layout.addWidget(input_card)
        self._update_date_label()

    # ── 日期导航 ─────────────────────────────────────────
    def _update_date_label(self):
        today = date.today().isoformat()
        if self._current_date == today:
            d = date.fromisoformat(self._current_date)
            self.date_label.setText(f"今天  {d.month}/{d.day}")
        else:
            self.date_label.setText(f"{self._current_date}")

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
        dialog = QDialog(self)
        dialog.setWindowTitle("选择日期")
        dialog.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        dialog.setStyleSheet(f"""
            QDialog {{
                background: white;
                border: 1px solid {CLR_BORDER};
                border-radius: 10px;
            }}
        """)
        vbox = QVBoxLayout(dialog)
        vbox.setContentsMargins(6, 6, 6, 6)
        cal = QCalendarWidget()
        cal.setSelectedDate(QDate.fromString(self._current_date, "yyyy-MM-dd"))
        cal.setGridVisible(False)
        cal.setStyleSheet(f"""
            QCalendarWidget QAbstractItemView {{
                selection-background-color: {CLR_PRIMARY};
                selection-color: white;
                font-size: 11px;
                color: {CLR_TEXT};
                background: white;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background: {CLR_BG};
            }}
            QCalendarWidget QToolButton {{
                color: {CLR_TEXT};
                background: transparent;
                border: none;
                font-size: 12px;
                padding: 2px 6px;
            }}
            QCalendarWidget QToolButton:hover {{
                background: {CLR_HOVER};
                border-radius: 4px;
                color: {CLR_PRIMARY};
            }}
            QCalendarWidget QSpinBox {{
                color: {CLR_TEXT};
                background: white;
                border: 1px solid {CLR_BORDER};
                border-radius: 4px;
                padding: 1px 4px;
                font-size: 12px;
            }}
            QCalendarWidget QMenu {{
                color: {CLR_TEXT};
                background: white;
            }}
        """)

        def on_date_clicked(qdate):
            self._current_date = qdate.toString("yyyy-MM-dd")
            self._update_date_label()
            self._load_todos()
            dialog.accept()

        cal.clicked.connect(on_date_clicked)
        vbox.addWidget(cal)
        btn_pos = self.date_label.mapToGlobal(
            self.date_label.rect().bottomLeft()
        )
        dialog.move(btn_pos)
        dialog.exec()

    # ── 加载/刷新 ────────────────────────────────────────
    def _load_todos(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        todos = get_todos_by_date(self._current_date)
        total = len(todos)
        done = sum(1 for t in todos if t['completed'])

        # 更新统计
        if total:
            self.stats_label.setText(f"共 {total} 项 · 已完成 {done} 项")
        else:
            self.stats_label.setText("")

        # 进度条
        self.progress_bar.done = done
        self.progress_bar.total = total
        self.progress_bar.update()
        self.progress_bar.setVisible(total > 0)

        # 空状态
        self.empty_label.setVisible(total == 0)
        self.scroll.setVisible(total > 0)

        # 排序：紧急未完成 > 一般未完成 > 已完成
        def sort_key(t):
            return (t['completed'], 0 if t['priority'] == 'urgent' else 1)

        for todo in sorted(todos, key=sort_key):
            w = TodoItem(todo, self._handle_toggle, self._handle_delete)
            self.list_layout.insertWidget(self.list_layout.count() - 1, w)

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


# ══════════════════════════════════════════════════════════
#  全部待办视图
# ══════════════════════════════════════════════════════════

class AllTodosWidget(QWidget):
    """展示跨日期的所有待办，支持「未完成 / 全部」切换，显示日期。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._show_all = False   # False=仅未完成，True=全部
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.setStyleSheet(f"background: {CLR_BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)

        # ── 筛选切换 ──────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.setSpacing(0)

        self.btn_incomplete = self._filter_btn("未完成", active=True)
        self.btn_all        = self._filter_btn("全部", active=False)
        self.btn_incomplete.clicked.connect(lambda: self._set_filter(False))
        self.btn_all.clicked.connect(lambda: self._set_filter(True))

        filter_row.addWidget(self.btn_incomplete)
        filter_row.addWidget(self.btn_all)
        filter_row.addStretch()

        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"color: {CLR_MUTED}; font-size: 10px;")
        filter_row.addWidget(self.count_label)
        layout.addLayout(filter_row)

        # ── 列表 ──────────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        _apply_scrollbar_style(self.scroll.verticalScrollBar())
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_container)
        layout.addWidget(self.scroll)

        # ── 空状态 ────────────────────────────────────────
        self.empty_label = QLabel("太棒了，没有未完成的待办！")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            f"color: {CLR_DISABLED}; font-size: 12px; padding: 20px 0;"
        )
        layout.addWidget(self.empty_label)

    def _filter_btn(self, text: str, active: bool) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(False)
        btn.setFixedHeight(26)
        self._apply_filter_btn_style(btn, active)
        return btn

    def _apply_filter_btn_style(self, btn: QPushButton, active: bool):
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {CLR_PRIMARY}; color: white;
                    border: none; border-radius: 5px;
                    padding: 2px 14px; font-size: 11px; font-weight: bold;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {CLR_MUTED};
                    border: 1px solid {CLR_BORDER}; border-radius: 5px;
                    padding: 2px 14px; font-size: 11px;
                }}
                QPushButton:hover {{ background: {CLR_HOVER}; color: {CLR_PRIMARY}; }}
            """)

    def _set_filter(self, show_all: bool):
        self._show_all = show_all
        self._apply_filter_btn_style(self.btn_incomplete, not show_all)
        self._apply_filter_btn_style(self.btn_all, show_all)
        self.refresh()

    def refresh(self):
        # 清除旧内容（保留末尾 stretch）
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        todos = get_all_todos(only_incomplete=not self._show_all)

        self.count_label.setText(f"共 {len(todos)} 项")
        self.empty_label.setVisible(len(todos) == 0)
        self.scroll.setVisible(len(todos) > 0)

        # 按日期分组
        groups: dict[str, list[dict]] = {}
        for t in todos:
            groups.setdefault(t['date'], []).append(t)

        today = date.today().isoformat()
        for d, items in groups.items():
            # 日期分组标题
            if d == today:
                label_text = f"今天  {d}"
            else:
                label_text = d
            header = QLabel(f"  {label_text}")
            header.setStyleSheet(f"""
                color: {CLR_MUTED}; font-size: 10px;
                background: transparent;
                padding: 4px 0 2px 0;
            """)
            self.list_layout.insertWidget(self.list_layout.count() - 1, header)

            for todo in items:
                w = AllTodoItem(todo,
                                on_toggle=self._handle_toggle,
                                on_delete=self._handle_delete)
                self.list_layout.insertWidget(self.list_layout.count() - 1, w)

    def _handle_toggle(self, todo_id: int):
        toggle_todo(todo_id)
        self.refresh()

    def _handle_delete(self, todo_id: int):
        delete_todo(todo_id)
        self.refresh()


class AllTodoItem(QWidget):
    """全部视图里的单条待办（含日期徽标）。"""

    def __init__(self, todo: dict, on_toggle, on_delete, parent=None):
        super().__init__(parent)
        self.todo = todo
        self.on_toggle = on_toggle
        self.on_delete = on_delete
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"""
            AllTodoItem {{
                background: {CLR_CARD};
                border: 1px solid {CLR_BORDER};
                border-radius: 8px;
            }}
            AllTodoItem:hover {{
                background: {CLR_HOVER};
                border-color: #C3D0F5;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(8)

        # 复选框
        cb = RoundCheckBox(bool(self.todo['completed']))
        cb.toggled.connect(lambda: self.on_toggle(self.todo['id']))
        layout.addWidget(cb)

        # 文字
        text = QLabel(self.todo['title'])
        text.setWordWrap(True)
        text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if self.todo['completed']:
            text.setStyleSheet(f"color: {CLR_DONE_TEXT}; text-decoration: line-through;")
        else:
            text.setStyleSheet(f"color: {CLR_TEXT};")
        layout.addWidget(text)

        # 状态/优先级标签
        done = bool(self.todo['completed'])
        is_urgent = self.todo['priority'] == 'urgent'
        tag_text = "完成" if done else ("紧急" if is_urgent else "一般")
        tag = QLabel(tag_text)
        tag.setStyleSheet(_tag_style(is_urgent, done))
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tag)

        # 删除按钮
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip("删除")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {CLR_DISABLED}; font-size: 15px;
                font-weight: bold; border-radius: 4px; padding: 0;
            }}
            QPushButton:hover {{ background: #FFE8E8; color: #E53E3E; }}
        """)
        del_btn.clicked.connect(lambda: self.on_delete(self.todo['id']))
        layout.addWidget(del_btn)
